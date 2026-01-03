"""
币安合约交易器 - Binance Futures Trader
负责执行合约交易操作，包括开仓、平仓、移动止损等
"""

import time
import logging
import threading
from decimal import Decimal, ROUND_DOWN, ROUND_UP
from typing import Dict, Optional, List, Tuple
from datetime import datetime
import requests
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceOrderException
from .risk_manager import RiskManager, TradeRecommendation
from .trade_notifier import TradeNotifier


class PositionInfo:
    """合约持仓信息"""
    def __init__(self, data: Dict):
        self.symbol = data.get('symbol', '')
        self.position_side = data.get('positionSide', 'BOTH')
        self.quantity = float(data.get('positionAmt', 0))
        self.entry_price = float(data.get('entryPrice', 0))
        self.mark_price = float(data.get('markPrice', 0))
        self.unrealized_pnl = float(data.get('unRealizedProfit', 0))
        self.leverage = int(data.get('leverage', 1))
        self.liquidation_price = float(data.get('liquidationPrice', 0))
        self.margin_type = data.get('marginType', 'isolated')

        # 计算盈亏百分比
        if self.entry_price > 0:
            self.unrealized_pnl_percent = ((self.mark_price - self.entry_price) / self.entry_price) * 100
        else:
            self.unrealized_pnl_percent = 0.0

        # 移动止损相关
        self.highest_price = self.mark_price  # 持仓以来的最高价
        self.trailing_stop_activated = False  # 移动止损是否已激活
        self.trailing_stop_price = 0.0  # 当前移动止损价格


