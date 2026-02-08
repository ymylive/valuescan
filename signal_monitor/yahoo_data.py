from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

import pandas as pd
import requests


YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"


def _request_chart(symbol: str, interval: str, range_: str) -> Optional[Dict[str, Any]]:
    url = YAHOO_CHART_URL.format(symbol=symbol)
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json",
    }
    try:
        resp = requests.get(url, params={"interval": interval, "range": range_}, headers=headers, timeout=15)
        if resp.status_code != 200:
            return None
        payload = resp.json()
        return payload if isinstance(payload, dict) else None
    except Exception:
        return None


def fetch_yahoo_snapshot(symbol: str) -> Optional[Dict[str, Any]]:
    payload = _request_chart(symbol, interval="1m", range_="1d")
    result = (payload or {}).get("chart", {}).get("result") or []
    if not result or not isinstance(result[0], dict):
        return None
    meta = result[0].get("meta") or {}
    price = meta.get("regularMarketPrice")
    previous_close = meta.get("previousClose") or meta.get("chartPreviousClose")
    high_24h = meta.get("regularMarketDayHigh")
    low_24h = meta.get("regularMarketDayLow")
    volume_24h = meta.get("regularMarketVolume")
    if price is None:
        return None
    change_pct = None
    if previous_close:
        try:
            change_pct = (float(price) - float(previous_close)) / float(previous_close) * 100
        except Exception:
            change_pct = None
    return {
        "price": price,
        "price_change_percent": change_pct,
        "high_24h": high_24h,
        "low_24h": low_24h,
        "volume_24h": volume_24h,
        "previous_close": previous_close,
        "as_of": datetime.now(timezone.utc).isoformat(),
        "source": "yahoo",
    }


def fetch_yahoo_klines(
    symbol: str,
    interval: str = "1h",
    range_: str = "10d",
) -> Optional[pd.DataFrame]:
    payload = _request_chart(symbol, interval=interval, range_=range_)
    result = (payload or {}).get("chart", {}).get("result") or []
    if not result or not isinstance(result[0], dict):
        return None
    timestamps = result[0].get("timestamp") or []
    indicators = result[0].get("indicators", {})
    quote = (indicators.get("quote") or [{}])[0]
    if not timestamps or not isinstance(quote, dict):
        return None

    df = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(timestamps, unit="s", utc=True),
            "open": quote.get("open"),
            "high": quote.get("high"),
            "low": quote.get("low"),
            "close": quote.get("close"),
            "volume": quote.get("volume"),
        }
    )
    df = df.dropna(subset=["open", "high", "low", "close"])
    for col in ("open", "high", "low", "close", "volume"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["open", "high", "low", "close"])
    if df.empty:
        return None
    return df.reset_index(drop=True)
