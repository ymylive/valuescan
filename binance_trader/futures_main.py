"""
Binance 合约自动交易主程序
整合信号监控 + 信号聚合 + 合约交易执行 + 移动止损
"""

import sys
import os
import time
import logging
import socket
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

# 添加父目录到路径，以便导入 signal_monitor 模块（如果需要集成）
sys.path.insert(0, str(Path(__file__).parent.parent))

from binance_trader.signal_aggregator import SignalAggregator
from binance_trader.risk_manager import RiskManager
from binance_trader.futures_trader import BinanceFuturesTrader
from binance_trader.trailing_stop import TrailingStopManager, PyramidingExitManager
from binance_trader.trading_signal_processor import TradingSignalProcessor, get_trading_signal_processor

# 导入配置
try:
    from binance_trader import config
except ImportError:
    print("❌ Error: config.py not found!")
    print("Please copy config.example.py to config.py and fill in your settings.")
    sys.exit(1)


def _is_local_proxy_reachable(proxy_url: str) -> bool:
    try:
        parsed = urlparse(proxy_url)
    except Exception:
        return False

    host = parsed.hostname
    port = parsed.port
    if not host or not port:
        return False

    if host not in {"127.0.0.1", "localhost", "::1"}:
        return True

    try:
        with socket.create_connection((host, port), timeout=0.3):
            return True
    except OSError:
        return False


def _resolve_binance_proxy() -> Optional[str]:
    """
    Resolve SOCKS5 proxy for Binance API calls.

    Priority:
    1) env vars (BINANCE_SOCKS5_PROXY/SOCKS5_PROXY/VALUESCAN_SOCKS5_PROXY/VALUESCAN_PROXY)
    2) config.SOCKS5_PROXY
    3) auto-detect local xray SOCKS (127.0.0.1:1080) if reachable
    """
    for key in ("BINANCE_SOCKS5_PROXY", "SOCKS5_PROXY", "VALUESCAN_SOCKS5_PROXY", "VALUESCAN_PROXY"):
        v = (os.getenv(key) or "").strip()
        if v:
            return v

    v = getattr(config, "SOCKS5_PROXY", None)
    if isinstance(v, str) and v.strip():
        return v.strip()

    if not bool(getattr(config, "AUTO_PROXY_BINANCE", True)):
        return None

    default_proxy = (os.getenv("BINANCE_DEFAULT_SOCKS5") or "socks5://127.0.0.1:1080").strip()
    if default_proxy and _is_local_proxy_reachable(default_proxy):
        return default_proxy
    return None