class BinanceFuturesTrader:
    """
    币安合约交易执行器

    核心功能：
    1. 连接币安合约 API
    2. 设置杠杆和保证金模式
    3. 执行市价开仓
    4. 管理止损止盈订单
    5. 实现移动止损策略
    6. 分批止盈管理
    7. 强平风险监控
    """

    def __init__(self,
                 api_key: str,
                 api_secret: str,
                 risk_manager: RiskManager,
                 leverage: int = 10,
                 margin_type: str = "ISOLATED",
                 testnet: bool = False,
                 proxy: Optional[str] = None,
                 api_timeout: int = 30,
                 api_retry_count: int = 3,
                 enable_proxy_fallback: bool = True):
        """
        初始化合约交易器

        Args:
            api_key: Binance API Key
            api_secret: Binance API Secret
            risk_manager: 风险管理器实例
            leverage: 杠杆倍数（1-125）
            margin_type: 保证金模式 ISOLATED/CROSSED
            testnet: 是否使用测试网
            proxy: SOCKS5代理 (格式: socks5://user:pass@host:port)
            api_timeout: API 请求超时（秒）
            api_retry_count: 网络错误重试次数（仅用于只读请求）
            enable_proxy_fallback: 代理失败时是否自动切换直连
        """
        self.risk_manager = risk_manager
        self.leverage = leverage
        self.margin_type = margin_type
        self.testnet = testnet
        self.logger = logging.getLogger(__name__)
        self._config = None
        self._use_hedge_mode = None
        self.enable_trailing_stop = False

        self.api_timeout = int(api_timeout) if api_timeout else 30
        self.api_retry_count = max(1, int(api_retry_count) if api_retry_count else 1)
        self.enable_proxy_fallback = bool(enable_proxy_fallback)

        # Time sync to prevent Binance APIError(code=-1021) timestamp drift.
        self._time_sync_lock = threading.Lock()
        self._last_time_sync_monotonic = 0.0
        try:
            import config as _local_config  # type: ignore

            self.time_sync_interval = int(getattr(_local_config, "BINANCE_TIME_SYNC_INTERVAL", 300) or 300)
            self.time_sync_safety_ms = int(getattr(_local_config, "BINANCE_TIME_SYNC_SAFETY_MS", 1500) or 1500)
            self.recv_window_ms = int(getattr(_local_config, "BINANCE_RECV_WINDOW_MS", 10000) or 10000)
        except Exception:
            self.time_sync_interval = 300
            self.time_sync_safety_ms = 1500
            self.recv_window_ms = 10000

        self._proxy = proxy.strip() if isinstance(proxy, str) and proxy.strip() else None
        self._proxy_display = None
        self._proxy_client: Optional[Client] = None
        self._direct_client: Optional[Client] = None

        # 配置代理/超时（python-binance 会把 requests_params 合并到每次请求）
        requests_params = {'timeout': self.api_timeout}
        if self._proxy:
            # 隐藏敏感信息，只显示主机:端口
            self._proxy_display = self._proxy.split('@')[-1] if '@' in self._proxy else self._proxy
            self.logger.info(f"🌐 使用 SOCKS5 代理: {self._proxy_display}")
            requests_params['proxies'] = {'http': self._proxy, 'https': self._proxy}

        # 初始化 Binance 客户端
        # 注意: python-binance 默认会在 __init__ 执行现货 ping；受限地区可能直接报错，
        # 这里用 ping=False 跳过，并用 futures_ping/futures_time 做合约连通性检测。
        self.client = Client(
            api_key,
            api_secret,
            testnet=testnet,
            ping=False,
            requests_params=requests_params
        )
        self._proxy_client = self.client
        if self._proxy:
            proxy_session = {'http': self._proxy, 'https': self._proxy}
            self._configure_session(self.client, proxies=proxy_session)

        if self.enable_proxy_fallback:
            self._direct_client = Client(
                api_key,
                api_secret,
                testnet=testnet,
                ping=False,
                requests_params={'timeout': self.api_timeout}
            )
            self._configure_session(self._direct_client, proxies=None)

        if testnet:
            # 设置合约测试网 URL (必须在任何 API 调用之前设置)
            # 注意: 币安测试网已迁移到 demo.binance.com
            # 但 API 端点仍然使用 testnet.binancefuture.com
            self.client.FUTURES_URL = 'https://testnet.binancefuture.com/fapi'
            if self._direct_client:
                self._direct_client.FUTURES_URL = 'https://testnet.binancefuture.com/fapi'

        # 启用时间戳自动同步，解决时间差问题
        # 这会在首次 API 调用时自动获取服务器时间并调整
        self.client.timestamp_offset = 0
        if self._direct_client:
            self._direct_client.timestamp_offset = 0

        if testnet:
            self.logger.warning("⚠️  运行于合约测试网模式")
        else:
            self.logger.info("运行于合约生产环境模式")

        # 持仓信息缓存
        self.positions: Dict[str, PositionInfo] = {}

        # 已执行的分批止盈级别（避免重复执行）
        self.executed_tp_levels: Dict[str, set] = {}

        # 缓存交易对规则，避免重复请求交易所信息
        self._symbol_info_cache: Dict[str, Dict] = {}

        # 初始化 Telegram 通知器
        try:
            import config
            self._config = config
            self.enable_trailing_stop = bool(getattr(config, 'ENABLE_TRAILING_STOP', False))
            enabled = getattr(config, 'ENABLE_TRADE_NOTIFICATIONS', False)
            bot_token = getattr(config, 'TELEGRAM_BOT_TOKEN', '')
            chat_id = getattr(config, 'TELEGRAM_CHAT_ID', '')
            self.notifier = TradeNotifier(
                bot_token=bot_token,
                chat_id=chat_id,
                enabled=enabled,
                proxy=proxy
            )

            # 保存通知开关
            self.notify_open = getattr(config, 'NOTIFY_OPEN_POSITION', True)
            self.notify_close = getattr(config, 'NOTIFY_CLOSE_POSITION', True)
            self.notify_stop_loss = getattr(config, 'NOTIFY_STOP_LOSS', True)
            self.notify_take_profit = getattr(config, 'NOTIFY_TAKE_PROFIT', True)
            self.notify_partial = getattr(config, 'NOTIFY_PARTIAL_CLOSE', True)
            self.notify_errors = getattr(config, 'NOTIFY_ERRORS', True)

            # 开仓前清理旧挂单（防止旧止盈/止损残留）
            self.cancel_exit_orders_before_entry = getattr(
                config, 'CANCEL_EXIT_ORDERS_BEFORE_ENTRY', True
            )
            self.exit_order_types_to_cancel = getattr(
                config,
                'EXIT_ORDER_TYPES_TO_CANCEL',
                ['STOP_MARKET', 'TAKE_PROFIT_MARKET', 'STOP', 'TAKE_PROFIT', 'TRAILING_STOP_MARKET']
            )

            # 金字塔止盈配置：前端可设置 3 个止盈点，落在 PYRAMIDING_EXIT_LEVELS
            self.enable_pyramiding_exit = getattr(config, 'ENABLE_PYRAMIDING_EXIT', False)
            self.pyramiding_exit_levels = getattr(config, 'PYRAMIDING_EXIT_LEVELS', []) or []
            self.pyramiding_exit_execution = str(
                getattr(config, 'PYRAMIDING_EXIT_EXECUTION', 'orders')
            ).strip().lower() or 'orders'

            # 做空金字塔止盈配置
            self.short_enable_pyramiding_exit = getattr(config, 'SHORT_ENABLE_PYRAMIDING_EXIT', False)
            self.short_pyramiding_exit_levels = getattr(config, 'SHORT_PYRAMIDING_EXIT_LEVELS', []) or []

            # 主流币独立策略配置
            self.enable_major_coin_strategy = getattr(config, 'ENABLE_MAJOR_COIN_STRATEGY', True)
            self.major_coins = set(s.upper() for s in getattr(config, 'MAJOR_COINS', ['BTC', 'ETH', 'BNB', 'SOL', 'XRP']))
            self.major_coin_stop_loss_percent = float(getattr(config, 'MAJOR_COIN_STOP_LOSS_PERCENT', 1.5) or 1.5)
            self.major_coin_pyramiding_exit_levels = getattr(config, 'MAJOR_COIN_PYRAMIDING_EXIT_LEVELS', [
                (1.5, 0.3), (2.5, 0.4), (4.0, 1.0)
            ]) or []
            self.major_coin_enable_trailing_stop = bool(
                getattr(config, 'MAJOR_COIN_ENABLE_TRAILING_STOP', True)
            )
            self.major_coin_trailing_stop_activation = float(getattr(config, 'MAJOR_COIN_TRAILING_STOP_ACTIVATION', 1.0) or 1.0)
            self.major_coin_trailing_stop_callback = float(getattr(config, 'MAJOR_COIN_TRAILING_STOP_CALLBACK', 0.8) or 0.8)

            # Safety: if SL/TP orders were not placed successfully, enforce exits
            # once price goes beyond configured thresholds.
            self.safety_force_exit_unprotected = bool(
                getattr(config, 'SAFETY_FORCE_EXIT_UNPROTECTED', True)
            )
            self.safety_min_action_interval = int(
                getattr(config, 'SAFETY_MIN_ACTION_INTERVAL', 15) or 15
            )
            self.safety_use_pyramiding_levels = bool(
                getattr(config, 'SAFETY_USE_PYRAMIDING_LEVELS', True)
            )
            self.safety_force_stop_loss_percent = float(
                getattr(config, 'SAFETY_FORCE_STOP_LOSS_PERCENT', 0) or 0
            )
        except Exception as e:
            self.logger.debug(f"未找到本地 config 模块，将尝试从 signal_monitor 加载: {e}")
            # 不传入 enabled=False，让 TradeNotifier 自己决定是否启用（会尝试从 signal_monitor 加载）
            self._config = None
            self.enable_trailing_stop = False
            self.notifier = TradeNotifier(proxy=proxy)
            # 使用默认通知开关
            self.notify_open = True
            self.notify_close = True
            self.notify_stop_loss = True
            self.notify_take_profit = True
            self.notify_partial = True
            self.notify_errors = True
            self.cancel_exit_orders_before_entry = True
            self.exit_order_types_to_cancel = [
                'STOP_MARKET',
                'TAKE_PROFIT_MARKET',
                'STOP',
                'TAKE_PROFIT',
                'TRAILING_STOP_MARKET',
            ]
            self.enable_pyramiding_exit = False
            self.pyramiding_exit_levels = []
            self.pyramiding_exit_execution = 'orders'
            self.short_enable_pyramiding_exit = False
            self.short_pyramiding_exit_levels = []
            self.safety_force_exit_unprotected = True
            self.safety_min_action_interval = 15
            self.safety_use_pyramiding_levels = True
            self.safety_force_stop_loss_percent = 0.0
            # 主流币策略默认值
            self.enable_major_coin_strategy = True
            self.major_coins = {'BTC', 'ETH', 'BNB', 'SOL', 'XRP'}
            self.major_coin_stop_loss_percent = 1.5
            self.major_coin_pyramiding_exit_levels = [(1.5, 0.3), (2.5, 0.4), (4.0, 1.0)]
            self.major_coin_enable_trailing_stop = True
            self.major_coin_trailing_stop_activation = 1.0
            self.major_coin_trailing_stop_callback = 0.8

        # 测试连接并同步时间（代理失败时自动切换直连）
        self._init_connectivity()
        self._use_hedge_mode = self._detect_hedge_mode()

        self._safety_last_action_ts: Dict[str, float] = {}
        
        # 初始化性能记录器
        try:
            from .performance_recorder import PerformanceRecorder
            trader_id = getattr(config, 'TRADER_ID', 'default') if 'config' in dir() else 'default'
            self.performance_recorder = PerformanceRecorder(trader_id=trader_id)
        except Exception as e:
            self.logger.debug(f"Performance recorder not available: {e}")
            self.performance_recorder = None

    def _configure_session(self, client: Client, proxies: Optional[Dict[str, str]] = None) -> None:
        session = getattr(client, "session", None)
        if session is None:
            return
        session.trust_env = False
        try:
            session.proxies = {} if proxies is None else dict(proxies)
        except Exception:
            pass

    def _is_timeout_error(self, exc: Exception) -> bool:
        if isinstance(exc, requests.exceptions.Timeout):
            return True
        msg = str(exc).lower()
        return "timed out" in msg or "timeout" in msg

    def _is_network_error(self, exc: Exception) -> bool:
        if isinstance(exc, requests.exceptions.RequestException):
            return True
        msg = str(exc)
        network_markers = [
            "ConnectionPool",
            "Read timed out",
            "Max retries exceeded",
            "Connection refused",
            "Connection reset",
            "Name or service not known",
            "Temporary failure in name resolution",
        ]
        return any(marker in msg for marker in network_markers)

    def _get_alternate_client(self) -> Optional[Client]:
        if not self._proxy_client or not self._direct_client:
            return None
        return self._direct_client if self.client is self._proxy_client else self._proxy_client

    def _set_active_client(self, client: Client, reason: str) -> None:
        if self.client is client:
            return

        old_transport = "proxy" if self._proxy_client and self.client is self._proxy_client else "direct"
        new_transport = "proxy" if self._proxy_client and client is self._proxy_client else "direct"

        try:
            client.timestamp_offset = getattr(self.client, "timestamp_offset", 0)
        except Exception:
            pass

        self.client = client

        if old_transport == "proxy" and new_transport == "direct":
            self.logger.warning(f"🔁 Binance API 连接切换: SOCKS5代理 -> 直连 ({reason})")
        elif old_transport == "direct" and new_transport == "proxy":
            self.logger.warning(f"🔁 Binance API 连接切换: 直连 -> SOCKS5代理 ({reason})")

    def _ping_and_sync_time(self, client: Client) -> None:
        client.futures_ping()

        server_time_response = client.futures_time()
        server_time = server_time_response['serverTime']
        local_time = int(time.time() * 1000)
        raw_offset = server_time - local_time
        safety_ms = int(getattr(self, "time_sync_safety_ms", 0) or 0)
        applied_offset = raw_offset - safety_ms

        client.timestamp_offset = applied_offset
        self._last_time_sync_monotonic = time.monotonic()

        if abs(raw_offset) > 500:
            self.logger.warning(
                "⚠️  检测到较大时间差，已自动调整: "
                f"raw_offset={raw_offset}ms safety={safety_ms}ms applied_offset={applied_offset}ms"
            )
        else:
            self.logger.info(
                f"⏰ 时间同步: raw_offset={raw_offset}ms safety={safety_ms}ms applied_offset={applied_offset}ms"
            )

    def _init_connectivity(self) -> None:
        try:
            self._ping_and_sync_time(self.client)
            self.logger.info("✅ 币安合约 API 连接成功")
            if self._direct_client:
                self._direct_client.timestamp_offset = self.client.timestamp_offset
            return
        except Exception as exc:
            if not (self._direct_client and self.enable_proxy_fallback and self._is_network_error(exc)):
                self.logger.error(f"❌ 币安合约 API 连接失败: {exc}")
                raise

            self.logger.warning(f"⚠️  代理连接 Binance 失败，尝试直连: {exc}")
            try:
                self._ping_and_sync_time(self._direct_client)
                self._set_active_client(self._direct_client, reason="init fallback")
                self.logger.info("✅ 币安合约 API 直连成功")
                if self._proxy_client:
                    self._proxy_client.timestamp_offset = self.client.timestamp_offset
            except Exception as exc2:
                self.logger.error(f"❌ 币安合约 API 连接失败: {exc2}")
                raise

    def _is_timestamp_error(self, exc: Exception) -> bool:
        if isinstance(exc, BinanceAPIException):
            if getattr(exc, "code", None) == -1021:
                return True
        msg = str(exc)
        return "Timestamp for this request" in msg or "timestamp for this request" in msg

    def _sync_time_if_needed(self, client: Optional[Client] = None, force: bool = False) -> None:
        target = client or self.client
        interval = max(int(getattr(self, "time_sync_interval", 300) or 300), 5)
        now = time.monotonic()
        if not force and self._last_time_sync_monotonic and (now - self._last_time_sync_monotonic) < interval:
            return

        with self._time_sync_lock:
            now2 = time.monotonic()
            if not force and self._last_time_sync_monotonic and (now2 - self._last_time_sync_monotonic) < interval:
                return
            self._ping_and_sync_time(target)
            try:
                offset = getattr(target, "timestamp_offset", 0)
            except Exception:
                offset = 0
            for c in (self._direct_client, self._proxy_client):
                if c and c is not target:
                    try:
                        c.timestamp_offset = offset
                    except Exception:
                        pass

    def _invoke_client_method(self, client: Client, method_name: str, *args, **kwargs):
        recv_window = int(getattr(self, "recv_window_ms", 0) or 0)
        if recv_window > 0 and "recvWindow" not in kwargs and "recv_window" not in kwargs:
            with_window = dict(kwargs)
            with_window["recvWindow"] = recv_window
            try:
                return getattr(client, method_name)(*args, **with_window)
            except TypeError:
                return getattr(client, method_name)(*args, **kwargs)
        return getattr(client, method_name)(*args, **kwargs)

    def _call_api(self, method_name: str, *args, **kwargs):
        self._sync_time_if_needed(self.client, force=False)
        try:
            return self._invoke_client_method(self.client, method_name, *args, **kwargs)
        except BinanceAPIException as exc:
            if self._is_timestamp_error(exc):
                self.logger.warning("Binance -1021 timestamp error, resyncing time and retrying...")
                self._sync_time_if_needed(self.client, force=True)
                return self._invoke_client_method(self.client, method_name, *args, **kwargs)
            raise

    def _call_read_api(self, method_name: str, *args, **kwargs):
        """
        对只读 Binance API 调用做网络重试 + 代理/直连回退。
        注意：下单/撤单等有副作用的接口不要使用该方法，以避免重复请求风险。
        """
        primary = self.client
        alt = self._get_alternate_client()
        last_exc: Optional[Exception] = None
        max_attempts = self.api_retry_count

        for attempt in range(max_attempts):
            try:
                self._sync_time_if_needed(primary, force=False)
                return self._invoke_client_method(primary, method_name, *args, **kwargs)
            except BinanceAPIException as exc:
                if self._is_timestamp_error(exc):
                    self.logger.warning("Binance -1021 timestamp error, resyncing time and retrying...")
                    self._sync_time_if_needed(primary, force=True)
                    return self._invoke_client_method(primary, method_name, *args, **kwargs)
                raise
            except Exception as exc:
                if not self._is_network_error(exc):
                    raise
                last_exc = exc
                if self._is_timeout_error(exc):
                    break
                if attempt < max_attempts - 1:
                    time.sleep(min(2 ** attempt, 5))
                    continue
                break

        if alt:
            try:
                self._sync_time_if_needed(alt, force=False)
                result = self._invoke_client_method(alt, method_name, *args, **kwargs)
                self._set_active_client(alt, reason=f"{method_name} success")
                return result
            except BinanceAPIException as exc:
                if self._is_timestamp_error(exc):
                    self.logger.warning("Binance -1021 timestamp error on alt client, resyncing and retrying...")
                    self._sync_time_if_needed(alt, force=True)
                    result = self._invoke_client_method(alt, method_name, *args, **kwargs)
                    self._set_active_client(alt, reason=f"{method_name} resync")
                    return result
                raise
            except Exception as exc:
                if not self._is_network_error(exc):
                    raise
                last_exc = exc

        if last_exc:
            raise last_exc
        raise RuntimeError(f"Binance API call failed: {method_name}")

    def _detect_hedge_mode(self) -> bool:
        cfg = getattr(self, "_config", None)
        if cfg is not None:
            try:
                return bool(getattr(cfg, "USE_HEDGE_MODE"))
            except Exception:
                pass
        try:
            result = self._call_read_api('futures_get_position_mode')
            if isinstance(result, dict):
                return bool(result.get('dualSidePosition'))
        except Exception:
            pass
        try:
            positions = self._call_read_api('futures_position_information')
            for pos in positions or []:
                side = str(pos.get('positionSide', '')).upper()
                if side in {'LONG', 'SHORT'}:
                    return True
        except Exception:
            pass
        return False

    def _ensure_hedge_mode(self) -> bool:
        if self._use_hedge_mode is None:
            self._use_hedge_mode = self._detect_hedge_mode()
        return bool(self._use_hedge_mode)

    def _submit_order_with_mode(self, order_kwargs: Dict, position_side: Optional[str] = None):
        use_hedge = self._ensure_hedge_mode()
        payload = dict(order_kwargs)
        if position_side and use_hedge:
            payload['positionSide'] = position_side
        for _ in range(3):
            try:
                return self._call_api('futures_create_order', **payload)
            except BinanceAPIException as exc:
                if getattr(exc, "code", None) == -1106 and 'reduceOnly' in payload:
                    payload = dict(payload)
                    payload.pop('reduceOnly', None)
                    continue
                if getattr(exc, "code", None) == -4061 or "position side" in str(exc).lower():
                    payload = dict(payload)
                    if 'positionSide' in payload:
                        payload.pop('positionSide', None)
                        self._use_hedge_mode = False
                    elif position_side:
                        payload['positionSide'] = position_side
                        self._use_hedge_mode = True
                    continue
                raise
        return self._call_api('futures_create_order', **payload)

    def is_major_coin(self, symbol: str) -> bool:
        """
        判断是否是主流币
        
        Args:
            symbol: 币种符号（如 "BTC" 或 "BTCUSDT"）
            
        Returns:
            是否是主流币
        """
        if not getattr(self, 'enable_major_coin_strategy', False):
            return False
        # 去除 USDT 后缀
        base_symbol = symbol.upper().replace('USDT', '').replace('USD', '')
        return base_symbol in getattr(self, 'major_coins', set())

    def get_coin_strategy_params(self, symbol: str) -> Dict:
        """
        获取币种对应的策略参数（主流币 vs 山寨币）
        
        Args:
            symbol: 币种符号
            
        Returns:
            策略参数字典，包含 stop_loss_percent, pyramiding_levels, 
            trailing_activation, trailing_callback
        """
        is_major = self.is_major_coin(symbol)
        
        if is_major:
            return {
                'is_major': True,
                'stop_loss_percent': getattr(self, 'major_coin_stop_loss_percent', 1.5),
                'pyramiding_levels': getattr(self, 'major_coin_pyramiding_exit_levels', []),
                'enable_trailing_stop': getattr(self, 'major_coin_enable_trailing_stop', True),
                'trailing_activation': getattr(self, 'major_coin_trailing_stop_activation', 1.0),
                'trailing_callback': getattr(self, 'major_coin_trailing_stop_callback', 0.8),
            }
        else:
            # 使用默认策略（山寨币）
            return {
                'is_major': False,
                'stop_loss_percent': self.risk_manager.stop_loss_percent,
                'pyramiding_levels': getattr(self, 'pyramiding_exit_levels', []),
                'enable_trailing_stop': getattr(self, 'enable_trailing_stop', False),
                'trailing_activation': None,  # 使用默认
                'trailing_callback': None,
            }

    def get_account_balance(self) -> Tuple[float, float]:
        """
        获取合约账户余额

        Returns:
            (总余额USDT, 可用余额USDT)
        """
        try:
            account = self._call_read_api('futures_account')
            total_wallet_balance = float(account.get('totalWalletBalance', 0))
            available_balance = float(account.get('availableBalance', 0))

            self.logger.debug(f"账户余额: 总额={total_wallet_balance}, 可用={available_balance}")
            return total_wallet_balance, available_balance
        except BinanceAPIException as e:
            self.logger.error(f"获取账户余额失败 (Binance API): {e}")
            return 0.0, 0.0
        except Exception as e:
            self.logger.warning(f"获取账户余额失败 (网络错误): {e}")
            return 0.0, 0.0

    def update_risk_manager_balance(self):
        """更新风险管理器的余额信息"""
        total, available = self.get_account_balance()
        self.risk_manager.update_balance(total, available)

    def get_symbol_price(self, symbol: str) -> Optional[float]:
        """获取合约当前标记价格"""
        try:
            ticker = self._call_read_api('futures_mark_price', symbol=symbol)
            return float(ticker['markPrice'])
        except BinanceAPIException as e:
            self.logger.error(f"获取 {symbol} 价格失败 (Binance API): {e}")
            return None
        except Exception as e:
            self.logger.warning(f"获取 {symbol} 价格失败 (网络错误): {e}")
            return None

    def set_leverage(self, symbol: str, leverage: int) -> bool:
        """设置杠杆倍数（带重试机制）"""
        max_retries = 3
        retry_delay = 2  # 秒

        for attempt in range(max_retries):
            try:
                result = self._call_api(
                    'futures_change_leverage',
                    symbol=symbol,
                    leverage=leverage
                )
                self.logger.info(f"✅ 设置 {symbol} 杠杆: {leverage}x")
                return True
            except BinanceAPIException as e:
                if "No need to change leverage" in str(e):
                    self.logger.debug(f"{symbol} 杠杆已设为 {leverage}x")
                    return True

                # 超时错误，尝试重试
                if e.code == -1007 or "Timeout" in str(e):
                    if attempt < max_retries - 1:
                        self.logger.warning(f"⏳ 设置杠杆超时，{retry_delay}秒后重试 ({attempt + 1}/{max_retries})")
                        time.sleep(retry_delay)
                        continue
                    else:
                        self.logger.error(f"设置 {symbol} 杠杆失败（已重试{max_retries}次）: {e}")
                        return False
                else:
                    self.logger.error(f"设置 {symbol} 杠杆失败: {e}")
                    return False

        return False

    def set_margin_type(self, symbol: str, margin_type: str) -> bool:
        """设置保证金模式（带重试机制）"""
        max_retries = 3
        retry_delay = 2  # 秒

        for attempt in range(max_retries):
            try:
                self._call_api(
                    'futures_change_margin_type',
                    symbol=symbol,
                    marginType=margin_type
                )
                self.logger.info(f"✅ 设置 {symbol} 保证金类型: {margin_type}")
                return True
            except BinanceAPIException as e:
                if "No need to change margin type" in str(e):
                    self.logger.debug(f"{symbol} 保证金类型已设为 {margin_type}")
                    return True

                # 超时错误，尝试重试
                if e.code == -1007 or "Timeout" in str(e):
                    if attempt < max_retries - 1:
                        self.logger.warning(f"⏳ 设置保证金模式超时，{retry_delay}秒后重试 ({attempt + 1}/{max_retries})")
                        time.sleep(retry_delay)
                        continue
                    else:
                        self.logger.error(f"设置 {symbol} 保证金类型失败（已重试{max_retries}次）: {e}")
                        return False
                else:
                    self.logger.error(f"设置 {symbol} 保证金类型失败: {e}")
                    return False

        return False

    def get_position_info(self, symbol: str) -> Optional[PositionInfo]:
        """获取指定标的的持仓信息"""
        try:
            positions = self._call_read_api('futures_position_information', symbol=symbol)
            for pos in positions:
                qty = float(pos.get('positionAmt', 0))
                if qty != 0:  # 有持仓
                    return PositionInfo(pos)
            return None
        except BinanceAPIException as e:
            self.logger.error(f"获取 {symbol} 持仓信息失败 (Binance API): {e}")
            return None
        except Exception as e:
            self.logger.warning(f"获取 {symbol} 持仓信息失败 (网络错误): {e}")
            return None

    def _get_position_amount(self, symbol: str) -> Optional[float]:
        """
        获取当前持仓数量（无持仓返回 0；网络/接口错误返回 None）。

        注意：此函数用于在开仓前判断是否安全清理旧挂单，避免误删正在保护持仓的止盈/止损。
        """
        try:
            positions = self._call_read_api('futures_position_information', symbol=symbol) or []
            for pos in positions:
                if pos.get('symbol') == symbol:
                    return float(pos.get('positionAmt', 0) or 0)
            if positions:
                return float(positions[0].get('positionAmt', 0) or 0)
            return 0.0
        except Exception as e:
            self.logger.warning(f"获取 {symbol} 持仓数量失败，跳过开仓前取消挂单: {e}")
            return None

    def cancel_exit_orders(self, symbol: str, order_types: Optional[List[str]] = None) -> int:
        """
        取消指定交易对的止盈/止损等退出类挂单（避免误取消策略挂的其它委托）。

        识别规则：
        - reduceOnly/closePosition 为 True 的订单
        - 或订单 type 属于配置的退出类型（默认 STOP/TAKE_PROFIT/TRAILING_STOP）

        Returns:
            已尝试取消的订单数量（成功/失败都会计入尝试数）。
        """
        try:
            configured_types = order_types or getattr(self, 'exit_order_types_to_cancel', None) or []
            exit_types = {str(t).upper() for t in configured_types if t}

            open_orders = self._call_read_api('futures_get_open_orders', symbol=symbol) or []
            if not isinstance(open_orders, list):
                return 0

            attempted = 0
            for order in open_orders:
                order_id = order.get('orderId')
                if not order_id:
                    continue

                order_type = str(order.get('type', '')).upper()
                reduce_only = bool(order.get('reduceOnly'))
                close_position = bool(order.get('closePosition'))

                is_exit_order = reduce_only or close_position or (order_type in exit_types)
                if not is_exit_order:
                    continue

                attempted += 1
                try:
                    self._call_api('futures_cancel_order', symbol=symbol, orderId=order_id)
                except BinanceAPIException as e:
                    self.logger.warning(f"取消订单失败 {symbol} orderId={order_id}: {e}")
                except Exception as e:
                    self.logger.warning(f"取消订单异常 {symbol} orderId={order_id}: {e}")

            if attempted:
                self.logger.info(f"🧹 已尝试取消 {symbol} 的退出类挂单 {attempted} 个")
            return attempted
        except Exception as e:
            self.logger.warning(f"取消 {symbol} 退出类挂单失败: {e}")
            return 0

    def cancel_stale_exit_orders_before_entry(self, symbol: str) -> int:
        """
        开仓前清理历史止盈/止损挂单。

        仅在确认当前无持仓（positionAmt==0）时执行，避免误删正在保护持仓的挂单。
        """
        if not getattr(self, 'cancel_exit_orders_before_entry', True):
            return 0

        position_amt = self._get_position_amount(symbol)
        if position_amt is None:
            return 0
        if abs(position_amt) > 0:
            return 0
        return self.cancel_exit_orders(symbol)

    @staticmethod
    def _normalize_exit_levels(exit_levels: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        normalized: List[Tuple[float, float]] = []
        for item in exit_levels or []:
            try:
                profit_pct = float(item[0])
                close_ratio = float(item[1])
            except Exception:
                continue
            if profit_pct <= 0:
                continue
            if close_ratio <= 0:
                continue
            normalized.append((profit_pct, close_ratio))
        return sorted(normalized, key=lambda x: x[0])

    def _place_take_profit_orders_from_levels(self, symbol: str, entry_price: float,
                                              total_qty: float,
                                              custom_levels: Optional[List[Tuple[float, float]]] = None) -> int:
        """
        根据止盈级别挂多级止盈单（支持主流币独立策略）。

        说明：
        - 前端的止盈 1/2/3 百分比会写入 PYRAMIDING_EXIT_LEVELS
        - close_ratio 语义与 PyramidingExitManager 一致：按“当前持仓比例”逐级平仓
        - 最后一个 close_ratio>=1 的级别使用 closePosition=True，避免舍入导致的残留

        Returns:
            成功提交的止盈单数量（不含止损单）。
        """
        # 优先使用自定义级别（主流币策略），否则使用默认配置
        if custom_levels:
            levels = self._normalize_exit_levels(custom_levels)
        else:
            levels = self._normalize_exit_levels(getattr(self, 'pyramiding_exit_levels', []) or [])
        if not levels:
            return 0
        # 兼容旧配置：平仓比例固定为 50% / 50% / 全平（按"剩余仓位"逐级计算）。
        # 仅对默认配置应用此兼容逻辑，自定义级别直接使用
        if len(levels) >= 3 and not custom_levels:
            levels = [
                (levels[0][0], 0.5),
                (levels[1][0], 0.5),
                (levels[2][0], 1.0),
            ]

        submitted = 0
        remaining = float(total_qty or 0)
        if remaining <= 0:
            return 0

        for idx, (profit_pct, close_ratio) in enumerate(levels):
            if remaining <= 0:
                break

            is_final_close = close_ratio >= 1.0
            tp_target = entry_price * (1 + profit_pct / 100)
            tp_price = self.format_price(symbol, tp_target, rounding="up")

            order_kwargs = {
                'symbol': symbol,
                'side': 'SELL',
                'type': 'TAKE_PROFIT_MARKET',
                'stopPrice': tp_price,
            }

            if is_final_close:
                order_kwargs['closePosition'] = True
                self.logger.info(f"🎯 设置止盈{idx+1} 于 {tp_price} (全平, {profit_pct}%)")
            else:
                raw_qty = remaining * min(max(close_ratio, 0.0), 1.0)
                tp_qty = self.format_quantity(symbol, raw_qty)
                if tp_qty <= 0:
                    self.logger.warning(f"止盈{idx+1} 下单量过小，跳过: {symbol} qty={raw_qty}")
                    continue
                if tp_qty > remaining:
                    tp_qty = remaining
                order_kwargs['quantity'] = tp_qty
                self.logger.info(
                    f"🎯 设置止盈{idx+1} 于 {tp_price} (平{tp_qty}张, {profit_pct}%, ratio={close_ratio})"
                )

            try:
                self._submit_order_with_mode(order_kwargs, position_side='LONG')
                submitted += 1
            except BinanceAPIException as e:
                self.logger.error(f"设置止盈{idx+1}失败: {e}")
            except Exception as e:
                self.logger.error(f"设置止盈{idx+1}异常: {e}")

            if not is_final_close and 'quantity' in order_kwargs:
                remaining -= float(order_kwargs['quantity'])

        return submitted

    def _place_short_pyramiding_exit_orders(self, symbol: str, entry_price: float,
                                            total_qty: float) -> int:
        """
        根据 SHORT_PYRAMIDING_EXIT_LEVELS 挂做空多级止盈单。

        说明：
        - 做空止盈在价格下跌时触发（价格低于入场价）
        - close_ratio 语义：按"当前持仓比例"逐级平仓
        - 最后一个 close_ratio>=1 的级别使用 closePosition=True

        Returns:
            成功提交的止盈单数量。
        """
        levels = self._normalize_exit_levels(getattr(self, 'short_pyramiding_exit_levels', []) or [])
        if not levels:
            return 0

        # 兼容配置：平仓比例固定为 50% / 50% / 全平
        if len(levels) >= 3:
            levels = [
                (levels[0][0], 0.5),
                (levels[1][0], 0.5),
                (levels[2][0], 1.0),
            ]

        submitted = 0
        remaining = float(total_qty or 0)
        if remaining <= 0:
            return 0

        for idx, (profit_pct, close_ratio) in enumerate(levels):
            if remaining <= 0:
                break

            is_final_close = close_ratio >= 1.0
            # 做空止盈：价格下跌 profit_pct% 时触发
            tp_target = entry_price * (1 - profit_pct / 100)
            tp_price = self.format_price(symbol, tp_target, rounding="down")

            order_kwargs = {
                'symbol': symbol,
                'side': 'BUY',  # 做空平仓用 BUY
                'type': 'TAKE_PROFIT_MARKET',
                'stopPrice': tp_price,
            }

            if is_final_close:
                order_kwargs['closePosition'] = True
                self.logger.info(f"🎯 做空止盈{idx+1} 于 {tp_price} (全平, -{profit_pct}%)")
            else:
                raw_qty = remaining * min(max(close_ratio, 0.0), 1.0)
                tp_qty = self.format_quantity(symbol, raw_qty)
                if tp_qty <= 0:
                    self.logger.warning(f"做空止盈{idx+1} 下单量过小，跳过: {symbol} qty={raw_qty}")
                    continue
                if tp_qty > remaining:
                    tp_qty = remaining
                order_kwargs['quantity'] = tp_qty
                self.logger.info(
                    f"🎯 做空止盈{idx+1} 于 {tp_price} (平{tp_qty}张, -{profit_pct}%, ratio={close_ratio})"
                )

            try:
                self._submit_order_with_mode(order_kwargs, position_side='SHORT')
                submitted += 1
            except BinanceAPIException as e:
                self.logger.error(f"设置做空止盈{idx+1}失败: {e}")
            except Exception as e:
                self.logger.error(f"设置做空止盈{idx+1}异常: {e}")

            if not is_final_close and 'quantity' in order_kwargs:
                remaining -= float(order_kwargs['quantity'])

        return submitted

    def verify_order_status(self, symbol: str, order_id: int) -> Optional[Dict]:
        """
        验证订单状态

        Args:
            symbol: 交易对
            order_id: 订单ID

        Returns:
            订单信息字典，如果查询失败返回None
        """
        try:
            order = self._call_read_api('futures_get_order', symbol=symbol, orderId=order_id)
            return order
        except Exception as e:
            self.logger.error(f"查询订单 {order_id} 状态失败: {e}")
            return None

    def calculate_quantity(self, symbol: str, usdt_amount: float,
                          leverage: int, current_price: float) -> float:
        """
        计算合约数量

        Args:
            symbol: 交易对
            usdt_amount: 使用的USDT金额（本金）
            leverage: 杠杆倍数
            current_price: 当前价格

        Returns:
            合约数量
        """
        # 合约价值 = 本金 × 杠杆
        position_value = usdt_amount * leverage

        # 数量 = 合约价值 / 当前价格
        quantity = position_value / current_price

        # 预留手续费（0.05%）
        quantity *= 0.9995

        return quantity

    def format_quantity(self, symbol: str, quantity: float) -> float:
        """根据交易对规则格式化数量"""
        try:
            symbol_info = self._get_symbol_info(symbol)
            if symbol_info:
                lot_filter = next(
                    (f for f in symbol_info.get('filters', []) if f.get('filterType') == 'LOT_SIZE'),
                    None
                )
                if lot_filter:
                    step_size = float(lot_filter.get('stepSize', 0)) or 0.0
                    min_qty = float(lot_filter.get('minQty', 0)) or 0.0
                    if step_size > 0:
                        rounded_qty = self._round_to_step(quantity, step_size, rounding="down")
                        if rounded_qty < min_qty and quantity >= min_qty:
                            self.logger.warning(
                                f"{symbol} 下单量 {quantity} 低于最小数量 {min_qty}，已上调至最小值"
                            )
                            rounded_qty = self._round_to_step(min_qty, step_size, rounding="up")
                        return rounded_qty
            return round(quantity, 3)  # 默认3位小数
        except Exception as e:
            self.logger.error(f"格式化数量失败: {e}")
            return round(quantity, 3)

    def format_price(self, symbol: str, price: float, rounding: str = "down") -> float:
        """根据交易对规则格式化价格"""
        try:
            symbol_info = self._get_symbol_info(symbol)
            if symbol_info:
                price_filter = next(
                    (f for f in symbol_info.get('filters', []) if f.get('filterType') == 'PRICE_FILTER'),
                    None
                )
                if price_filter:
                    tick_size = float(price_filter.get('tickSize', 0)) or 0.0
                    if tick_size > 0:
                        rounded_price = self._round_to_step(price, tick_size, rounding=rounding)
                        return rounded_price
            return round(price, 4)
        except Exception as e:
            self.logger.error(f"格式化价格失败: {e}")
            return round(price, 4)

    def _get_symbol_info(self, symbol: str) -> Optional[Dict]:
        """获取并缓存交易对规则"""
        if symbol in self._symbol_info_cache:
            return self._symbol_info_cache[symbol]

        try:
            exchange_info = self._call_read_api('futures_exchange_info')
            symbol_info = next((s for s in exchange_info['symbols'] if s['symbol'] == symbol), None)
            if symbol_info:
                self._symbol_info_cache[symbol] = symbol_info
                return symbol_info
        except Exception as e:
            self.logger.error(f"获取 {symbol} 交易规则失败: {e}")
        return None

    @staticmethod
    def _round_to_step(value: float, step: float, rounding: str = "down") -> float:
        """按照交易对步长对数值取整"""
        if step <= 0:
            return value

        decimal_value = Decimal(str(value))
        decimal_step = Decimal(str(step))

        rounding_mode = ROUND_DOWN if rounding == "down" else ROUND_UP
        floored = (decimal_value / decimal_step).to_integral_value(rounding=rounding_mode) * decimal_step

        # 使用 tickSize 的精度格式化结果，避免浮点数残留
        quantized = floored.quantize(decimal_step)
        return float(quantized)

    def open_long_position(self, recommendation: TradeRecommendation,
                          symbol_suffix: str = "USDT",
                          leverage: int = None,
                          margin_type: str = None) -> bool:
        """
        开多仓

        Args:
            recommendation: 交易建议
            symbol_suffix: 交易对后缀
            leverage: 杠杆倍数（None则使用默认）
            margin_type: 保证金模式（None则使用默认）

        Returns:
            是否成功
        """
        if recommendation.action != "BUY":
            self.logger.info(f"跳过 {recommendation.symbol} 交易: {recommendation.reason}")
            return False

        # 使用指定杠杆或默认杠杆
        leverage = leverage or self.leverage
        margin_type = margin_type or self.margin_type

        # 构建完整的交易对符号
        binance_symbol = f"{recommendation.symbol}{symbol_suffix}"

        try:
            # 1. 设置杠杆（尽力而为，即使失败也继续）
            leverage_set = self.set_leverage(binance_symbol, leverage)
            if not leverage_set:
                self.logger.warning(f"⚠️  设置杠杆失败，使用当前杠杆继续交易")

            # 2. 设置保证金模式（尽力而为，即使失败也继续）
            margin_set = self.set_margin_type(binance_symbol, margin_type)
            if not margin_set:
                self.logger.warning(f"⚠️  设置保证金模式失败，使用当前模式继续交易")

            # 3. 获取当前价格
            current_price = self.get_symbol_price(binance_symbol)
            if not current_price:
                self.logger.error(f"获取 {binance_symbol} 价格失败")
                return False

            # 使用风控建议的币数量（已经是基于 max_position_percent 计算的）
            # 注意：recommendation.quantity 是基于本金百分比计算的币数量，不需要再乘杠杆
            # 合约交易中，杠杆只影响保证金需求，不影响开仓数量
            notional_usdt = recommendation.quantity * current_price

            self.logger.info(
                f"\n{'='*60}\n"
                f"🚀 开多仓 (合约)\n"
                f"交易对: {binance_symbol}\n"
                f"杠杆: {leverage}x\n"
                f"保证金类型: {margin_type}\n"
                f"数量: {recommendation.quantity:.6f} {recommendation.symbol}\n"
                f"名义价值: {notional_usdt:.2f} USDT\n"
                f"所需保证金: {notional_usdt / leverage:.2f} USDT\n"
                f"止损: {recommendation.stop_loss:.2f}\n"
                f"止盈 1: {recommendation.take_profit_1:.2f}\n"
                f"止盈 2: {recommendation.take_profit_2:.2f}\n"
                f"风险等级: {recommendation.risk_level}\n"
                f"原因: {recommendation.reason}\n"
                f"{'='*60}"
            )

            # 4. 直接使用风控建议的数量（不再调用 calculate_quantity，避免重复乘杠杆）
            # 旧逻辑 BUG：calculate_quantity 会再乘一次杠杆，导致实际仓位 = 本金% × 杠杆 × 杠杆
            quantity = recommendation.quantity

            # 格式化数量
            quantity = self.format_quantity(binance_symbol, quantity)

            self.logger.info(f"📊 计算数量: {quantity} 张合约 @ {current_price}")

            # 4.5 开仓前取消旧的止盈/止损挂单（避免旧单残留）
            self.cancel_stale_exit_orders_before_entry(binance_symbol)

            # 5. 开仓（市价做多）- 带重试和状态验证
            max_order_retries = 2
            order_retry_delay = 3  # 秒
            order = None
            order_id = None

            # 检测账户持仓模式并选择合适的下单方式
            # 单向模式：不使用 positionSide
            # 双向模式：使用 positionSide='LONG'
            use_hedge_mode = getattr(config, 'USE_HEDGE_MODE', False) if 'config' in dir() else False
            
            for order_attempt in range(max_order_retries):
                try:
                    self.logger.info(f"🔄 尝试下单 ({order_attempt + 1}/{max_order_retries})...")
                    
                    # 先尝试不带 positionSide（单向模式）
                    try:
                        order = self._call_api('futures_create_order',
                            symbol=binance_symbol,
                            side='BUY',
                            type='MARKET',
                            quantity=quantity
                        )
                    except BinanceAPIException as e:
                        # 如果是 positionSide 相关错误，尝试双向模式
                        if e.code == -4061 or "position side" in str(e).lower():
                            self.logger.warning("单向模式下单失败，尝试双向模式...")
                            order = self._call_api('futures_create_order',
                                symbol=binance_symbol,
                                side='BUY',
                                positionSide='LONG',
                                type='MARKET',
                                quantity=quantity
                            )
                        else:
                            raise
                    
                    order_id = order.get('orderId')
                    self.logger.info(f"✅ 订单已提交，ID: {order_id}")
                    break  # 成功则跳出重试循环

                except BinanceAPIException as e:
                    # 超时错误且未达最大重试次数
                    if (e.code == -1007 or "Timeout" in str(e)) and order_attempt < max_order_retries - 1:
                        self.logger.warning(
                            f"⏳ 下单超时，{order_retry_delay}秒后重试 "
                            f"({order_attempt + 1}/{max_order_retries})"
                        )
                        time.sleep(order_retry_delay)
                        continue
                    else:
                        # 非超时错误或已达最大重试次数
                        self.logger.error(f"❌ 下单失败: {e}")

                        # 超时情况下尝试检查是否有新持仓
                        if e.code == -1007 or "Timeout" in str(e):
                            self.logger.warning("⚠️  超时错误，检查是否有新持仓...")
                            time.sleep(2)  # 等待2秒让订单可能完成
                            position = self.get_position_info(binance_symbol)
                            if position and position.quantity > 0:
                                self.logger.warning(
                                    f"⚠️  检测到新持仓 {position.quantity} 张合约，"
                                    f"订单可能已执行但响应超时"
                                )
                                # 构造一个虚拟订单对象继续流程
                                order = {
                                    'orderId': 'UNKNOWN_TIMEOUT',
                                    'status': 'FILLED',
                                    'executedQty': str(position.quantity),
                                    'origQty': str(quantity)
                                }
                                self.logger.info("✅ 使用检测到的持仓信息继续流程")
                                break
                        raise  # 重新抛出异常

            # 检查是否成功下单
            if not order:
                self.logger.error("❌ 下单失败，未获取到订单信息")
                return False

            # 6. 验证订单状态（如果有订单ID）
            if order_id and order_id != 'UNKNOWN_TIMEOUT':
                time.sleep(1)  # 等待1秒确保订单处理完成
                verified_order = self.verify_order_status(binance_symbol, order_id)
                if verified_order:
                    order = verified_order  # 使用验证后的订单信息
                    self.logger.info(f"✅ 订单状态已验证: {verified_order.get('status')}")

            executed_quantity = float(order.get('executedQty') or order.get('origQty') or 0)

            self.logger.info(
                f"✅ 多仓已开: {binance_symbol} "
                f"x{executed_quantity or quantity} (请求 {quantity})"
            )
            self.logger.info(f"订单 ID: {order.get('orderId')}, 状态: {order.get('status')}")

            # 7. 更新风险管理器持仓（使用实际成交数量）
            self.risk_manager.add_position(
                symbol=recommendation.symbol,
                quantity=executed_quantity or quantity,
                entry_price=current_price
            )

            # 8. 获取币种策略参数（主流币 vs 山寨币）
            coin_strategy = self.get_coin_strategy_params(recommendation.symbol)
            is_major = coin_strategy['is_major']
            
            if is_major:
                # 主流币使用独立止损
                actual_stop_loss_percent = coin_strategy['stop_loss_percent']
                actual_stop_loss = current_price * (1 - actual_stop_loss_percent / 100)
                self.logger.info(f"🏆 主流币策略: 止损={actual_stop_loss_percent}%")
            else:
                actual_stop_loss = recommendation.stop_loss
            
            # 设置止损单（自动适应单向/双向持仓模式）
            stop_loss_price = self.format_price(binance_symbol, actual_stop_loss, rounding="down")
            self.logger.info(f"🛡️  设置止损于 {stop_loss_price} ({'主流币' if is_major else '山寨币'}策略)")

            try:
                # 先尝试单向模式（不带 positionSide）
                try:
                    stop_order = self._call_api('futures_create_order',
                        symbol=binance_symbol,
                        side='SELL',
                        type='STOP_MARKET',
                        stopPrice=stop_loss_price,
                        closePosition=True
                    )
                except BinanceAPIException as e:
                    # 如果失败，尝试双向模式
                    if e.code == -4061 or "position side" in str(e).lower():
                        self.logger.warning("单向模式止损失败，尝试双向模式...")
                        stop_order = self._call_api('futures_create_order',
                            symbol=binance_symbol,
                            side='SELL',
                            positionSide='LONG',
                            type='STOP_MARKET',
                            stopPrice=stop_loss_price,
                            closePosition=True
                        )
                    else:
                        raise
                self.logger.info(f"✅ 止损已设于 {stop_loss_price}")
            except BinanceAPIException as e:
                self.logger.error(f"设置止损失败: {e}")

            # 9. 设置止盈单（根据主流币/山寨币策略选择不同的止盈级别）
            tp_count = 0
            if getattr(self, 'enable_pyramiding_exit', False) and getattr(
                    self, 'pyramiding_exit_execution', 'orders') == 'orders':
                # 根据币种类型选择止盈级别
                if is_major and coin_strategy['pyramiding_levels']:
                    self.logger.info(f"🏆 使用主流币金字塔止盈策略: {coin_strategy['pyramiding_levels']}")
                    tp_count = self._place_take_profit_orders_from_levels(
                        binance_symbol, current_price, executed_quantity or quantity,
                        custom_levels=coin_strategy['pyramiding_levels']
                    )
                else:
                    tp_count = self._place_take_profit_orders_from_levels(
                        binance_symbol, current_price, executed_quantity or quantity
                    )
            if tp_count == 0:
                # 兼容旧配置：固定 2 个止盈点 (50% + 50%)
                # 自动适应单向/双向持仓模式
                tp1_price = self.format_price(binance_symbol, recommendation.take_profit_1, rounding="up")
                tp1_quantity = self.format_quantity(binance_symbol, (executed_quantity or quantity) * 0.5)
                self.logger.info(f"🎯 设置第一止盈于 {tp1_price} (平{tp1_quantity}张合约, 50%)")

                try:
                    # 先尝试单向模式
                    self._submit_order_with_mode(
                        {
                            'symbol': binance_symbol,
                            'side': 'SELL',
                            'type': 'TAKE_PROFIT_MARKET',
                            'stopPrice': tp1_price,
                            'quantity': tp1_quantity,
                            'reduceOnly': True,
                        },
                        position_side='LONG'
                    )
                    self.logger.info(f"✅ 第一止盈已设于 {tp1_price}")
                except BinanceAPIException as e:
                    self.logger.error(f"设置第一止盈失败: {e}")

                tp2_price = self.format_price(binance_symbol, recommendation.take_profit_2, rounding="up")
                tp2_quantity = self.format_quantity(binance_symbol, (executed_quantity or quantity) * 0.5)
                self.logger.info(f"🎯 设置第二止盈于 {tp2_price} (平{tp2_quantity}张合约, 50%)")

                try:
                    # 先尝试单向模式
                    self._submit_order_with_mode(
                        {
                            'symbol': binance_symbol,
                            'side': 'SELL',
                            'type': 'TAKE_PROFIT_MARKET',
                            'stopPrice': tp2_price,
                            'quantity': tp2_quantity,
                            'reduceOnly': True,
                        },
                        position_side='LONG'
                    )
                    self.logger.info(f"✅ 第二止盈已设于 {tp2_price}")
                except BinanceAPIException as e:
                    self.logger.error(f"设置第二止盈失败: {e}")

            # 11. 记录交易
            self.risk_manager.record_trade(recommendation.symbol)

            # 12. 更新余额
            self.update_risk_manager_balance()

            # 13. 初始化止盈级别跟踪
            self.executed_tp_levels[recommendation.symbol] = set()

            # 14. 发送开仓通知
            if self.notify_open:
                self.notifier.notify_open_position(
                    symbol=binance_symbol,
                    side='LONG',
                    quantity=executed_quantity or quantity,
                    price=current_price,
                    leverage=leverage,
                    stop_loss=stop_loss_price,
                    take_profit=recommendation.take_profit_1,
                    take_profit_2=recommendation.take_profit_2,
                    reason=recommendation.reason
                )
            
            # 15. 记录交易到性能数据库
            # Requirements: 4.1
            if self.performance_recorder and self.performance_recorder.is_available:
                self.performance_recorder.record_open_position(
                    symbol=binance_symbol,
                    quantity=executed_quantity or quantity,
                    entry_price=current_price,
                    order_id=str(order.get('orderId')) if order else None
                )

            return True

        except BinanceOrderException as e:
            self.logger.error(f"❌ 订单失败: {e}")
            return False
        except BinanceAPIException as e:
            self.logger.error(f"❌ API 错误: {e}")
            return False
        except Exception as e:
            self.logger.error(f"❌ 未预期的错误: {e}")
            return False

    def open_short_position(self, recommendation: TradeRecommendation,
                           symbol_suffix: str = "USDT",
                           leverage: int = None,
                           margin_type: str = None,
                           stop_loss_percent: float = 2.0,
                           take_profit_percent: float = 3.0) -> bool:
        """
        开空仓

        Args:
            recommendation: 交易建议
            symbol_suffix: 交易对后缀
            leverage: 杠杆倍数（None则使用默认）
            margin_type: 保证金模式（None则使用默认）
            stop_loss_percent: 止损百分比（向上）
            take_profit_percent: 止盈百分比（向下）

        Returns:
            是否成功
        """
        # 使用指定杠杆或默认杠杆
        leverage = leverage or self.leverage
        margin_type = margin_type or self.margin_type

        # 构建完整的交易对符号
        binance_symbol = f"{recommendation.symbol}{symbol_suffix}"

        try:
            # 1. 设置杠杆
            leverage_set = self.set_leverage(binance_symbol, leverage)
            if not leverage_set:
                self.logger.warning(f"⚠️  设置杠杆失败，使用当前杠杆继续交易")

            # 2. 设置保证金模式
            margin_set = self.set_margin_type(binance_symbol, margin_type)
            if not margin_set:
                self.logger.warning(f"⚠️  设置保证金模式失败，使用当前模式继续交易")

            # 3. 获取当前价格
            current_price = self.get_symbol_price(binance_symbol)
            if not current_price:
                self.logger.error(f"获取 {binance_symbol} 价格失败")
                return False

            # 使用风控建议的币数量计算等值本金
            notional_usdt = recommendation.quantity * current_price

            self.logger.info(
                f"\n{'='*60}\n"
                f"🔻 开空仓 (合约)\n"
                f"交易对: {binance_symbol}\n"
                f"杠杆: {leverage}x\n"
                f"保证金类型: {margin_type}\n"
                f"数量: {recommendation.quantity:.6f} {recommendation.symbol}\n"
                f"名义价值: {notional_usdt:.2f} USDT (x{leverage} => {notional_usdt * leverage:.2f})\n"
                f"止损: +{stop_loss_percent}% (向上)\n"
                f"止盈: -{take_profit_percent}% (向下)\n"
                f"原因: {recommendation.reason}\n"
                f"{'='*60}"
            )

            # 4. 计算合约数量
            quantity = self.calculate_quantity(
                binance_symbol,
                notional_usdt,
                leverage,
                current_price
            )
            quantity = self.format_quantity(binance_symbol, quantity)

            self.logger.info(f"📊 计算数量: {quantity} 张合约 @ {current_price}")

            # 4.5 开仓前取消旧的止盈/止损挂单
            self.cancel_stale_exit_orders_before_entry(binance_symbol)

            # 5. 开仓（市价做空）- 带重试
            max_order_retries = 2
            order_retry_delay = 3
            order = None
            order_id = None

            for order_attempt in range(max_order_retries):
                try:
                    self.logger.info(f"🔄 尝试下单 ({order_attempt + 1}/{max_order_retries})...")
                    order = self._submit_order_with_mode(
                        {
                            'symbol': binance_symbol,
                            'side': 'SELL',
                            'type': 'MARKET',
                            'quantity': quantity,
                        },
                        position_side='SHORT'
                    )
                    order_id = order.get('orderId')
                    self.logger.info(f"✅ 订单已提交，ID: {order_id}")
                    break

                except BinanceAPIException as e:
                    if (e.code == -1007 or "Timeout" in str(e)) and order_attempt < max_order_retries - 1:
                        self.logger.warning(
                            f"⏳ 下单超时，{order_retry_delay}秒后重试 "
                            f"({order_attempt + 1}/{max_order_retries})"
                        )
                        time.sleep(order_retry_delay)
                        continue
                    else:
                        self.logger.error(f"❌ 下单失败: {e}")
                        if e.code == -1007 or "Timeout" in str(e):
                            self.logger.warning("⚠️  超时错误，检查是否有新持仓...")
                            time.sleep(2)
                            position = self.get_position_info(binance_symbol)
                            if position and position.quantity < 0:
                                self.logger.warning(
                                    f"⚠️  检测到新空仓 {abs(position.quantity)} 张合约"
                                )
                                order = {
                                    'orderId': 'UNKNOWN_TIMEOUT',
                                    'status': 'FILLED',
                                    'executedQty': str(abs(position.quantity)),
                                    'origQty': str(quantity)
                                }
                                break
                        raise

            if not order:
                self.logger.error("❌ 下单失败，未获取到订单信息")
                return False

            # 6. 验证订单状态
            if order_id and order_id != 'UNKNOWN_TIMEOUT':
                time.sleep(1)
                verified_order = self.verify_order_status(binance_symbol, order_id)
                if verified_order:
                    order = verified_order
                    self.logger.info(f"✅ 订单状态已验证: {verified_order.get('status')}")

            executed_quantity = float(order.get('executedQty') or order.get('origQty') or 0)

            self.logger.warning(
                f"✅ 空仓已开: {binance_symbol} "
                f"x{executed_quantity or quantity} (请求 {quantity})"
            )
            self.logger.info(f"订单 ID: {order.get('orderId')}, 状态: {order.get('status')}")

            # 7. 更新风险管理器持仓
            self.risk_manager.add_position(
                symbol=recommendation.symbol,
                quantity=-(executed_quantity or quantity),  # 负数表示空仓
                entry_price=current_price
            )

            # 8. 设置止损单（空仓止损在上方）
            stop_loss_price = current_price * (1 + stop_loss_percent / 100)
            stop_loss_price = self.format_price(binance_symbol, stop_loss_price, rounding="up")
            self.logger.info(f"🛡️  设置止损于 {stop_loss_price} (+{stop_loss_percent}%)")

            try:
                self._submit_order_with_mode(
                    {
                        'symbol': binance_symbol,
                        'side': 'BUY',
                        'type': 'STOP_MARKET',
                        'stopPrice': stop_loss_price,
                        'closePosition': True,
                    },
                    position_side='SHORT'
                )
                self.logger.info(f"✅ 止损已设于 {stop_loss_price}")
            except BinanceAPIException as e:
                self.logger.error(f"设置止损失败: {e}")

            # 9. 设置止盈单（空仓止盈在下方）
            # 检查是否启用做空金字塔退出
            if self.short_enable_pyramiding_exit and self.short_pyramiding_exit_levels:
                # 使用金字塔退出策略
                tp_count = self._place_short_pyramiding_exit_orders(
                    binance_symbol, current_price, executed_quantity or float(quantity)
                )
                self.logger.info(f"✅ 已设置 {tp_count} 个做空金字塔止盈单")
            else:
                # 使用简单止盈
                take_profit_price = current_price * (1 - take_profit_percent / 100)
                take_profit_price = self.format_price(binance_symbol, take_profit_price, rounding="down")
                self.logger.info(f"🎯 设置止盈于 {take_profit_price} (-{take_profit_percent}%)")

                try:
                    self._submit_order_with_mode(
                        {
                            'symbol': binance_symbol,
                            'side': 'BUY',
                            'type': 'TAKE_PROFIT_MARKET',
                            'stopPrice': take_profit_price,
                            'closePosition': True,
                        },
                        position_side='SHORT'
                    )
                    self.logger.info(f"✅ 止盈已设于 {take_profit_price}")
                except BinanceAPIException as e:
                    self.logger.error(f"设置止盈失败: {e}")

            # 10. 记录交易
            self.risk_manager.record_trade(recommendation.symbol)

            # 11. 更新余额
            self.update_risk_manager_balance()

            # 12. 初始化止盈级别跟踪
            self.executed_tp_levels[recommendation.symbol] = set()

            # 13. 发送开仓通知
            if self.notify_open:
                self.notifier.notify_open_position(
                    symbol=binance_symbol,
                    side='SHORT',
                    quantity=executed_quantity or quantity,
                    price=current_price,
                    leverage=leverage,
                    stop_loss=stop_loss_price,
                    take_profit=take_profit_price,
                    reason=recommendation.reason
                )

            # 14. 记录交易到性能数据库
            if self.performance_recorder and self.performance_recorder.is_available:
                self.performance_recorder.record_open_position(
                    symbol=binance_symbol,
                    quantity=-(executed_quantity or quantity),
                    entry_price=current_price,
                    order_id=str(order.get('orderId')) if order else None
                )

            return True

        except BinanceOrderException as e:
            self.logger.error(f"❌ 订单失败: {e}")
            return False
        except BinanceAPIException as e:
            self.logger.error(f"❌ API 错误: {e}")
            return False
        except Exception as e:
            self.logger.error(f"❌ 未预期的错误: {e}")
            return False

    def close_position(self, symbol: str, reason: str = "手动平仓") -> bool:
        """
        平仓

        Args:
            symbol: 交易对（如 BTCUSDT）
            reason: 平仓原因

        Returns:
            是否成功
        """
        try:
            self.logger.info(f"🔻 平仓: {symbol} - 原因: {reason}")

            # 获取持仓信息（平仓前）
            position = self.get_position_info(symbol)
            entry_price = position.entry_price if position else 0
            raw_quantity = float(position.quantity) if position else 0.0
            quantity = abs(raw_quantity) if position else 0.0
            mark_price = position.mark_price if position else 0

            if not position or quantity <= 0:
                self.logger.warning(f"未找到 {symbol} 的持仓，无法平仓")
                return False

            side = 'SELL' if raw_quantity > 0 else 'BUY'
            formatted_qty = self.format_quantity(symbol, quantity)
            pos_side = 'LONG' if raw_quantity > 0 else 'SHORT'
            order = self._submit_order_with_mode(
                {
                    'symbol': symbol,
                    'side': side,
                    'type': 'MARKET',
                    'quantity': formatted_qty,
                    'reduceOnly': True,
                },
                position_side=pos_side
            )
            self.logger.info(f"✅ 仓位已平: {symbol}")
            self.logger.info(f"订单 ID: {order.get('orderId')}")

            # 计算盈亏
            exit_price = mark_price  # use mark price as a close proxy
            pnl = 0.0
            if entry_price > 0 and quantity > 0:
                if raw_quantity > 0:
                    pnl = (exit_price - entry_price) * quantity
                    pnl_percent = ((exit_price - entry_price) / entry_price) * 100
                else:
                    pnl = (entry_price - exit_price) * quantity
                    pnl_percent = ((entry_price - exit_price) / entry_price) * 100

                # 发送平仓通知
                if self.notify_close:
                    self.notifier.notify_close_position(
                        symbol=symbol,
                        side='LONG' if raw_quantity > 0 else 'SHORT',
                        quantity=quantity,
                        entry_price=entry_price,
                        exit_price=exit_price,
                        pnl=pnl,
                        pnl_percent=pnl_percent,
                        reason=reason
                    )
            
            # 记录交易到性能数据库
            # Requirements: 4.1
            if self.performance_recorder and self.performance_recorder.is_available:
                self.performance_recorder.record_close_position(
                    symbol=symbol,
                    quantity=quantity,
                    exit_price=exit_price,
                    realized_pnl=pnl,
                    order_id=str(order.get('orderId')) if order else None
                )

            # 取消该标的的所有未成交订单
            self.cancel_all_orders(symbol)

            # 从风险管理器移除持仓
            symbol_base = symbol.replace("USDT", "")
            self.risk_manager.remove_position(symbol_base)

            # 清理止盈级别记录
            if symbol_base in self.executed_tp_levels:
                del self.executed_tp_levels[symbol_base]

            return True

        except BinanceAPIException as e:
            self.logger.error(f"平仓 {symbol} 失败: {e}")
            return False

    def partial_close_position(self, symbol: str, close_percent: float,
                               reason: str = "止盈") -> bool:
        """
        部分平仓

        Args:
            symbol: 交易对
            close_percent: 平仓比例 (0-1)
            reason: 平仓原因

        Returns:
            是否成功
        """
        try:
            # 获取当前持仓
            position = self.get_position_info(symbol)
            if not position or position.quantity == 0:
                self.logger.warning(f"未找到 {symbol} 的持仓")
                return False

            # 计算平仓数量
            raw_quantity = float(position.quantity)
            close_quantity = abs(raw_quantity) * close_percent
            close_quantity = self.format_quantity(symbol, close_quantity)

            self.logger.info(
                f"📉 部分平仓 {close_percent*100:.0f}% {symbol}: "
                f"{close_quantity} 张合约 - 原因: {reason}"
            )

            # 保存平仓前的信息
            entry_price = position.entry_price
            current_price = position.mark_price
            total_quantity = abs(position.quantity)

            side = 'SELL' if raw_quantity > 0 else 'BUY'
            pos_side = 'LONG' if raw_quantity > 0 else 'SHORT'
            order = self._submit_order_with_mode(
                {
                    'symbol': symbol,
                    'side': side,
                    'type': 'MARKET',
                    'quantity': close_quantity,
                    'reduceOnly': True,
                },
                position_side=pos_side
            )
            self.logger.info(f"✅ 部分平仓成功: {close_quantity} 张合约")

            # 计算盈亏
            if raw_quantity > 0:
                pnl = (current_price - entry_price) * close_quantity
            else:
                pnl = (entry_price - current_price) * close_quantity
            remaining_qty = total_quantity - close_quantity

            # 发送部分平仓通知
            if self.notify_partial:
                self.notifier.notify_partial_close(
                    symbol=symbol,
                    side='LONG' if raw_quantity > 0 else 'SHORT',
                    closed_qty=close_quantity,
                    remaining_qty=remaining_qty,
                    close_percent=close_percent * 100,
                    current_price=current_price,
                    pnl=pnl,
                    reason=reason
                )

            return True

        except BinanceAPIException as e:
            self.logger.error(f"部分平仓 {symbol} 失败: {e}")
            return False

    def cancel_all_orders(self, symbol: str):
        """取消指定交易对的所有未成交订单"""
        try:
            result = self._call_api('futures_cancel_all_open_orders', symbol=symbol)
            self.logger.info(f"已取消 {symbol} 的所有订单")
        except BinanceAPIException as e:
            self.logger.error(f"取消 {symbol} 订单失败: {e}")

    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """获取未成交订单"""
        try:
            if symbol:
                return self._call_read_api('futures_get_open_orders', symbol=symbol)
            return self._call_read_api('futures_get_open_orders')
        except BinanceAPIException as e:
            self.logger.error(f"获取未成交订单失败: {e}")
            return []

    def update_positions(self):
        """更新所有持仓信息"""
        try:
            positions = self._call_read_api('futures_position_information')
            previous_positions = self.positions
            updated_positions: Dict[str, PositionInfo] = {}
            risk_positions: Dict[str, Dict[str, float]] = {}

            for pos_data in positions:
                qty = float(pos_data.get('positionAmt', 0))
                if qty != 0:  # 只保存有持仓的
                    symbol = pos_data.get('symbol')
                    position = PositionInfo(pos_data)

                    # 如果之前有缓存，继承移动止损数据
                    if symbol in previous_positions:
                        old_pos = previous_positions[symbol]
                        position.highest_price = max(position.mark_price, old_pos.highest_price)
                        position.trailing_stop_activated = old_pos.trailing_stop_activated
                        position.trailing_stop_price = old_pos.trailing_stop_price

                    updated_positions[symbol] = position

                    symbol_base = symbol.replace("USDT", "")
                    risk_entry_time = None
                    update_time = pos_data.get("updateTime")
                    if update_time:
                        try:
                            risk_entry_time = datetime.fromtimestamp(int(update_time) / 1000)
                        except Exception:
                            risk_entry_time = None

                    risk_positions[symbol_base] = {
                        "quantity": abs(position.quantity),
                        "entry_price": position.entry_price,
                        "current_price": position.mark_price,
                        "entry_time": risk_entry_time,
                    }

            # 检测被外部平仓的标的（如止损单触发）
            closed_symbols = set(previous_positions.keys()) - set(updated_positions.keys())
            for closed_symbol in closed_symbols:
                self.logger.warning(f"🔔 检测到 {closed_symbol} 已被外部平仓（可能是止损/止盈单触发）")
                # 取消该币种的所有剩余挂单
                self.cancel_all_orders(closed_symbol)
                # 清理风险管理器中的持仓记录
                symbol_base = closed_symbol.replace("USDT", "")
                self.risk_manager.remove_position(symbol_base)
                # 清理止盈级别记录
                if symbol_base in self.executed_tp_levels:
                    del self.executed_tp_levels[symbol_base]

            # 用最新数据替换缓存
            self.positions = updated_positions

            # 与风控持仓同步，移除已平仓标的
            self.risk_manager.sync_positions(risk_positions)

        except BinanceAPIException as e:
            self.logger.error(f"更新持仓失败 (Binance API): {e}")
        except Exception as e:
            # 捕获网络连接错误等其他异常
            self.logger.warning(f"更新持仓失败 (网络错误): {e}")
            # 保留之前的持仓数据，不做更新

    def monitor_positions(self):
        """监控持仓状态并更新价格"""
        self.update_positions()

        for symbol, position in self.positions.items():
            symbol_base = symbol.replace("USDT", "")

            self.logger.debug(
                f"{symbol_base}: Entry={position.entry_price:.2f}, "
                f"Mark={position.mark_price:.2f}, "
                f"PnL={position.unrealized_pnl_percent:.2f}%, "
                f"Leverage={position.leverage}x"
            )

        if getattr(self, 'safety_force_exit_unprotected', False):
            try:
                self._safety_enforce_unprotected_exits()
            except Exception as e:
                self.logger.warning(f"Safety exit enforcement failed: {e}")

    def _get_position_pnl_percent(self, position: PositionInfo) -> float:
        entry_price = float(getattr(position, 'entry_price', 0) or 0)
        mark_price = float(getattr(position, 'mark_price', 0) or 0)
        qty = float(getattr(position, 'quantity', 0) or 0)
        if entry_price <= 0:
            return 0.0
        if qty >= 0:
            return ((mark_price - entry_price) / entry_price) * 100
        return ((entry_price - mark_price) / entry_price) * 100

    def _get_open_orders_safe(self, symbol: str) -> List[Dict]:
        try:
            orders = self._call_read_api('futures_get_open_orders', symbol=symbol) or []
            return orders if isinstance(orders, list) else []
        except Exception:
            return []

    @staticmethod
    def _price_matches_target(order_price: float, target_price: float, rel_tol: float = 0.01) -> bool:
        if target_price <= 0:
            return False
        try:
            order_price = float(order_price)
        except Exception:
            return False
        return abs(order_price - target_price) / target_price <= rel_tol

    def _has_protection_order(self, orders: List[Dict], order_types: set, target_price: float) -> bool:
        for order in orders:
            if str(order.get('type', '')).upper() not in order_types:
                continue
            stop_price = order.get('stopPrice')
            if stop_price is None:
                continue
            if self._price_matches_target(stop_price, target_price):
                return True
        return False

    def _safety_get_take_profit_levels(self) -> List[Tuple[float, float]]:
        if getattr(self, 'safety_use_pyramiding_levels', True) and getattr(self, 'enable_pyramiding_exit', False):
            levels = self._normalize_exit_levels(getattr(self, 'pyramiding_exit_levels', []) or [])
            if levels:
                return levels

        # Fallback: derive from RiskManager percentages (2-level strategy).
        try:
            tp1 = float(getattr(self.risk_manager, 'take_profit_1_percent', 0) or 0)
            tp2 = float(getattr(self.risk_manager, 'take_profit_2_percent', 0) or 0)
        except Exception:
            return []
        levels: List[Tuple[float, float]] = []
        if tp1 > 0:
            levels.append((tp1, 0.5))
        if tp2 > 0:
            levels.append((tp2, 1.0))
        return self._normalize_exit_levels(levels)

    def _safety_get_stop_loss_percent(self) -> float:
        override = float(getattr(self, 'safety_force_stop_loss_percent', 0) or 0)
        if override > 0:
            return override
        try:
            return float(getattr(self.risk_manager, 'stop_loss_percent', 0) or 0)
        except Exception:
            return 0.0

    def _safety_may_act(self, symbol: str) -> bool:
        now = time.time()
        last = float(self._safety_last_action_ts.get(symbol, 0) or 0)
        min_interval = max(int(getattr(self, 'safety_min_action_interval', 15) or 15), 1)
        if last and (now - last) < min_interval:
            return False
        self._safety_last_action_ts[symbol] = now
        return True

    def _safety_enforce_unprotected_exits(self) -> None:
        """
        If a position has moved beyond SL/TP thresholds but no SL/TP orders exist on the exchange,
        enforce exit via market close/partial close using the pyramiding semantics.
        """
        levels = self._safety_get_take_profit_levels()
        stop_loss_percent = self._safety_get_stop_loss_percent()

        stop_types = {'STOP_MARKET', 'STOP', 'TRAILING_STOP_MARKET'}
        tp_types = {'TAKE_PROFIT_MARKET', 'TAKE_PROFIT'}

        for symbol, position in list(self.positions.items()):
            symbol_base = symbol.replace("USDT", "")
            pnl_pct = self._get_position_pnl_percent(position)
            orders = self._get_open_orders_safe(symbol)

            entry_price = float(getattr(position, 'entry_price', 0) or 0)
            qty = float(getattr(position, 'quantity', 0) or 0)
            is_long = qty >= 0

            stop_target = None
            if entry_price > 0 and stop_loss_percent > 0:
                stop_target = entry_price * (1 - abs(stop_loss_percent) / 100) if is_long else entry_price * (1 + abs(stop_loss_percent) / 100)

            has_stop = bool(stop_target and self._has_protection_order(orders, stop_types, stop_target))

            # Safety stop-loss: full close
            if stop_loss_percent > 0 and pnl_pct <= -abs(stop_loss_percent) and not has_stop:
                if not self._safety_may_act(symbol):
                    continue
                self.logger.warning(
                    f"🛑 Safety SL: {symbol} pnl={pnl_pct:.2f}% <= -{abs(stop_loss_percent):.2f}% "
                    f"and no stop order, forcing market close"
                )
                self.close_position(symbol, reason="安全止损(未挂止损单)")
                continue

            # Safety take-profits: pyramiding semantics (only when the corresponding TP order is missing)
            if not levels:
                continue

            executed = self.executed_tp_levels.setdefault(symbol_base, set())
            for idx, (profit_pct, close_ratio) in enumerate(levels):
                if idx in executed:
                    continue
                if pnl_pct < profit_pct:
                    break
                if not self._safety_may_act(symbol):
                    break

                tp_target = None
                if entry_price > 0:
                    tp_target = entry_price * (1 + profit_pct / 100) if is_long else entry_price * (1 - profit_pct / 100)
                if tp_target and self._has_protection_order(orders, tp_types, tp_target):
                    break

                if close_ratio >= 1.0:
                    self.logger.warning(
                        f"🎯 Safety TP{idx+1}: {symbol} pnl={pnl_pct:.2f}% >= {profit_pct:.2f}% "
                        f"and missing TP order, forcing full close"
                    )
                    ok = self.close_position(symbol, reason=f"安全止盈Level {idx+1}(未挂止盈单)")
                else:
                    self.logger.warning(
                        f"🎯 Safety TP{idx+1}: {symbol} pnl={pnl_pct:.2f}% >= {profit_pct:.2f}% "
                        f"and missing TP order, forcing partial close ratio={close_ratio}"
                    )
                    ok = self.partial_close_position(
                        symbol, close_ratio, reason=f"安全止盈Level {idx+1}(未挂止盈单)"
                    )

                if ok:
                    executed.add(idx)
                break

    def check_liquidation_risk(self) -> List[Tuple[str, float]]:
        """
        检查强平风险

        Returns:
            [(symbol, margin_ratio), ...] 保证金率较低的持仓列表
        """
        risky_positions = []

        for symbol, position in self.positions.items():
            if position.liquidation_price > 0:
                # 计算距离强平价格的百分比
                distance = abs(position.mark_price - position.liquidation_price) / position.mark_price * 100

                if distance < 30:  # 距离强平价格小于30%
                    risky_positions.append((symbol, distance))

        return risky_positions
