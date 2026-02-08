import os
import time
from typing import Any, Dict, List, Optional

import pandas as pd
import requests

try:
    from signal_monitor.logger import logger
except Exception:
    from logger import logger


_CACHE: Dict[str, Dict[str, Any]] = {}
_CACHE_TTL = int(os.getenv("NOFX_METALS_KLINES_TTL", "10") or 10)


def _cache_get(key: str) -> Optional[pd.DataFrame]:
    entry = _CACHE.get(key)
    if not entry:
        return None
    ts = entry.get("ts")
    if not isinstance(ts, (int, float)):
        return None
    if _CACHE_TTL <= 0 or time.time() - ts > _CACHE_TTL:
        return None
    data = entry.get("data")
    return data if isinstance(data, pd.DataFrame) else None


def _cache_set(key: str, df: pd.DataFrame) -> None:
    if df is None or df.empty:
        return
    _CACHE[key] = {"ts": time.time(), "data": df}


def _safe_symbol(symbol: str) -> str:
    return str(symbol or "").upper().replace("$", "").strip()


def _map_oanda_symbol(symbol: str) -> Optional[str]:
    base = _safe_symbol(symbol)
    mapping = {
        "XAUUSD": "XAU_USD",
        "XAGUSD": "XAG_USD",
        "GOLD": "XAU_USD",
        "SILVER": "XAG_USD",
        "XAU": "XAU_USD",
        "XAG": "XAG_USD",
    }
    return mapping.get(base)


def _map_twelvedata_symbol(symbol: str) -> Optional[str]:
    base = _safe_symbol(symbol)
    mapping = {
        "XAUUSD": "XAU/USD",
        "XAGUSD": "XAG/USD",
        "GOLD": "XAU/USD",
        "SILVER": "XAG/USD",
        "XAU": "XAU/USD",
        "XAG": "XAG/USD",
    }
    return mapping.get(base)

def _map_binance_symbol(symbol: str) -> Optional[str]:
    base = _safe_symbol(symbol)
    mapping = {
        "XAUUSDT": "XAUUSDT",
        "XAGUSDT": "XAGUSDT",
        "XAUUSD": "XAUUSDT",
        "XAGUSD": "XAGUSDT",
        "GOLD": "XAUUSDT",
        "SILVER": "XAGUSDT",
        "XAU": "XAUUSDT",
        "XAG": "XAGUSDT",
    }
    return mapping.get(base)


def _interval_to_oanda_granularity(interval: str) -> str:
    interval = (interval or "").lower()
    mapping = {
        "1m": "M1",
        "5m": "M5",
        "15m": "M15",
        "30m": "M30",
        "1h": "H1",
        "2h": "H2",
        "4h": "H4",
    }
    return mapping.get(interval, "H1")

def _fetch_binance_futures_klines(symbol: str, interval: str, limit: int) -> Optional[pd.DataFrame]:
    mapped = _map_binance_symbol(symbol)
    if not mapped:
        return None
    url = "https://fapi.binance.com/fapi/v1/klines"
    params = {"symbol": mapped, "interval": interval, "limit": limit}
    try:
        resp = requests.get(url, params=params, timeout=12)
        if resp.status_code != 200:
            return None
        data = resp.json()
    except Exception as exc:
        logger.warning("Binance klines error: %s", exc)
        return None
    if not isinstance(data, list) or not data:
        return None
    rows: List[Dict[str, Any]] = []
    for row in data:
        if not isinstance(row, list) or len(row) < 6:
            continue
        try:
            rows.append({
                "timestamp": pd.to_datetime(int(row[0]), unit="ms", utc=True),
                "open": float(row[1]),
                "high": float(row[2]),
                "low": float(row[3]),
                "close": float(row[4]),
                "volume": float(row[5]),
            })
        except Exception:
            continue
    if not rows:
        return None
    df = pd.DataFrame(rows)
    return df.sort_values("timestamp").reset_index(drop=True)

def _fetch_binance_continuous_klines(symbol: str, interval: str, limit: int) -> Optional[pd.DataFrame]:
    mapped = _map_binance_symbol(symbol)
    if not mapped:
        return None
    url = "https://fapi.binance.com/fapi/v1/continuousKlines"
    params = {
        "pair": mapped,
        "contractType": "TRADIFI_PERPETUAL",
        "interval": interval,
        "limit": limit,
    }
    try:
        resp = requests.get(url, params=params, timeout=12)
        if resp.status_code != 200:
            return None
        data = resp.json()
    except Exception as exc:
        logger.warning("Binance continuous klines error: %s", exc)
        return None
    if not isinstance(data, list) or not data:
        return None
    rows: List[Dict[str, Any]] = []
    for row in data:
        if not isinstance(row, list) or len(row) < 6:
            continue
        try:
            rows.append({
                "timestamp": pd.to_datetime(int(row[0]), unit="ms", utc=True),
                "open": float(row[1]),
                "high": float(row[2]),
                "low": float(row[3]),
                "close": float(row[4]),
                "volume": float(row[5]),
            })
        except Exception:
            continue
    if not rows:
        return None
    df = pd.DataFrame(rows)
    return df.sort_values("timestamp").reset_index(drop=True)


