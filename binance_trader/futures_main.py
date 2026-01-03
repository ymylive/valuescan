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
            major_coin_max_position_percent=getattr(config, 'MAJOR_COIN_MAX_POSITION_PERCENT', None),
            major_total_position_percent=getattr(config, 'MAJOR_TOTAL_POSITION_PERCENT', None),
            alt_total_position_percent=getattr(config, 'ALT_TOTAL_POSITION_PERCENT', None),
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
        enable_alt_trailing = bool(getattr(config, "ENABLE_TRAILING_STOP", False))
        enable_major_trailing = bool(getattr(config, "ENABLE_MAJOR_COIN_STRATEGY", False)) and bool(
            getattr(config, "MAJOR_COIN_ENABLE_TRAILING_STOP", True)
        )
        if enable_alt_trailing or enable_major_trailing:
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

        # 7. 初始化 AI 模式处理器（如果启用）
        self.ai_mode_enabled = getattr(config, 'ENABLE_AI_MODE', False)
        self.ai_mode_handler = None
        self.ai_position_agent = None

        if self.ai_mode_enabled:
            from binance_trader.ai_mode_handler import AISignalHandler
            from binance_trader.ai_position_agent import AIPositionAgent

            blacklist = getattr(config, 'COIN_BLACKLIST', [])
            self.ai_mode_handler = AISignalHandler(blacklist=blacklist)
            self.logger.info(f"✅ AI 托管模式已启用，黑名单: {blacklist}")

            # 初始化 AI 仓位管理代理（如果启用）
            enable_ai_position_agent = getattr(config, 'ENABLE_AI_POSITION_AGENT', False)
            if enable_ai_position_agent:
                ai_api_key = getattr(config, 'AI_POSITION_API_KEY', '')
                ai_api_url = getattr(config, 'AI_POSITION_API_URL', '')
                ai_model = getattr(config, 'AI_POSITION_MODEL', '')
                ai_check_interval = getattr(config, 'AI_POSITION_CHECK_INTERVAL', 300)

                self.ai_position_agent = AIPositionAgent(
                    api_key=ai_api_key,
                    api_url=ai_api_url,
                    model=ai_model,
                    check_interval=ai_check_interval,
                )
                self.logger.info("✅ AI 仓位管理代理已启用")
            else:
                self.logger.info("⏸️  AI 仓位管理代理未启用")
        else:
            self.logger.info("⏸️  AI 托管模式未启用，使用传统信号聚合策略")

        # 8. 初始化 AI 进化系统（如果启用）
        self.ai_evolution_enabled = getattr(config, 'ENABLE_AI_EVOLUTION', False)
        self.ai_performance_tracker = None
        self.ai_evolution_engine = None

        if self.ai_evolution_enabled:
            from binance_trader.ai_performance_tracker import AIPerformanceTracker
            from binance_trader.ai_evolution_engine import AIEvolutionEngine

            # 初始化性能追踪器
            self.ai_performance_tracker = AIPerformanceTracker("data/ai_performance.db")
            self.logger.info("✅ AI 性能追踪器已启用")

            # 初始化进化引擎
            evolution_api_key = getattr(config, 'AI_EVOLUTION_API_KEY', '')
            evolution_api_url = getattr(config, 'AI_EVOLUTION_API_URL', '')
            evolution_model = getattr(config, 'AI_EVOLUTION_MODEL', '')

            self.ai_evolution_engine = AIEvolutionEngine(
                performance_tracker=self.ai_performance_tracker,
                api_key=evolution_api_key,
                api_url=evolution_api_url,
                model=evolution_model,
            )

            # 配置进化参数
            self.ai_evolution_engine.config["min_trades_for_learning"] = getattr(
                config, 'AI_EVOLUTION_MIN_TRADES', 50
            )
            self.ai_evolution_engine.config["learning_period_days"] = getattr(
                config, 'AI_EVOLUTION_LEARNING_PERIOD_DAYS', 30
            )
            self.ai_evolution_engine.config["evolution_interval_hours"] = getattr(
                config, 'AI_EVOLUTION_INTERVAL_HOURS', 24
            )
            self.ai_evolution_engine.config["ab_testing"]["enabled"] = getattr(
                config, 'ENABLE_AI_AB_TESTING', True
            )
            self.ai_evolution_engine.config["ab_testing"]["test_ratio"] = getattr(
                config, 'AI_AB_TEST_RATIO', 0.2
            )
            # 配置进化策略
            self.ai_evolution_engine.config["evolution_profile"] = getattr(
                config, 'AI_EVOLUTION_PROFILE', 'balanced_day'
            )
            self.ai_evolution_engine._save_config()

            # 打印策略信息
            try:
                from binance_trader.ai_evolution_profiles import get_profile_config
                profile_config = get_profile_config(self.ai_evolution_engine.config["evolution_profile"])
                self.logger.info(
                    "✅ AI 自我进化系统已启用 - 策略: %s (%s)",
                    profile_config["name"],
                    profile_config["description"]
                )
            except Exception:
                self.logger.info("✅ AI 自我进化系统已启用")
        else:
            self.logger.info("⏸️  AI 自我进化系统未启用")

        # 做空配置
        self.short_stop_loss_percent = getattr(config, 'SHORT_STOP_LOSS_PERCENT', 2.0)
        self.short_take_profit_percent = getattr(config, 'SHORT_TAKE_PROFIT_PERCENT', 3.0)

        # 9. 更新账户余额
        self.trader.update_risk_manager_balance()

        # 状态跟踪
        self.last_balance_update = time.time()
        self.last_position_monitor = time.time()
        self.last_trailing_stop_check = time.time()
        self.last_evolution_check = time.time()

        # 10. 初始化时检查已有持仓，添加到追踪管理器
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
                        enabled, activation, callback = self._get_trailing_stop_settings(symbol_base)
                        if enabled:
                            self.trailing_stop_manager.add_position(
                                symbol_base,
                                position.entry_price,
                                position.mark_price,
                                activation_percent=activation,
                                callback_percent=callback,
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

    def _get_trailing_stop_settings(self, symbol_base: str):
        """
        Per-symbol trailing-stop configuration.

        Returns:
            (enabled, activation_percent, callback_percent)
        """
        try:
            strategy = self.trader.get_coin_strategy_params(symbol_base)
            enabled = bool(strategy.get("enable_trailing_stop", False))
            if not enabled:
                return False, None, None
            return True, strategy.get("trailing_activation"), strategy.get("trailing_callback")
        except Exception:
            return bool(getattr(config, "ENABLE_TRAILING_STOP", False)), None, None

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
        enable_alt_trailing = bool(getattr(config, "ENABLE_TRAILING_STOP", False))
        enable_major_trailing = bool(getattr(config, "ENABLE_MAJOR_COIN_STRATEGY", False)) and bool(
            getattr(config, "MAJOR_COIN_ENABLE_TRAILING_STOP", True)
        )
        trailing_status = []
        if enable_alt_trailing:
            trailing_status.append("山寨币")
        if enable_major_trailing:
            trailing_status.append("主流币")
        self.logger.info(f"追踪止损: {'已启用 ✅ (' + ','.join(trailing_status) + ')' if trailing_status else '已禁用'}")
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

        # 如果启用 AI 模式，忽略传统信号
        if self.ai_mode_enabled:
            self.logger.debug("AI 模式已启用，忽略传统信号: type=%s symbol=%s", message_type, symbol)
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

    def process_ai_signal(self, payload: dict):
        """
        处理 AI 信号

        Args:
            payload: AI 信号 payload，包含:
                - symbol: 币种符号
                - direction: 交易方向 (LONG/SHORT)
                - ai_data: AI 分析数据
        """
        # 检查紧急停止
        if self._check_emergency_stop():
            return

        # 检查是否启用 AI 模式
        if not self.ai_mode_enabled or not self.ai_mode_handler:
            self.logger.warning("收到 AI 信号但 AI 模式未启用，忽略")
            return

        # 使用 AI 模式处理器处理信号
        trade_signal = self.ai_mode_handler.process_ai_signal(payload)

        if not trade_signal:
            self.logger.debug("AI 信号处理失败或被过滤")
            return

        # 执行 AI 交易信号
        self._handle_ai_trade_signal(trade_signal)

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
                enabled, activation, callback = self._get_trailing_stop_settings(trade_signal.symbol)
                if enabled:
                    self.trailing_stop_manager.add_position(
                        trade_signal.symbol,
                        current_price,
                        current_price,
                        activation_percent=activation,
                        callback_percent=callback,
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

    def _handle_ai_trade_signal(self, trade_signal: dict):
        """
        处理 AI 交易信号

        Args:
            trade_signal: AI 交易信号，包含:
                - symbol: 币种符号
                - direction: 交易方向 (LONG/SHORT)
                - entry_price: 入场价格
                - stop_loss: 止损价格
                - take_profit_levels: 止盈级别 [(价格, 比例), ...]
                - confidence: 信心度 (0-1)
                - analysis: AI 分析文本
        """
        symbol = trade_signal["symbol"]
        direction = trade_signal["direction"]
        entry_price = trade_signal["entry_price"]
        stop_loss = trade_signal["stop_loss"]
        tp_levels = trade_signal.get("take_profit_levels", [])
        confidence = trade_signal.get("confidence", 0.5)
        analysis = trade_signal.get("analysis", "")

        self.logger.warning("🤖"*40)
        self.logger.warning(f"AI 交易信号: {direction} {symbol}")
        self.logger.warning(f"入场: {entry_price:.4f}, 止损: {stop_loss:.4f}")
        self.logger.warning(f"信心度: {confidence:.2f}")
        self.logger.warning(f"分析: {analysis[:100]}")
        self.logger.warning("🤖"*40)

        # 检查是否启用自动交易
        if not config.AUTO_TRADING_ENABLED:
            self.logger.info("⏸️  自动交易已禁用，跳过执行 (观察模式)")
            return

        binance_symbol = f"{symbol}{config.SYMBOL_SUFFIX}"

        # 检查是否已有持仓
        existing_position = self.trader.get_position_info(binance_symbol)
        if existing_position and existing_position.quantity != 0:
            self.logger.info(f"⏭️ {binance_symbol} 已有持仓，跳过开仓")
            return

        # 获取当前价格
        current_price = self.trader.get_symbol_price(binance_symbol)
        if not current_price:
            self.logger.error(f"获取 {binance_symbol} 价格失败，跳过交易")
            return

        # 根据信心度调整仓位大小
        base_position_percent = config.MAX_POSITION_PERCENT
        adjusted_position_percent = base_position_percent * confidence
        self.logger.info(f"根据 AI 信心度调整仓位: {base_position_percent}% × {confidence:.2f} = {adjusted_position_percent:.2f}%")

        # 生成交易建议（使用 AI 提供的价格）
        from binance_trader.risk_manager import TradeRecommendation

        recommendation = TradeRecommendation(
            action="BUY" if direction == "LONG" else "SELL",
            symbol=symbol,
            quantity=0,  # 将由 trader 计算
            entry_price=current_price,
            stop_loss=stop_loss,
            take_profit=tp_levels[0][0] if tp_levels else None,
            position_size_percent=adjusted_position_percent,
            reason=f"AI 信号 (confidence={confidence:.2f})",
        )

        # 执行交易
        leverage = self._get_leverage(symbol)

        if direction == "LONG":
            success = self.trader.open_long_position(
                recommendation,
                symbol_suffix=config.SYMBOL_SUFFIX,
                leverage=leverage,
                margin_type=config.MARGIN_TYPE,
            )
        else:  # SHORT
            success = self.trader.open_short_position(
                recommendation,
                symbol_suffix=config.SYMBOL_SUFFIX,
                leverage=leverage,
                margin_type=config.MARGIN_TYPE,
            )

        if success:
            self.logger.info(f"✅ AI 交易执行成功: {direction} {symbol}")

            # 记录到性能追踪器
            if self.ai_performance_tracker:
                trade_id = f"{symbol}_{int(time.time())}"
                self.ai_performance_tracker.record_trade_entry(
                    trade_id=trade_id,
                    symbol=symbol,
                    direction=direction,
                    entry_price=current_price,
                    quantity=recommendation.quantity if hasattr(recommendation, 'quantity') else 0,
                    ai_analysis=analysis,
                    ai_confidence=confidence,
                    ai_stop_loss=stop_loss,
                    ai_take_profit=tp_levels[0][0] if tp_levels else None,
                    ai_risk_level=trade_signal.get("risk_level", "medium"),
                    market_conditions={
                        "timestamp": int(time.time()),
                        "price": current_price,
                    },
                )

            # 添加到移动止损跟踪
            if self.trailing_stop_manager:
                enabled, activation, callback = self._get_trailing_stop_settings(symbol)
                if enabled:
                    self.trailing_stop_manager.add_position(
                        symbol,
                        current_price,
                        current_price,
                        activation_percent=activation,
                        callback_percent=callback,
                    )

            # 添加到分批止盈跟踪
            if self.pyramiding_manager:
                self.pyramiding_manager.add_position(symbol, current_price)

        else:
            self.logger.error(f"❌ AI 交易执行失败: {direction} {symbol}")

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
                    enabled, activation, callback = self._get_trailing_stop_settings(confluence.symbol)
                    if enabled:
                        self.trailing_stop_manager.add_position(
                            confluence.symbol,
                            current_price,
                            current_price,
                            activation_percent=activation,
                            callback_percent=callback,
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
                        enabled, activation, callback = self._get_trailing_stop_settings(symbol_base)
                        if enabled:
                            self.trailing_stop_manager.add_position(
                                symbol_base,
                                position.entry_price,
                                position.mark_price,
                                activation_percent=activation,
                                callback_percent=callback,
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

            enabled, activation, callback = self._get_trailing_stop_settings(symbol_base)
            if not enabled:
                if symbol_base in self.trailing_stop_manager.tracking_data:
                    self.trailing_stop_manager.remove_position(symbol_base)
                continue

            if symbol_base not in self.trailing_stop_manager.tracking_data:
                self.trailing_stop_manager.add_position(
                    symbol_base,
                    position.entry_price,
                    position.mark_price,
                    activation_percent=activation,
                    callback_percent=callback,
                )
            else:
                tracking = self.trailing_stop_manager.tracking_data.get(symbol_base) or {}
                if activation is not None:
                    tracking["activation_percent"] = activation
                if callback is not None:
                    tracking["callback_percent"] = callback

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

    def check_ai_evolution(self):
        """检查并执行 AI 进化"""
        if not self.ai_evolution_enabled or not self.ai_evolution_engine:
            return

        now = time.time()
        # 每小时检查一次
        if now - self.last_evolution_check < 3600:
            return

        self.last_evolution_check = now

        try:
            if self.ai_evolution_engine.should_evolve():
                self.logger.info("🧬 开始 AI 进化过程...")
                evolution_result = self.ai_evolution_engine.analyze_and_evolve()

                if evolution_result:
                    self.logger.info("🧬 AI 进化完成!")
                    self.logger.info("  - 分析交易数: %d", evolution_result["trades_analyzed"])
                    self.logger.info("  - 预期改进: %.2f%%", evolution_result["expected_improvement"])

                    # 打印洞察
                    for insight in evolution_result.get("insights", []):
                        self.logger.info("  💡 %s", insight)

                    # 如果启用了 A/B 测试
                    if self.ai_evolution_engine.config["ab_testing"]["enabled"]:
                        self.logger.info(
                            "  🧪 A/B 测试已启动: %.0f%% 使用新策略",
                            self.ai_evolution_engine.config["ab_testing"]["test_ratio"] * 100,
                        )
                    else:
                        self.logger.info("  ✅ 新策略已应用")

        except Exception as e:
            self.logger.error("AI 进化失败: %s", e)
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
                self.check_ai_evolution()  # AI 进化检查

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

                    # 打印 AI 性能统计（如果启用）
                    if self.ai_performance_tracker:
                        perf_stats = self.ai_performance_tracker.get_performance_stats(days=7)
                        if perf_stats:
                            self.logger.info(
                                f"🤖 AI 性能 (7天): "
                                f"交易={perf_stats['closed_trades']}, "
                                f"胜率={perf_stats['win_rate']:.1f}%, "
                                f"总盈亏={perf_stats['total_pnl']:.2f}"
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
