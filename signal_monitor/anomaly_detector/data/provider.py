"""
数据提供者模块 - Freqtrade风格的统一数据接口
支持多交易所数据源 (Binance + CCXT)
"""

from __future__ import annotations

import os
import time
import threading
from typing import Any, Dict, List, Optional, Tuple
from collections import deque
from dataclasses import dataclass, field

import requests

try:
    from ..logger import logger
except Exception:
    import logging
    logger = logging.getLogger(__name__)

# CCXT 多交易所支持
try:
    from ...ccxt_data import fetch_ccxt_ticker, fetch_ccxt_orderbook, fetch_ccxt_snapshot
    CCXT_AVAILABLE = True
except ImportError:
    try:
        from signal_monitor.ccxt_data import fetch_ccxt_ticker, fetch_ccxt_orderbook, fetch_ccxt_snapshot
        CCXT_AVAILABLE = True
    except ImportError:
        CCXT_AVAILABLE = False
        fetch_ccxt_ticker = None
        fetch_ccxt_orderbook = None
        fetch_ccxt_snapshot = None


@dataclass
class OHLCV:
    """K线数据"""
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class Ticker:
    """行情数据"""
    symbol: str
    price: float
    price_change_pct: float
    high_24h: float
    low_24h: float
    volume_24h: float
    timestamp: float = field(default_factory=time.time)


@dataclass
class OrderBook:
    """订单簿数据"""
    symbol: str
    bids: List[Tuple[float, float]]  # [(price, amount), ...]
    asks: List[Tuple[float, float]]
    timestamp: float = field(default_factory=time.time)


class DataBuffer:
    """数据缓冲区 - 环形缓冲区实现"""

    def __init__(self, maxlen: int = 500):
        self._data: deque = deque(maxlen=maxlen)
        self._lock = threading.Lock()

    def push(self, item: Any) -> None:
        with self._lock:
            self._data.append(item)

    def get_all(self) -> List[Any]:
        with self._lock:
            return list(self._data)

    def get_latest(self, n: int = 1) -> List[Any]:
        with self._lock:
            return list(self._data)[-n:]

    def __len__(self) -> int:
        with self._lock:
            return len(self._data)