def _fetch_oanda_klines(symbol: str, interval: str, limit: int) -> Optional[pd.DataFrame]:
    token = os.getenv("NOFX_OANDA_API_KEY") or os.getenv("OANDA_API_KEY")
    if not token:
        return None
    instrument = _map_oanda_symbol(symbol)
    if not instrument:
        return None
    env = (os.getenv("NOFX_OANDA_ENV") or os.getenv("OANDA_ENV") or "practice").strip().lower()
    base_url = "https://api-fxpractice.oanda.com/v3" if env != "live" else "https://api-fxtrade.oanda.com/v3"
    url = f"{base_url}/instruments/{instrument}/candles"
    granularity = _interval_to_oanda_granularity(interval)
    params = {"granularity": granularity, "count": limit, "price": "M"}
    headers = {"Authorization": f"Bearer {token}", "Accept-Datetime-Format": "RFC3339"}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=12)
        if resp.status_code != 200:
            logger.warning("OANDA candles failed: %s %s", resp.status_code, resp.text[:200])
            return None
        payload = resp.json()
    except Exception as exc:
        logger.warning("OANDA candles error: %s", exc)
        return None
    candles = payload.get("candles") if isinstance(payload, dict) else None
    if not isinstance(candles, list) or not candles:
        return None
    rows: List[Dict[str, Any]] = []
    for candle in candles:
        if not isinstance(candle, dict):
            continue
        if candle.get("complete") is False:
            continue
        mid = candle.get("mid") if isinstance(candle.get("mid"), dict) else None
        if not mid:
            continue
        try:
            rows.append({
                "timestamp": candle.get("time"),
                "open": float(mid.get("o")),
                "high": float(mid.get("h")),
                "low": float(mid.get("l")),
                "close": float(mid.get("c")),
                "volume": float(candle.get("volume", 0) or 0),
            })
        except Exception:
            continue
    if not rows:
        return None
    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df.dropna(subset=["timestamp", "open", "high", "low", "close"])
    if df.empty:
        return None
    return df.sort_values("timestamp").reset_index(drop=True)


def _fetch_twelvedata_klines(symbol: str, interval: str, limit: int) -> Optional[pd.DataFrame]:
    api_key = os.getenv("NOFX_TWELVEDATA_API_KEY") or os.getenv("TWELVEDATA_API_KEY")
    if not api_key:
        return None
    mapped = _map_twelvedata_symbol(symbol)
    if not mapped:
        return None
    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": mapped,
        "interval": interval,
        "outputsize": limit,
        "apikey": api_key,
        "format": "JSON",
        "timezone": "UTC",
    }
    try:
        resp = requests.get(url, params=params, timeout=12)
        payload = resp.json()
    except Exception as exc:
        logger.warning("Twelve Data request failed: %s", exc)
        return None
    if not isinstance(payload, dict):
        return None
    if payload.get("status") == "error":
        logger.warning("Twelve Data error: %s", payload.get("message"))
        return None
    values = payload.get("values")
    if not isinstance(values, list) or not values:
        return None
    rows: List[Dict[str, Any]] = []
    for row in values:
        if not isinstance(row, dict):
            continue
        try:
            rows.append({
                "timestamp": row.get("datetime"),
                "open": float(row.get("open")),
                "high": float(row.get("high")),
                "low": float(row.get("low")),
                "close": float(row.get("close")),
                "volume": float(row.get("volume", 0) or 0),
            })
        except Exception:
            continue
    if not rows:
        return None
    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df.dropna(subset=["timestamp", "open", "high", "low", "close"])
    if df.empty:
        return None
    return df.sort_values("timestamp").reset_index(drop=True)


def fetch_metals_klines(
    symbol: str,
    interval: str = "1h",
    limit: int = 200,
    force_refresh: bool = False,
) -> Optional[pd.DataFrame]:
    base = _safe_symbol(symbol)
    if not base:
        return None
    cache_key = f"{base}:{interval}:{limit}"
    if not force_refresh:
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached
    providers_raw = os.getenv("NOFX_METALS_KLINE_PROVIDERS") or "binance,oanda,twelvedata"
    providers = [p.strip().lower() for p in providers_raw.split(",") if p.strip()]
    for provider in providers:
        if provider == "binance":
            df = _fetch_binance_futures_klines(base, interval, limit)
            if (df is None or df.empty) and base in ("XAUUSD", "XAGUSD", "XAUUSDT", "XAGUSDT"):
                df = _fetch_binance_continuous_klines(base, interval, limit)
        elif provider == "oanda":
            df = _fetch_oanda_klines(base, interval, limit)
        elif provider == "twelvedata":
            df = _fetch_twelvedata_klines(base, interval, limit)
        else:
            df = None
        if df is not None and not df.empty:
            try:
                df.attrs["provider"] = provider
            except Exception:
                pass
            _cache_set(cache_key, df)
            return df
    return None