class FuturesAutoTradingSystem:
    """合约自动交易系统主类"""

    def __init__(self):
        """初始化系统"""
        self._setup_logging()
        self.logger = logging.getLogger(__name__)

        self.logger.info("="*80)
        self.logger.info("🚀 初始化币安合约自动交易系统")
        self.logger.info("="*80)

        # 1. 初始化信号聚合器
        signal_state_file = getattr(config, "SIGNAL_STATE_FILE", "data/signal_state.json")
        enable_signal_cache = getattr(config, "ENABLE_SIGNAL_STATE_CACHE", True)
        max_processed_ids = getattr(config, "MAX_PROCESSED_SIGNAL_IDS", 5000)
        if not signal_state_file:
            enable_signal_cache = False

        self.signal_aggregator = SignalAggregator(
            time_window=config.SIGNAL_TIME_WINDOW,
            min_score=config.MIN_SIGNAL_SCORE,
            state_file=signal_state_file if enable_signal_cache else None,
            enable_persistence=enable_signal_cache,
            max_processed_ids=max_processed_ids
        )

        # 2. 初始化风险管理器
        self.risk_manager = RiskManager(
            max_position_percent=config.MAX_POSITION_PERCENT,
            max_total_position_percent=config.MAX_TOTAL_POSITION_PERCENT,
            max_daily_trades=config.MAX_DAILY_TRADES,
            max_daily_loss_percent=config.MAX_DAILY_LOSS_PERCENT,
            stop_loss_percent=config.STOP_LOSS_PERCENT,
            take_profit_1_percent=config.TAKE_PROFIT_1_PERCENT,
            take_profit_2_percent=config.TAKE_PROFIT_2_PERCENT,
            major_coins=getattr(config, 'MAJOR_COINS', []),
            major_coin_max_position_percent=getattr(config, 'MAJOR_COIN_MAX_POSITION_PERCENT', None)
        )

        # 3. 初始化合约交易器
        try:
            # 获取代理配置（如果有）
            proxy = _resolve_binance_proxy()
            api_timeout = getattr(config, 'API_TIMEOUT', 30)
            api_retry_count = getattr(config, 'API_RETRY_COUNT', 3)
            enable_proxy_fallback = getattr(config, 'ENABLE_PROXY_FALLBACK', True)

            self.trader = BinanceFuturesTrader(
                api_key=config.BINANCE_API_KEY,
                api_secret=config.BINANCE_API_SECRET,
                risk_manager=self.risk_manager,
                leverage=config.LEVERAGE,
                margin_type=config.MARGIN_TYPE,
                testnet=config.USE_TESTNET,
                proxy=proxy,
                api_timeout=api_timeout,
                api_retry_count=api_retry_count,
                enable_proxy_fallback=enable_proxy_fallback
            )
        except Exception as e:
            self.logger.error(f"初始化币安合约交易器失败: {e}")
            self.logger.error("请检查 config.py 中的 API 凭证")
            sys.exit(1)

        # 4. 初始化移动止损管理器（如果启用）
        self.trailing_stop_manager = None
        if config.ENABLE_TRAILING_STOP:
            self.trailing_stop_manager = TrailingStopManager(
                activation_percent=config.TRAILING_STOP_ACTIVATION,
                callback_percent=config.TRAILING_STOP_CALLBACK,
                update_interval=config.TRAILING_STOP_UPDATE_INTERVAL
            )
            self.logger.info("✅ 追踪止损已启用")

        # 5. 初始化分批止盈管理器（如果启用）
        self.pyramiding_manager = None
        if config.ENABLE_PYRAMIDING_EXIT:
            execution = str(getattr(config, "PYRAMIDING_EXIT_EXECUTION", "orders")).strip().lower()
            if execution == "market":
                self.pyramiding_manager = PyramidingExitManager(
                    exit_levels=config.PYRAMIDING_EXIT_LEVELS
                )
                self.logger.info("✅ 金字塔退出已启用 (market)")
            else:
                self.pyramiding_manager = None
                self.logger.info("✅ 金字塔止盈将由交易所挂单执行 (orders)")

        # 6. 初始化交易信号处理器（新策略）
        long_enabled = getattr(config, 'LONG_TRADING_ENABLED', True)
        short_enabled = getattr(config, 'SHORT_TRADING_ENABLED', False)
        self.trading_signal_processor = get_trading_signal_processor(
            long_enabled=long_enabled,
            short_enabled=short_enabled
        )
        self.logger.info(f"✅ 交易信号处理器已初始化 (做多={long_enabled}, 做空={short_enabled})")

        # 做空配置
        self.short_stop_loss_percent = getattr(config, 'SHORT_STOP_LOSS_PERCENT', 2.0)
        self.short_take_profit_percent = getattr(config, 'SHORT_TAKE_PROFIT_PERCENT', 3.0)

        # 7. 更新账户余额
        self.trader.update_risk_manager_balance()

        # 状态跟踪
        self.last_balance_update = time.time()
        self.last_position_monitor = time.time()
        self.last_trailing_stop_check = time.time()

        # 8. 初始化时检查已有持仓，添加到追踪管理器
        self._init_existing_positions()

        self.logger.info("✅ 系统初始化成功")
        self._print_system_status()

    def _init_existing_positions(self):
        """初始化时检查已有持仓，添加到追踪管理器"""
        try:
            # 先更新持仓信息
            self.trader.update_positions()
            
            if not self.trader.positions:
                self.logger.info("📊 当前无持仓")
                return
            
            self.logger.info(f"📊 检测到 {len(self.trader.positions)} 个已有持仓，添加到追踪管理器")
            
            for symbol, position in self.trader.positions.items():
                symbol_base = symbol.replace("USDT", "")
                
                # 只追踪多仓
                if position.quantity > 0:
                    # 添加到移动止损跟踪
                    if self.trailing_stop_manager:
                        self.trailing_stop_manager.add_position(
                            symbol_base,
                            position.entry_price,
                            position.mark_price
                        )
                        self.logger.info(
                            f"  ✅ {symbol_base} 已添加到移动止损跟踪 "
                            f"(入场={position.entry_price:.4f}, 当前={position.mark_price:.4f})"
                        )
                    
                    # 添加到分批止盈跟踪
                    if self.pyramiding_manager:
                        self.pyramiding_manager.add_position(symbol_base, position.entry_price)
                        self.logger.info(f"  ✅ {symbol_base} 已添加到金字塔止盈跟踪")
                else:
                    self.logger.info(f"  ⏭️ {symbol_base} 是空仓，跳过追踪")
                    
        except Exception as e:
            self.logger.warning(f"初始化已有持仓追踪失败: {e}")

    def _setup_logging(self):
        """配置日志系统"""
        log_dir = Path(config.LOG_FILE).parent
        log_dir.mkdir(parents=True, exist_ok=True)

        logging.basicConfig(
            level=getattr(logging, config.LOG_LEVEL),
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler(config.LOG_FILE, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )

    def _print_system_status(self):
        """打印系统状态"""
        status = self.risk_manager.get_status()

        self.logger.info("="*80)
        self.logger.info("📊 系统状态")
        self.logger.info("="*80)
        self.logger.info(f"交易模式: 期货 {'测试网 ⚠️' if config.USE_TESTNET else '生产环境 🔴'}")
        self.logger.info(f"杠杆倍数: {config.LEVERAGE}x")
        self.logger.info(f"保证金类型: {config.MARGIN_TYPE}")
        self.logger.info(f"自动交易: {'已启用 ✅' if config.AUTO_TRADING_ENABLED else '已禁用 (观察模式)'}")
        long_enabled = getattr(config, 'LONG_TRADING_ENABLED', True)
        short_enabled = getattr(config, 'SHORT_TRADING_ENABLED', False)
        self.logger.info(f"做多策略: {'已启用 ✅' if long_enabled else '已禁用'}")
        self.logger.info(f"做空策略: {'已启用 ✅' if short_enabled else '已禁用'}")
        self.logger.info(f"追踪止损: {'已启用 ✅' if config.ENABLE_TRAILING_STOP else '已禁用'}")
        self.logger.info(f"金字塔退出: {'已启用 ✅' if config.ENABLE_PYRAMIDING_EXIT else '已禁用'}")
        self.logger.info(f"总余额: {status['total_balance']:.2f} USDT")
        self.logger.info(f"可用余额: {status['available_balance']:.2f} USDT")
        self.logger.info(f"持仓数量: {status['position_count']}")
        self.logger.info(f"今日交易: {status['daily_trades']}/{config.MAX_DAILY_TRADES}")
        self.logger.info(f"今日盈亏: {status['daily_pnl']:.2f} USDT")
        self.logger.info(f"交易状态: {'运行中' if status['trading_enabled'] else '已暂停: ' + status['halt_reason']}")
        self.logger.info("="*80)

    def _check_emergency_stop(self) -> bool:
        """检查紧急停止开关"""
        if config.ENABLE_EMERGENCY_STOP:
            if os.path.exists(config.EMERGENCY_STOP_FILE):
                self.logger.error(f"🚨 检测到紧急停止文件: {config.EMERGENCY_STOP_FILE}")
                self.risk_manager.halt_trading("紧急停止已激活")
                return True
        return False

    def _get_leverage(self, symbol: str) -> int:
        """根据币种获取杠杆倍数 (支持主流币独立杠杆)"""
        major_coin_leverage = getattr(config, 'MAJOR_COIN_LEVERAGE', None)
        major_coins = getattr(config, 'MAJOR_COINS', [])
        
        # symbol 可能包含 USDT 后缀，先去除
        base_symbol = symbol.replace("USDT", "").replace("BUSD", "")
        
        if major_coin_leverage is not None and base_symbol in major_coins:
            return int(major_coin_leverage)
        return int(config.LEVERAGE)

    def process_signal(self, message_type: int, message_id: str, symbol: str, data: dict):
        """
        处理来自信号监控模块的信号

        Args:
            message_type: ValueScan 消息类型 (110=Alpha, 113=FOMO, 112=FOMO加剧)
            message_id: 消息ID
            symbol: 交易标的（如 "BTC"）
            data: 原始消息数据
        """
        # 检查紧急停止
        if self._check_emergency_stop():
            return

        # 获取 predictType（用于 Type 100 信号）
        predict_type = data.get('predictType') if data else None

        # 使用新的交易信号处理器处理信号
        trade_signal = self.trading_signal_processor.process_signal(
            message_type=message_type,
            symbol=symbol,
            predict_type=predict_type
        )

        # 如果生成了交易信号，执行交易
        if trade_signal:
            self._handle_trade_signal(trade_signal)
            return

        # 兼容旧逻辑：添加到信号聚合器
        confluence = self.signal_aggregator.add_signal(
            message_type=message_type,
            message_id=message_id,
            symbol=symbol,
            data=data
        )

        # 检查是否是风险信号（FOMO加剧）- 用于已有持仓的止盈建议
        if message_type == 112:  # FOMO加剧
            self._handle_risk_signal(symbol)
            return

        # 如果匹配到聚合信号（旧逻辑，保持兼容）
        if confluence:
            self._handle_confluence_signal(confluence)

    def _handle_trade_signal(self, trade_signal):
        """
        处理交易信号（来自 TradingSignalProcessor）
        
        Args:
            trade_signal: TradeSignal 对象，包含 symbol, direction, signal_type 等
        """
        self.logger.warning("🔥"*40)
        self.logger.warning(f"检测到交易信号: {trade_signal.direction} {trade_signal.symbol}")
        self.logger.warning(f"原因: {trade_signal.reason}")
        self.logger.warning("🔥"*40)

        # 检查是否启用自动交易
        if not config.AUTO_TRADING_ENABLED:
            self.logger.info("⏸️  自动交易已禁用，跳过执行 (观察模式)")
            return

        # 获取当前价格
        binance_symbol = f"{trade_signal.symbol}{config.SYMBOL_SUFFIX}"
        current_price = self.trader.get_symbol_price(binance_symbol)

        if not current_price:
            self.logger.error(f"获取 {binance_symbol} 价格失败，跳过交易")
            return

        # 检查是否已有同方向持仓
        existing_position = self.trader.get_position_info(binance_symbol)
        if existing_position:
            pos_qty = existing_position.quantity
            if trade_signal.direction == 'LONG' and pos_qty > 0:
                self.logger.info(f"⏭️ {binance_symbol} 已有多仓，跳过开仓")
                return
            if trade_signal.direction == 'SHORT' and pos_qty < 0:
                self.logger.info(f"⏭️ {binance_symbol} 已有空仓，跳过开仓")
                return

        # 生成交易建议
        recommendation = self.risk_manager.generate_trade_recommendation(
            symbol=trade_signal.symbol,
            current_price=current_price,
            signal_score=0.8  # 单信号默认评分
        )

        # 强制设置为 BUY（风控可能返回 HOLD）
        if recommendation.action == "HOLD":
            self.logger.info(f"风控建议 HOLD: {recommendation.reason}")
            # 如果风控允许，仍然执行
            if "每日交易次数" not in recommendation.reason and "亏损" not in recommendation.reason:
                recommendation.action = "BUY"
            else:
                return

        # 获取杠杆倍数
        leverage = self._get_leverage(trade_signal.symbol)

        # 执行交易
        if trade_signal.direction == 'LONG':
            success = self.trader.open_long_position(
                recommendation,
                symbol_suffix=config.SYMBOL_SUFFIX,
                leverage=leverage,
                margin_type=config.MARGIN_TYPE
            )
        else:  # SHORT
            # 修改 recommendation 的 reason
            recommendation.reason = trade_signal.reason
            success = self.trader.open_short_position(
                recommendation,
                symbol_suffix=config.SYMBOL_SUFFIX,
                leverage=leverage,
                margin_type=config.MARGIN_TYPE,
                stop_loss_percent=self.short_stop_loss_percent,
                take_profit_percent=self.short_take_profit_percent
            )

        if success:
            self.logger.warning(f"✅ {trade_signal.direction} 交易执行成功: {binance_symbol}")

            # 添加到移动止损跟踪（仅做多）
            if trade_signal.direction == 'LONG' and self.trailing_stop_manager:
                self.trailing_stop_manager.add_position(
                    trade_signal.symbol,
                    current_price,
                    current_price
                )

            # 添加到分批止盈跟踪（仅做多）
            if trade_signal.direction == 'LONG' and self.pyramiding_manager:
                self.pyramiding_manager.add_position(
                    trade_signal.symbol,
                    current_price
                )
        else:
            self.logger.error(f"❌ {trade_signal.direction} 交易执行失败: {binance_symbol}")

    def _handle_risk_signal(self, symbol: str):
        """处理风险信号（FOMO加剧）- 建议止盈"""
        binance_symbol = f"{symbol}{config.SYMBOL_SUFFIX}"

        # 检查是否有持仓
        if binance_symbol in self.trader.positions:
            position = self.trader.positions[binance_symbol]

            self.logger.warning(
                f"\n⚠️  检测到 {symbol} 的风险信号 (FOMO加剧)!\n"
                f"   市场情绪过热，建议止盈离场\n"
                f"   当前盈亏: {position.unrealized_pnl_percent:.2f}%\n"
            )

            # 如果盈利，考虑部分止盈
            if position.unrealized_pnl_percent > 0:
                self.logger.warning(f"💡 建议平仓 50% 锁定利润")

                if config.AUTO_TRADING_ENABLED:
                    # 自动平仓50%
                    self.trader.partial_close_position(
                        binance_symbol,
                        0.5,
                        reason="FOMO加剧风险信号 - 自动止盈"
                    )
        else:
            self.logger.info(f"⚠️  {symbol} 有风险信号，但未持仓")

    def _handle_confluence_signal(self, confluence):
        """处理聚合信号（买入信号）"""
        self.logger.warning("🔥"*40)
        self.logger.warning(f"检测到聚合信号: {confluence}")
        self.logger.warning("🔥"*40)

        # 3. 检查是否启用自动交易
        if not config.AUTO_TRADING_ENABLED:
            self.logger.info("⏸️  自动交易已禁用，跳过执行 (观察模式)")
            return

        # 4. 获取当前价格
        binance_symbol = f"{confluence.symbol}{config.SYMBOL_SUFFIX}"
        current_price = self.trader.get_symbol_price(binance_symbol)

        if not current_price:
            self.logger.error(f"获取 {binance_symbol} 价格失败，跳过交易")
            return

        # 5. 生成交易建议
        recommendation = self.risk_manager.generate_trade_recommendation(
            symbol=confluence.symbol,
            current_price=current_price,
            signal_score=confluence.score
        )

        self.logger.info(f"交易建议: {recommendation.action} - {recommendation.reason}")

        # 6. 执行交易
        if recommendation.action == "BUY":
            leverage = self._get_leverage(confluence.symbol)
            success = self.trader.open_long_position(
                recommendation,
                symbol_suffix=config.SYMBOL_SUFFIX,
                leverage=leverage,
                margin_type=config.MARGIN_TYPE
            )

            if success:
                self.logger.info("✅ 交易执行成功")

                # 添加到移动止损跟踪
                if self.trailing_stop_manager:
                    self.trailing_stop_manager.add_position(
                        confluence.symbol,
                        current_price,
                        current_price
                    )

                # 添加到分批止盈跟踪
                if self.pyramiding_manager:
                    self.pyramiding_manager.add_position(
                        confluence.symbol,
                        current_price
                    )

            else:
                self.logger.error("❌ 交易执行失败")

    def monitor_positions(self):
        """定期监控持仓"""
        now = time.time()

        if now - self.last_position_monitor >= config.POSITION_MONITOR_INTERVAL:
            # 记录更新前的持仓
            previous_symbols = set(self.trader.positions.keys())
            
            # 更新持仓信息
            self.trader.monitor_positions()
            
            # 检测被外部平仓的标的，清理相关管理器
            current_symbols = set(self.trader.positions.keys())
            closed_symbols = previous_symbols - current_symbols
            for closed_symbol in closed_symbols:
                symbol_base = closed_symbol.replace("USDT", "")
                self.logger.info(f"🧹 清理 {symbol_base} 的追踪止损和金字塔退出记录")
                if self.trailing_stop_manager:
                    self.trailing_stop_manager.remove_position(symbol_base)
                if self.pyramiding_manager:
                    self.pyramiding_manager.remove_position(symbol_base)

            # 检测新持仓（可能是程序重启后发现的已有持仓），自动添加到追踪管理器
            new_symbols = current_symbols - previous_symbols
            for new_symbol in new_symbols:
                symbol_base = new_symbol.replace("USDT", "")
                position = self.trader.positions.get(new_symbol)
                if position and position.quantity > 0:  # 只追踪多仓
                    # 添加到移动止损跟踪
                    if self.trailing_stop_manager and symbol_base not in self.trailing_stop_manager.tracking_data:
                        self.trailing_stop_manager.add_position(
                            symbol_base,
                            position.entry_price,
                            position.mark_price
                        )
                        self.logger.info(f"📊 自动添加 {symbol_base} 到移动止损跟踪 (入场价={position.entry_price:.4f})")
                    # 添加到分批止盈跟踪
                    if self.pyramiding_manager and symbol_base not in self.pyramiding_manager.entry_prices:
                        self.pyramiding_manager.add_position(symbol_base, position.entry_price)
                        self.logger.info(f"📊 自动添加 {symbol_base} 到金字塔止盈跟踪")

            self.last_position_monitor = now

    def check_trailing_stops(self):
        """检查移动止损"""
        if not self.trailing_stop_manager:
            return

        now = time.time()
        if now - self.last_trailing_stop_check < config.TRAILING_STOP_UPDATE_INTERVAL:
            return

        self.last_trailing_stop_check = now

        # 遍历所有持仓
        for symbol, position in self.trader.positions.items():
            symbol_base = symbol.replace("USDT", "")

            # 更新价格并检查触发
            trigger = self.trailing_stop_manager.update_price(
                symbol_base,
                position.mark_price
            )

            if trigger:
                # 触发移动止损，立即平仓
                self.logger.warning(f"🛑 {symbol} 触发追踪止损")
                self.trader.close_position(symbol, reason="追踪止损")

                # 移除分批止盈跟踪
                if self.pyramiding_manager:
                    self.pyramiding_manager.remove_position(symbol_base)

    def check_pyramiding_exits(self):
        """检查分批止盈"""
        if not self.pyramiding_manager:
            return

        # 遍历所有持仓
        for symbol, position in self.trader.positions.items():
            symbol_base = symbol.replace("USDT", "")

            # 检查是否触发分批止盈
            exit_trigger = self.pyramiding_manager.check_exit_trigger(
                symbol_base,
                position.mark_price
            )

            if exit_trigger:
                profit_pct, close_ratio, level_idx = exit_trigger

                self.logger.info(
                    f"🎯 {symbol} 触发金字塔退出 Level {level_idx+1}: "
                    f"盈利 {profit_pct:.2f}%, 平仓 {close_ratio*100:.0f}%"
                )

                # 部分平仓
                if close_ratio >= 1.0:
                    # 全部平仓
                    self.trader.close_position(symbol, reason=f"金字塔退出 Level {level_idx+1}")

                    # 清理跟踪
                    if self.trailing_stop_manager:
                        self.trailing_stop_manager.remove_position(symbol_base)
                    self.pyramiding_manager.remove_position(symbol_base)
                else:
                    # 部分平仓
                    self.trader.partial_close_position(
                        symbol,
                        close_ratio,
                        reason=f"金字塔退出 Level {level_idx+1}"
                    )

    def update_balance(self):
        """定期更新余额"""
        now = time.time()

        if now - self.last_balance_update >= config.BALANCE_UPDATE_INTERVAL:
            self.trader.update_risk_manager_balance()
            self.last_balance_update = now

    def run_standalone(self):
        """
        运行模式：独立模式
        仅运行交易系统，手动调用 process_signal() 处理信号
        """
        self.logger.info("📡 以独立模式运行 (期货)")
        self.logger.info("等待通过 process_signal() 方法接收外部信号...")

        try:
            while True:
                # 定期维护任务
                self.monitor_positions()
                self.check_trailing_stops()
                self.check_pyramiding_exits()
                self.update_balance()

                # 打印状态（每5分钟）
                if time.time() % 300 < 1:
                    self._print_system_status()

                    # 打印信号统计
                    stats = self.signal_aggregator.get_pending_signals_count()
                    self.logger.info(
                        f"📊 信号缓冲: "
                        f"FOMO={stats['fomo']} ({stats['symbols_with_fomo']} 个标的), "
                        f"ALPHA={stats['alpha']} ({stats['symbols_with_alpha']} 个标的)"
                    )

                time.sleep(1)

        except KeyboardInterrupt:
            self.logger.info("\n🛑 正在关闭...")
            self._print_system_status()


def main():
    """主函数"""
    print("\n" + "="*80)
    print("🚀 币安合约自动交易系统 - 基于 ValueScan 信号")
    print("="*80)
    print("\n⚠️  警告: 这是带杠杆的期货交易")
    print("   高风险，高收益。请谨慎交易！")
    print("\n选择运行模式:")
    print("1. 独立模式 (手动输入信号)")
    print("2. 测试信号聚合")
    print()

    choice = input("输入选择 (1/2): ").strip()

    if choice == "2":
        # 测试模式
        test_signal_aggregation()
        return

    # 初始化系统
    system = FuturesAutoTradingSystem()

    if choice == "1":
        system.run_standalone()
    else:
        print("无效选择")


def test_signal_aggregation():
    """测试信号聚合功能"""
    print("\n🧪 测试信号聚合功能...\n")

    aggregator = SignalAggregator(
        time_window=300,
        min_score=0.6
    )

    # 模拟信号
    print("1️⃣ 添加 BTC 的 FOMO 信号...")
    result1 = aggregator.add_signal(113, "msg1", "BTC", {})
    print(f"   结果: {result1}\n")

    print("2️⃣ 添加 BTC 的 Alpha 信号...")
    result2 = aggregator.add_signal(110, "msg2", "BTC", {})
    print(f"   结果: {result2}\n")

    if result2:
        print("✅ 信号聚合成功！")
        print(f"   标的: {result2.symbol}")
        print(f"   时间差: {result2.time_gap:.2f}秒")
        print(f"   评分: {result2.score:.2f}")
    else:
        print("❌ 未检测到信号聚合（不应该发生）")

    print("\n3️⃣ 添加 ETH 的 FOMO 信号（无 Alpha 信号）...")
    result3 = aggregator.add_signal(113, "msg3", "ETH", {})
    print(f"   结果: {result3} (预期为 None)\n")

    print("4️⃣ 添加 BTC 的风险信号 (Type 112 - FOMO加剧)...")
    result4 = aggregator.add_signal(112, "msg4", "BTC", {})
    print(f"   结果: {result4} (风险信号不触发聚合)\n")

    # 检查风险信号
    has_risk = aggregator.check_risk_signal("BTC")
    print(f"⚠️  BTC 是否有风险信号: {has_risk}")

    stats = aggregator.get_pending_signals_count()
    print(f"\n📊 待匹配信号统计: {stats}")


if __name__ == "__main__":
    main()
