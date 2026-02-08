"""
Telegram 跟单交易主程序
整合 Telegram 监控 + 信号解析 + 合约交易执行
"""

import sys
import os
import time
import asyncio
import logging
import contextlib
from datetime import datetime
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from telegram_copytrade.signal_parser import TradeSignal
from telegram_copytrade.telegram_client import TelegramMonitor

try:
    from telegram_copytrade import config
except ImportError:
    print("❌ Error: config.py not found!")
    print("Please copy config.example.py to config.py and fill in your settings.")
    sys.exit(1)

from binance_trader.risk_manager import RiskManager
from binance_trader.futures_trader import BinanceFuturesTrader
from binance_trader.trailing_stop import TrailingStopManager, PyramidingExitManager


class CopyTradeSystem:
    """Telegram 跟单交易系统"""
    
    def __init__(self):
        """初始化系统"""
        self._setup_logging()
        self.logger = logging.getLogger(__name__)
        
        self.logger.info("="*80)
        self.logger.info("🚀 初始化 Telegram 跟单交易系统")
        self.logger.info("="*80)

        # 如果未启用跟单，进入空闲模式：不初始化 Telegram/币安，避免任何副作用
        self.copytrade_enabled = bool(getattr(config, "COPYTRADE_ENABLED", False))
        if not self.copytrade_enabled:
            self.logger.warning("⏸️ COPYTRADE_ENABLED=False，跟单模块空闲，不连接 Telegram/币安。")
            self.risk_manager = None
            self.trader = None
            self.trailing_stop_manager = None
            self.telegram_monitor = None
            self.last_position_monitor = time.time()
            self.positions_tracked = {}
            return
        
        # 1. 初始化风险管理器
        self.risk_manager = RiskManager(
            max_position_percent=config.MAX_POSITION_PERCENT,
            max_total_position_percent=config.MAX_TOTAL_POSITION_PERCENT,
            max_daily_trades=config.MAX_DAILY_TRADES,
            max_daily_loss_percent=config.MAX_DAILY_LOSS_PERCENT,
            stop_loss_percent=config.STOP_LOSS_PERCENT,
            take_profit_1_percent=config.TAKE_PROFIT_1_PERCENT,
            take_profit_2_percent=config.TAKE_PROFIT_2_PERCENT
        )
        
        # 2. 初始化合约交易器
        api_key = config.BINANCE_API_KEY
        api_secret = config.BINANCE_API_SECRET
        
        # 如果未配置，尝试从 binance_trader 读取
        if not api_key or not api_secret:
            try:
                from binance_trader import config as trader_config
                api_key = trader_config.BINANCE_API_KEY
                api_secret = trader_config.BINANCE_API_SECRET
            except ImportError:
                pass
        
        if not api_key or not api_secret:
            self.logger.error("❌ 未配置币安 API 凭证")
            sys.exit(1)
        
        proxy = getattr(config, 'SOCKS5_PROXY', None)
        api_timeout = getattr(config, 'API_TIMEOUT', 30)
        api_retry_count = getattr(config, 'API_RETRY_COUNT', 3)
        enable_proxy_fallback = getattr(config, 'ENABLE_PROXY_FALLBACK', True)

        # 交易器初始化可能因网络/代理问题失败，增加重试以避免服务反复重启
        init_attempts = 5
        init_delay = 5
        self.trader = None
        for attempt in range(1, init_attempts + 1):
            try:
                self.trader = BinanceFuturesTrader(
                    api_key=api_key,
                    api_secret=api_secret,
                    risk_manager=self.risk_manager,
                    leverage=config.LEVERAGE if isinstance(config.LEVERAGE, int) else 10,
                    margin_type=config.MARGIN_TYPE,
                    testnet=config.USE_TESTNET,
                    proxy=proxy,
                    api_timeout=api_timeout,
                    api_retry_count=api_retry_count,
                    enable_proxy_fallback=enable_proxy_fallback
                )
                break
            except Exception as e:
                self.logger.error(
                    f"❌ 初始化币安交易器失败 (尝试 {attempt}/{init_attempts}): {e}"
                )
                if attempt >= init_attempts:
                    raise
                time.sleep(init_delay)
                init_delay = min(init_delay * 2, 60)

        assert self.trader is not None
        
        # 3. 初始化移动止损管理器
        self.trailing_stop_manager = None
        if config.ENABLE_TRAILING_STOP:
            self.trailing_stop_manager = TrailingStopManager(
                activation_percent=config.TRAILING_STOP_ACTIVATION,
                callback_percent=config.TRAILING_STOP_CALLBACK
            )
            self.logger.info("✅ 追踪止损已启用")
        
        # 4. 初始化 Telegram 监控器
        self.telegram_monitor = TelegramMonitor(
            api_id=config.TELEGRAM_API_ID,
            api_hash=config.TELEGRAM_API_HASH,
            session_name="copytrade_session",
            proxy=self._parse_proxy(proxy) if proxy else None
        )
        self.telegram_monitor.set_monitor_group_ids(config.MONITOR_GROUP_IDS)
        self.telegram_monitor.set_signal_user_ids(getattr(config, 'SIGNAL_USER_IDS', []))
        self.telegram_monitor.set_signal_callback(self._on_signal)
        
        # 状态跟踪
        self.last_position_monitor = time.time()
        self.positions_tracked = {}  # symbol -> entry_price
        
        self.logger.info("✅ 系统初始化成功")
        self._print_status()
    
    def _setup_logging(self):
        """配置日志"""
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
    
    def _parse_proxy(self, proxy_str: str) -> Optional[dict]:
        """解析代理字符串"""
        if not proxy_str or not proxy_str.startswith("socks5://"):
            return None
        
        # socks5://127.0.0.1:1080
        addr = proxy_str.replace("socks5://", "")
        if ":" in addr:
            host, port = addr.split(":")
            return {
                "proxy_type": "socks5",
                "addr": host,
                "port": int(port)
            }
        return None
    
    def _print_status(self):
        """打印系统状态"""
        self.logger.info("="*80)
        self.logger.info("📊 跟单系统状态")
        self.logger.info("="*80)
        self.logger.info(f"跟单模式: {'测试网 ⚠️' if config.USE_TESTNET else '生产环境 🔴'}")
        self.logger.info(f"跟单启用: {'✅' if config.COPYTRADE_ENABLED else '❌'}")
        self.logger.info(f"跟单模式: {config.COPYTRADE_MODE}")
        self.logger.info(f"固定仓位: {config.FIXED_POSITION_SIZE} USDT")
        self.logger.info(f"杠杆倍数: {config.LEVERAGE}x")
        self.logger.info(f"止损: {config.STOP_LOSS_PERCENT}%")
        self.logger.info(f"止盈: {config.TAKE_PROFIT_1_PERCENT}% / {config.TAKE_PROFIT_2_PERCENT}% / {config.TAKE_PROFIT_3_PERCENT}%")
        self.logger.info(f"监控群组ID: {config.MONITOR_GROUP_IDS}")
        self.logger.info("="*80)
    
    def _on_signal(self, signal: TradeSignal):
        """处理收到的信号"""
        self.logger.info(f"📨 收到信号: {signal.signal_type} {signal.symbol} {signal.direction}")
        
        if not config.COPYTRADE_ENABLED:
            self.logger.info("⏸️ 跟单已禁用，忽略信号")
            return
        
        # 信号过滤
        if not self._filter_signal(signal):
            return
        
        if signal.signal_type == "OPEN":
            self._handle_open_signal(signal)
        elif signal.signal_type == "CLOSE":
            self._handle_close_signal(signal)
    
    def _filter_signal(self, signal: TradeSignal) -> bool:
        """过滤信号"""
        # 杠杆过滤
        if signal.leverage < config.MIN_LEVERAGE or signal.leverage > config.MAX_LEVERAGE:
            self.logger.info(f"⚠️ 杠杆 {signal.leverage}x 超出范围，忽略")
            return False
        
        # 方向过滤
        if config.DIRECTION_FILTER != "BOTH":
            if config.DIRECTION_FILTER == "LONG" and signal.direction != "LONG":
                self.logger.info(f"⚠️ 只跟做多，忽略做空信号")
                return False
            if config.DIRECTION_FILTER == "SHORT" and signal.direction != "SHORT":
                self.logger.info(f"⚠️ 只跟做空，忽略做多信号")
                return False
        
        # 币种白名单
        symbol_base = signal.symbol.replace("USDT", "")
        if config.SYMBOL_WHITELIST and symbol_base not in config.SYMBOL_WHITELIST:
            self.logger.info(f"⚠️ {symbol_base} 不在白名单中，忽略")
            return False
        
        # 币种黑名单
        if symbol_base in config.SYMBOL_BLACKLIST:
            self.logger.info(f"⚠️ {symbol_base} 在黑名单中，忽略")
            return False
        
        return True
    
    def _handle_open_signal(self, signal: TradeSignal):
        """处理开仓信号"""
        self.logger.warning("🔥" * 40)
        self.logger.warning(f"📈 跟单开仓: {signal.symbol} {signal.direction} {signal.leverage}x")
        self.logger.warning("🔥" * 40)
        
        # 检查是否已有持仓
        if signal.symbol in self.trader.positions:
            self.logger.info(f"⚠️ 已有 {signal.symbol} 持仓，跳过")
            return
        
        # 计算仓位大小
        position_usdt = config.FIXED_POSITION_SIZE
        if position_usdt > config.MAX_SINGLE_TRADE_VALUE:
            position_usdt = config.MAX_SINGLE_TRADE_VALUE
        
        # 获取当前价格
        current_price = signal.current_price or signal.entry_price
        if not current_price:
            current_price = self.trader.get_symbol_price(signal.symbol)
        
        if not current_price:
            self.logger.error(f"❌ 无法获取 {signal.symbol} 价格")
            return
        
        # 计算数量
        quantity = position_usdt / current_price
        
        # 使用配置的杠杆或跟随信号
        leverage = config.LEVERAGE if isinstance(config.LEVERAGE, int) else signal.leverage
        
        # 计算止损止盈价格
        if signal.direction == "LONG":
            stop_loss = current_price * (1 - config.STOP_LOSS_PERCENT / 100)
            take_profit_1 = current_price * (1 + config.TAKE_PROFIT_1_PERCENT / 100)
            take_profit_2 = current_price * (1 + config.TAKE_PROFIT_2_PERCENT / 100)
        else:
            stop_loss = current_price * (1 + config.STOP_LOSS_PERCENT / 100)
            take_profit_1 = current_price * (1 - config.TAKE_PROFIT_1_PERCENT / 100)
            take_profit_2 = current_price * (1 - config.TAKE_PROFIT_2_PERCENT / 100)
        
        # 生成交易建议
        from binance_trader.risk_manager import TradeRecommendation
        
        recommendation = TradeRecommendation(
            action="BUY" if signal.direction == "LONG" else "SELL",
            symbol=signal.symbol.replace("USDT", ""),
            quantity=quantity,
            price=current_price,
            stop_loss=stop_loss,
            take_profit_1=take_profit_1,
            take_profit_2=take_profit_2,
            risk_level="MEDIUM",
            reason=f"Telegram 跟单: {signal.direction} {signal.leverage}x"
        )
        
        # 执行交易
        if signal.direction == "LONG":
            success = self.trader.open_long_position(
                recommendation,
                symbol_suffix="USDT",
                leverage=leverage,
                margin_type=config.MARGIN_TYPE
            )
        else:
            # 做空
            success = self.trader.open_short_position(
                recommendation,
                symbol_suffix="USDT",
                leverage=leverage,
                margin_type=config.MARGIN_TYPE
            )
        
        if success:
            self.logger.info(f"✅ 跟单成功: {signal.symbol} {signal.direction}")
            self.positions_tracked[signal.symbol] = {
                "entry_price": current_price,
                "direction": signal.direction,
                "leverage": leverage
            }
            
            # 添加到移动止损
            if self.trailing_stop_manager:
                self.trailing_stop_manager.add_position(
                    signal.symbol.replace("USDT", ""),
                    current_price,
                    current_price
                )
        else:
            self.logger.error(f"❌ 跟单失败: {signal.symbol}")
    
    def _handle_close_signal(self, signal: TradeSignal):
        """处理平仓信号"""
        self.logger.warning("="*60)
        self.logger.warning(f"📉 收到平仓信号: {signal.symbol} {signal.direction}")
        self.logger.warning(f"   开仓价: {signal.entry_price}")
        self.logger.warning(f"   平仓价: {signal.current_price}")
        self.logger.warning(f"   收益: {signal.pnl:+.2f} USDT ({signal.pnl_percent:+.2f}%)")
        self.logger.warning("="*60)
        
        # 检查是否启用跟随平仓
        follow_close = getattr(config, 'FOLLOW_CLOSE_SIGNAL', False)
        if not follow_close and config.COPYTRADE_MODE != "FULL":
            self.logger.info(f"⚠️ 跟随平仓未启用，不跟平仓信号")
            return
        
        if signal.symbol not in self.trader.positions:
            self.logger.info(f"⚠️ 无 {signal.symbol} 持仓，忽略平仓信号")
            return
        
        self.logger.warning(f"� 执行跟单平仓: {signal.symbol}")
        
        success = self.trader.close_position(signal.symbol, reason=f"Telegram跟单平仓 (信号收益: {signal.pnl:+.2f} USDT)")
        if success:
            self.logger.info(f"✅ 平仓成功: {signal.symbol}")
            
            # 记录跟单收益
            if signal.symbol in self.positions_tracked:
                tracked = self.positions_tracked[signal.symbol]
                if isinstance(tracked, dict):
                    entry = tracked.get("entry_price", 0)
                    self.logger.info(f"   我方开仓价: {entry}")
                del self.positions_tracked[signal.symbol]
            
            # 清理移动止损
            if self.trailing_stop_manager:
                symbol_base = signal.symbol.replace("USDT", "")
                if symbol_base in self.trailing_stop_manager.positions:
                    del self.trailing_stop_manager.positions[symbol_base]
        else:
            self.logger.error(f"❌ 平仓失败: {signal.symbol}")
    
    def monitor_positions(self):
        """监控持仓"""
        now = time.time()
        if now - self.last_position_monitor >= 10:  # 每10秒
            self.trader.monitor_positions()
            self.last_position_monitor = now
    
    async def run(self):
        """运行跟单系统"""
        if not getattr(self, "copytrade_enabled", False):
            self.logger.info("⏸️ 跟单未启用，保持空闲状态。")
            while True:
                await asyncio.sleep(60)

        self.logger.info("📡 启动 Telegram 跟单系统...")

        # 启动位置监控任务
        async def position_monitor_loop():
            while True:
                self.monitor_positions()
                await asyncio.sleep(10)

        monitor_task = asyncio.create_task(position_monitor_loop())

        base_backoff = 5
        max_backoff = 120
        backoff = base_backoff

        try:
            while True:
                start_ts = time.time()
                try:
                    await self.telegram_monitor.start()
                    # run_until_disconnected 正常返回 => 断连
                    self.logger.warning("⚠️ Telegram 连接断开，准备重连...")
                    run_seconds = time.time() - start_ts
                    if run_seconds >= 60:
                        backoff = base_backoff
                except asyncio.CancelledError:
                    raise
                except KeyboardInterrupt:
                    self.logger.info("🛑 正在关闭...")
                    break
                except Exception as e:
                    self.logger.exception(f"❌ Telegram 监控异常: {e}")
                    backoff = min(backoff * 2, max_backoff)
                finally:
                    with contextlib.suppress(Exception):
                        await self.telegram_monitor.stop()

                await asyncio.sleep(backoff)
        finally:
            monitor_task.cancel()
            with contextlib.suppress(Exception):
                await monitor_task


def main():
    """主函数"""
    print("\n" + "="*80)
    print("🚀 Telegram 跟单交易系统")
    print("="*80)
    print("\n⚠️ 警告: 这是带杠杆的期货交易")
    print("   请确保已正确配置并了解风险！\n")
    
    system = CopyTradeSystem()
    asyncio.run(system.run())


if __name__ == "__main__":
    main()
