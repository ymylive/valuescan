"""
CCXT-based market data helpers.
CCXT is a required dependency for multi-exchange support.
"""

from __future__ import annotations

import os
import threading
import time
from typing import Any, Dict, List, Optional

import ccxt  # 必须依赖

try:
    from logger import logger
except Exception:
    logger = None


_EXCHANGE_LOCK = threading.Lock()
_EXCHANGE_CACHE: Dict[str, Any] = {}
_EXCHANGE_TS: Dict[str, float] = {}
_CACHE_TTL_SEC = 1800


def _log(level: str, msg: str, *args: Any) -> None:
    if logger:
        getattr(logger, level, logger.info)(msg, *args)


def _safe_symbol(symbol: str) -> str:
    return str(symbol or "").upper().replace("$", "").replace("USDT", "").strip()


def _env_or_config(name: str, default: str) -> str:
    raw = os.getenv(name)
    if raw is not None and raw != "":
        return raw
    try:
        import config as signal_config
        value = getattr(signal_config, name, default)
        return str(value)
    except Exception:
        return default


def _ccxt_enabled() -> bool:
    raw = _env_or_config("NOFX_CCXT_ENABLED", "1")
    return str(raw).lower() in ("1", "true", "yes", "on")


def _ccxt_exchange_id() -> str:
    return _env_or_config("NOFX_CCXT_EXCHANGE", "binance").strip().lower()


def _ccxt_market_type() -> str:
    return _env_or_config("NOFX_CCXT_MARKET_TYPE", "spot").strip().lower()


def _get_exchange(exchange_id: Optional[str] = None) -> Optional[Any]:
    if not _ccxt_enabled():
        return None

    exchange_id = exchange_id or _ccxt_exchange_id()
    now = time.time()
    with _EXCHANGE_LOCK:
        cached = _EXCHANGE_CACHE.get(exchange_id)
        cached_ts = _EXCHANGE_TS.get(exchange_id, 0.0)
        if cached and (now - cached_ts) < _CACHE_TTL_SEC:
            return cached

        exchange_class = getattr(ccxt, exchange_id, None)
        if not exchange_class:
            _log("warning", "[CCXT] Unknown exchange: %s", exchange_id)
            return None
        try:
            exchange = exchange_class({"enableRateLimit": True})
            market_type = _ccxt_market_type()
            if hasattr(exchange, "options") and isinstance(exchange.options, dict):
                exchange.options["defaultType"] = market_type
            exchange.load_markets()
        except Exception as exc:
            _log("warning", "[CCXT] Failed to init exchange %s: %s", exchange_id, exc)
            return None

        _EXCHANGE_CACHE[exchange_id] = exchange
        _EXCHANGE_TS[exchange_id] = now
        return exchange


def fetch_ccxt_ticker(symbol: str) -> Optional[Dict[str, Any]]:
    exchange = _get_exchange()
    if not exchange:
        return None
    base = _safe_symbol(symbol)
    if not base:
        return None
    pair = f"{base}/USDT"
    try:
        ticker = exchange.fetch_ticker(pair)
    except Exception as exc:
        _log("debug", "[CCXT] fetch_ticker failed %s: %s", pair, exc)
        return None
    if not isinstance(ticker, dict):
        return None

    price = ticker.get("last") or ticker.get("close")
    return {
        "price": float(price) if price is not None else None,
        "price_change_percent": ticker.get("percentage"),
        "high_24h": ticker.get("high"),
        "low_24h": ticker.get("low"),
        "volume_24h": ticker.get("quoteVolume") or ticker.get("baseVolume"),
        "trade_count": ticker.get("count"),
        "bid": ticker.get("bid"),
        "ask": ticker.get("ask"),
        "source": f"ccxt:{_ccxt_exchange_id()}",
    }


def fetch_ccxt_orderbook(symbol: str, limit: int = 20) -> Optional[Dict[str, Any]]:
    exchange = _get_exchange()
    if not exchange:
        return None
    base = _safe_symbol(symbol)
    if not base:
        return None
    pair = f"{base}/USDT"
    try:
        orderbook = exchange.fetch_order_book(pair, limit=limit)
    except Exception as exc:
        _log("debug", "[CCXT] fetch_order_book failed %s: %s", pair, exc)
        return None
    if not isinstance(orderbook, dict):
        return None
    return {
        "bids": orderbook.get("bids") or [],
        "asks": orderbook.get("asks") or [],
    }


def _calc_depth_notional(side: list, limit: int = 10) -> float:
    depth = 0.0
    for price, amount in side[:limit]:
        try:
            depth += float(price) * float(amount)
        except Exception:
            continue
    return depth


def _build_liquidity_metrics(ticker: Dict[str, Any], orderbook: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    bid = ticker.get("bid")
    ask = ticker.get("ask")
    if (bid is None or ask is None) and orderbook:
        bids = orderbook.get("bids") or []
        asks = orderbook.get("asks") or []
        if bids:
            bid = bids[0][0]
        if asks:
            ask = asks[0][0]

    spread = None
    spread_pct = None
    if bid is not None and ask is not None:
        try:
            spread = float(ask) - float(bid)
            mid = (float(ask) + float(bid)) / 2.0
            if mid > 0:
                spread_pct = spread / mid * 100.0
        except Exception:
            spread = None
            spread_pct = None

    depth_bid = depth_ask = depth_total = None
    if orderbook:
        bids = orderbook.get("bids") or []
        asks = orderbook.get("asks") or []
        depth_bid = _calc_depth_notional(bids)
        depth_ask = _calc_depth_notional(asks)
        depth_total = depth_bid + depth_ask

    return {
        "spread": spread,
        "spread_pct": spread_pct,
        "depth_bid": depth_bid,
        "depth_ask": depth_ask,
        "depth_total": depth_total,
    }


def fetch_ccxt_snapshot(symbol: str) -> Optional[Dict[str, Any]]:
    ticker = fetch_ccxt_ticker(symbol)
    if not ticker:
        return None
    raw_limit = _env_or_config("NOFX_CCXT_ORDERBOOK_LIMIT", "20")
    try:
        orderbook_limit = int(raw_limit)
    except Exception:
        orderbook_limit = 20
    orderbook = fetch_ccxt_orderbook(symbol, limit=orderbook_limit)
    liquidity = _build_liquidity_metrics(ticker, orderbook)
    payload = dict(ticker)
    if liquidity:
        payload["liquidity"] = liquidity
    return payload