class DataProvider:
    """
    统一数据提供者 - Freqtrade风格

    提供统一的数据访问接口，支持多数据源回退
    """

    def __init__(self):
        self._session = self._create_session()
        self._cache: Dict[str, DataBuffer] = {}
        self._ticker_cache: Dict[str, Tuple[float, Ticker]] = {}
        self._cache_ttl = 5.0  # 缓存5秒

    def _create_session(self) -> requests.Session:
        session = requests.Session()
        proxy = os.getenv("NOFX_PROXY") or os.getenv("HTTP_PROXY")
        if proxy:
            session.proxies = {"http": proxy, "https": proxy}
        return session

    def _safe_symbol(self, symbol: str) -> str:
        return symbol.upper().replace("$", "").replace("USDT", "").strip()

    # ==================== Ticker ====================

    def get_ticker(self, symbol: str) -> Optional[Ticker]:
        """获取行情数据 (Binance优先，CCXT备用)"""
        symbol = self._safe_symbol(symbol)

        # 检查缓存
        if symbol in self._ticker_cache:
            ts, ticker = self._ticker_cache[symbol]
            if time.time() - ts < self._cache_ttl:
                return ticker

        # 优先使用 Binance
        ticker = self._fetch_binance_ticker(symbol)

        # Binance 失败时使用 CCXT
        if not ticker and CCXT_AVAILABLE and fetch_ccxt_ticker:
            ticker = self._fetch_ccxt_ticker(symbol)

        if ticker:
            self._ticker_cache[symbol] = (time.time(), ticker)
        return ticker

    def _fetch_ccxt_ticker(self, symbol: str) -> Optional[Ticker]:
        """从CCXT获取行情 (多交易所支持)"""
        try:
            data = fetch_ccxt_ticker(symbol)
            if data and data.get("price") is not None:
                return Ticker(
                    symbol=symbol,
                    price=float(data["price"]),
                    price_change_pct=float(data.get("price_change_percent") or 0),
                    high_24h=float(data.get("high_24h") or 0),
                    low_24h=float(data.get("low_24h") or 0),
                    volume_24h=float(data.get("volume_24h") or 0),
                )
        except Exception as e:
            logger.debug(f"[DataProvider] CCXT ticker failed: {e}")
        return None

    def _fetch_binance_ticker(self, symbol: str) -> Optional[Ticker]:
        """从Binance获取行情"""
        try:
            url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}USDT"
            resp = self._session.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return Ticker(
                    symbol=symbol,
                    price=float(data.get("lastPrice", 0)),
                    price_change_pct=float(data.get("priceChangePercent", 0)),
                    high_24h=float(data.get("highPrice", 0)),
                    low_24h=float(data.get("lowPrice", 0)),
                    volume_24h=float(data.get("quoteVolume", 0)),
                )
        except Exception as e:
            logger.debug(f"[DataProvider] Binance ticker failed: {e}")
        return None

    # ==================== OHLCV ====================

    def get_ohlcv(self, symbol: str, interval: str = "1h", limit: int = 100) -> List[OHLCV]:
        """获取K线数据"""
        symbol = self._safe_symbol(symbol)
        return self._fetch_binance_klines(symbol, interval, limit)

    def _fetch_binance_klines(self, symbol: str, interval: str, limit: int) -> List[OHLCV]:
        """从Binance获取K线"""
        try:
            url = "https://api.binance.com/api/v3/klines"
            params = {"symbol": f"{symbol}USDT", "interval": interval, "limit": limit}
            resp = self._session.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return [
                    OHLCV(
                        timestamp=int(k[0]),
                        open=float(k[1]),
                        high=float(k[2]),
                        low=float(k[3]),
                        close=float(k[4]),
                        volume=float(k[5]),
                    )
                    for k in data
                ]
        except Exception as e:
            logger.debug(f"[DataProvider] Binance klines failed: {e}")
        return []

    # ==================== Order Book ====================

    def get_orderbook(self, symbol: str, limit: int = 20) -> Optional[OrderBook]:
        """获取订单簿 (Binance优先，CCXT备用)"""
        symbol = self._safe_symbol(symbol)

        # 优先使用 Binance
        orderbook = self._fetch_binance_orderbook(symbol, limit)

        # Binance 失败时使用 CCXT
        if not orderbook and CCXT_AVAILABLE and fetch_ccxt_orderbook:
            orderbook = self._fetch_ccxt_orderbook(symbol, limit)

        return orderbook

    def _fetch_ccxt_orderbook(self, symbol: str, limit: int) -> Optional[OrderBook]:
        """从CCXT获取订单簿 (多交易所支持)"""
        try:
            data = fetch_ccxt_orderbook(symbol, limit=limit)
            if data:
                return OrderBook(
                    symbol=symbol,
                    bids=[(float(b[0]), float(b[1])) for b in data.get("bids", [])],
                    asks=[(float(a[0]), float(a[1])) for a in data.get("asks", [])],
                )
        except Exception as e:
            logger.debug(f"[DataProvider] CCXT orderbook failed: {e}")
        return None

    def _fetch_binance_orderbook(self, symbol: str, limit: int) -> Optional[OrderBook]:
        """从Binance获取订单簿"""
        try:
            url = f"https://api.binance.com/api/v3/depth?symbol={symbol}USDT&limit={limit}"
            resp = self._session.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return OrderBook(
                    symbol=symbol,
                    bids=[(float(b[0]), float(b[1])) for b in data.get("bids", [])],
                    asks=[(float(a[0]), float(a[1])) for a in data.get("asks", [])],
                )
        except Exception as e:
            logger.debug(f"[DataProvider] Binance orderbook failed: {e}")
        return None

    # ==================== Derivatives ====================

    def get_funding_rate(self, symbol: str) -> Optional[float]:
        """获取资金费率"""
        symbol = self._safe_symbol(symbol)
        try:
            url = f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={symbol}USDT&limit=1"
            resp = self._session.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data:
                    return float(data[0].get("fundingRate", 0))
        except Exception as e:
            logger.debug(f"[DataProvider] Funding rate failed: {e}")
        return None

    def get_open_interest(self, symbol: str) -> Optional[float]:
        """获取持仓量"""
        symbol = self._safe_symbol(symbol)
        try:
            url = f"https://fapi.binance.com/fapi/v1/openInterest?symbol={symbol}USDT"
            resp = self._session.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return float(data.get("openInterest", 0))
        except Exception as e:
            logger.debug(f"[DataProvider] Open interest failed: {e}")
        return None

    # ==================== Sentiment ====================

    def get_fear_greed_index(self) -> Optional[int]:
        """获取恐惧贪婪指数"""
        try:
            url = "https://api.alternative.me/fng/?limit=1"
            resp = self._session.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("data"):
                    return int(data["data"][0].get("value", 50))
        except Exception as e:
            logger.debug(f"[DataProvider] Fear&Greed failed: {e}")
        return None

    # ==================== Buffer Management ====================

    def get_buffer(self, key: str) -> DataBuffer:
        """获取或创建数据缓冲区"""
        if key not in self._cache:
            self._cache[key] = DataBuffer()
        return self._cache[key]

    def push_to_buffer(self, key: str, data: Any) -> None:
        """推送数据到缓冲区"""
        self.get_buffer(key).push(data)
