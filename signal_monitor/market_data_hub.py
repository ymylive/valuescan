from __future__ import annotations

import os
from datetime import datetime, timezone
from io import StringIO
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests

from signal_monitor.yahoo_data import fetch_yahoo_snapshot, fetch_yahoo_klines


STOCK_SOURCE_WEIGHTS = {
    "yahoo": 0.45,
    "finnhub": 0.3,
    "stooq": 0.15,
    "alphavantage": 0.05,
    "twelvedata": 0.05,
}

FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY") or os.getenv("NOFX_FINNHUB_API_KEY") or "ctdj3t1r01qhb4a7lmagctdj3t1r01qhb4a7lmb0"
ALPHAVANTAGE_API_KEY = os.getenv("ALPHAVANTAGE_API_KEY") or os.getenv("NOFX_ALPHAVANTAGE_API_KEY")
TWELVEDATA_API_KEY = os.getenv("TWELVEDATA_API_KEY") or os.getenv("NOFX_TWELVEDATA_API_KEY")


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def _request_json(url: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> Optional[Any]:
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        return None
    return None


def _merge_snapshot(base: Dict[str, Any], extra: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base)
    for key, value in extra.items():
        if value is None:
            continue
        if merged.get(key) in (None, 0, "", []):
            merged[key] = value
    return merged


def _maybe_stooq_symbol(symbol: str) -> List[str]:
    raw = symbol.strip()
    candidates = []
    if raw:
        candidates.append(raw)
        if raw.startswith("^"):
            candidates.append(raw.lower())
        if "." not in raw and not raw.startswith("^"):
            candidates.append(f"{raw}.US")
            candidates.append(f"{raw.lower()}.us")
    return list(dict.fromkeys(candidates))


def fetch_finnhub_quote(symbol: str) -> Optional[Dict[str, Any]]:
    if not FINNHUB_API_KEY:
        return None
    data = _request_json(
        "https://finnhub.io/api/v1/quote",
        params={"symbol": symbol, "token": FINNHUB_API_KEY},
    )
    if not isinstance(data, dict):
        return None
    current = data.get("c")
    prev_close = data.get("pc")
    if current is None:
        return None
    change_pct = data.get("dp")
    if change_pct is None and prev_close:
        try:
            change_pct = (float(current) - float(prev_close)) / float(prev_close) * 100
        except Exception:
            change_pct = None
    return {
        "price": current,
        "previous_close": prev_close,
        "price_change_percent": change_pct,
        "high_24h": data.get("h"),
        "low_24h": data.get("l"),
        "volume_24h": data.get("v"),
        "as_of": datetime.now(timezone.utc).isoformat(),
        "source": "finnhub",
    }


def fetch_alphavantage_quote(symbol: str) -> Optional[Dict[str, Any]]:
    if not ALPHAVANTAGE_API_KEY:
        return None
    data = _request_json(
        "https://www.alphavantage.co/query",
        params={"function": "GLOBAL_QUOTE", "symbol": symbol, "apikey": ALPHAVANTAGE_API_KEY},
    )
    quote = (data or {}).get("Global Quote") if isinstance(data, dict) else None
    if not isinstance(quote, dict):
        return None
    price = _safe_float(quote.get("05. price"))
    prev_close = _safe_float(quote.get("08. previous close"))
    if price is None:
        return None
    change_pct = None
    if prev_close:
        change_pct = (price - prev_close) / prev_close * 100
    return {
        "price": price,
        "previous_close": prev_close,
        "price_change_percent": change_pct,
        "high_24h": _safe_float(quote.get("03. high")),
        "low_24h": _safe_float(quote.get("04. low")),
        "volume_24h": _safe_float(quote.get("06. volume")),
        "as_of": datetime.now(timezone.utc).isoformat(),
        "source": "alphavantage",
    }


def fetch_twelvedata_quote(symbol: str) -> Optional[Dict[str, Any]]:
    if not TWELVEDATA_API_KEY:
        return None
    data = _request_json(
        "https://api.twelvedata.com/quote",
        params={"symbol": symbol, "apikey": TWELVEDATA_API_KEY},
    )
    if not isinstance(data, dict):
        return None
    price = _safe_float(data.get("close"))
    if price is None:
        return None
    prev_close = _safe_float(data.get("previous_close"))
    change_pct = None
    if prev_close:
        change_pct = (price - prev_close) / prev_close * 100
    return {
        "price": price,
        "previous_close": prev_close,
        "price_change_percent": change_pct,
        "high_24h": _safe_float(data.get("high")),
        "low_24h": _safe_float(data.get("low")),
        "volume_24h": _safe_float(data.get("volume")),
        "as_of": datetime.now(timezone.utc).isoformat(),
        "source": "twelvedata",
    }


def fetch_stooq_quote(symbol: str) -> Optional[Dict[str, Any]]:
    for candidate in _maybe_stooq_symbol(symbol):
        url = f"https://stooq.com/q/l/?s={candidate}&f=sd2t2ohlcv&h&e=csv"
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code != 200:
                continue
            df = pd.read_csv(StringIO(resp.text))
        except Exception:
            continue
        if df.empty or "Close" not in df.columns:
            continue
        row = df.iloc[0]
        price = _safe_float(row.get("Close"))
        if price is None:
            continue
        return {
            "price": price,
            "previous_close": _safe_float(row.get("Open")),
            "price_change_percent": None,
            "high_24h": _safe_float(row.get("High")),
            "low_24h": _safe_float(row.get("Low")),
            "volume_24h": _safe_float(row.get("Volume")),
            "as_of": datetime.now(timezone.utc).isoformat(),
            "source": "stooq",
        }
    return None


def fetch_stooq_klines(symbol: str) -> Optional[pd.DataFrame]:
    for candidate in _maybe_stooq_symbol(symbol):
        url = f"https://stooq.com/q/d/l/?s={candidate}&i=d"
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code != 200:
                continue
            df = pd.read_csv(StringIO(resp.text))
        except Exception:
            continue
        if df.empty or "Close" not in df.columns:
            continue
        df = df.rename(
            columns={
                "Date": "timestamp",
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume",
            }
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
        for col in ("open", "high", "low", "close", "volume"):
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df.dropna(subset=["timestamp", "open", "high", "low", "close"]).reset_index(drop=True)
        if not df.empty:
            return df
    return None


def fetch_stock_snapshot_sources(symbol: str) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    providers = [
        ("yahoo", fetch_yahoo_snapshot),
        ("finnhub", fetch_finnhub_quote),
        ("stooq", fetch_stooq_quote),
        ("alphavantage", fetch_alphavantage_quote),
        ("twelvedata", fetch_twelvedata_quote),
    ]
    merged: Dict[str, Any] = {}
    sources: List[Dict[str, Any]] = []
    for name, provider in providers:
        data = provider(symbol)
        if not isinstance(data, dict):
            continue
        sources.append({"name": name, "weight": STOCK_SOURCE_WEIGHTS.get(name, 0.1), "data": data})
    for item in sorted(sources, key=lambda x: x.get("weight", 0), reverse=True):
        merged = _merge_snapshot(merged, item["data"])
    snapshot = merged if merged.get("price") is not None else None
    return snapshot, sources


def fetch_stock_klines(symbol: str) -> Optional[pd.DataFrame]:
    df = fetch_yahoo_klines(symbol, interval="1h", range_="10d")
    if df is not None and not df.empty:
        return df
    return fetch_stooq_klines(symbol)
