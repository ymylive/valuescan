"""
Market data sources with fallback polling.
Sources: Binance, CoinMarketCap, CryptoCompare, CoinGecko.
"""

import os
import time
from typing import Any, Dict, List, Optional

import requests

from logger import logger

BINANCE_BASE = "https://api.binance.com"
COINGECKO_BASE = "https://api.coingecko.com/api/v3"
CMC_BASE = "https://pro-api.coinmarketcap.com/v1"
CRYPTOCOMPARE_BASE = "https://min-api.cryptocompare.com"

COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY", "").strip()
CMC_API_KEY = os.getenv("COINMARKETCAP_API_KEY", "").strip()
CRYPTOCOMPARE_API_KEY = os.getenv("CRYPTOCOMPARE_API_KEY", "").strip()
CRYPTO_NEWS_API_KEY = os.getenv("CRYPTO_NEWS_API_KEY", "").strip()

if not (COINGECKO_API_KEY and CMC_API_KEY and CRYPTOCOMPARE_API_KEY and CRYPTO_NEWS_API_KEY):
    try:
        import config as signal_config
        if not COINGECKO_API_KEY:
            COINGECKO_API_KEY = getattr(signal_config, "COINGECKO_API_KEY", "").strip()
        if not CMC_API_KEY:
            CMC_API_KEY = getattr(signal_config, "COINMARKETCAP_API_KEY", "").strip()
        if not CRYPTOCOMPARE_API_KEY:
            CRYPTOCOMPARE_API_KEY = getattr(signal_config, "CRYPTOCOMPARE_API_KEY", "").strip()
        if not CRYPTO_NEWS_API_KEY:
            CRYPTO_NEWS_API_KEY = getattr(signal_config, "CRYPTO_NEWS_API_KEY", "").strip()
    except Exception:
        pass

_session = requests.Session()
_coin_id_cache: Dict[str, str] = {}
_coin_id_last_fetch = 0.0


def _req(url: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> Optional[Any]:
    try:
        resp = _session.get(url, params=params, headers=headers, timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except Exception as exc:
        logger.debug("request failed: %s", exc)
    return None


def _safe_symbol(symbol: str) -> str:
    return symbol.upper().replace("$", "").replace("USDT", "").strip()


def _get_coingecko_id(symbol: str) -> Optional[str]:
    sym = _safe_symbol(symbol).lower()
    if sym in _coin_id_cache:
        return _coin_id_cache[sym]

    global _coin_id_last_fetch
    if time.time() - _coin_id_last_fetch < 3600 and _coin_id_cache:
        return _coin_id_cache.get(sym)

    data = _req(f"{COINGECKO_BASE}/coins/list", params=None, headers=_cg_headers())
    if not isinstance(data, list):
        return None
    _coin_id_cache.clear()
    for item in data:
        if not isinstance(item, dict):
            continue
        sid = item.get("symbol")
        cid = item.get("id")
        if sid and cid:
            _coin_id_cache[str(sid).lower()] = str(cid)
    _coin_id_last_fetch = time.time()
    return _coin_id_cache.get(sym)


def _cg_headers() -> Optional[Dict[str, str]]:
    if COINGECKO_API_KEY:
        return {"x-cg-demo-api-key": COINGECKO_API_KEY}
    return None


def fetch_binance_ticker(symbol: str) -> Optional[Dict[str, Any]]:
    sym = _safe_symbol(symbol)
    url = f"{BINANCE_BASE}/api/v3/ticker/24hr"
    data = _req(url, params={"symbol": f"{sym}USDT"})
    if not isinstance(data, dict):
        return None
    return {
        "price": float(data.get("lastPrice", 0) or 0),
        "price_change_percent": float(data.get("priceChangePercent", 0) or 0),
        "high_24h": float(data.get("highPrice", 0) or 0),
        "low_24h": float(data.get("lowPrice", 0) or 0),
        "volume_24h": float(data.get("quoteVolume", 0) or 0),
        "open_24h": float(data.get("openPrice", 0) or 0),
        "source": "binance",
    }


def fetch_cmc_ticker(symbol: str) -> Optional[Dict[str, Any]]:
    if not CMC_API_KEY:
        return None
    sym = _safe_symbol(symbol)
    headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY}
    data = _req(f"{CMC_BASE}/cryptocurrency/quotes/latest", params={"symbol": sym, "convert": "USD"}, headers=headers)
    if not isinstance(data, dict):
        return None
    item = (data.get("data") or {}).get(sym)
    if not isinstance(item, dict):
        return None
    quote = (item.get("quote") or {}).get("USD") or {}
    return {
        "price": float(quote.get("price", 0) or 0),
        "price_change_percent": float(quote.get("percent_change_24h", 0) or 0),
        "high_24h": float(quote.get("high_24h", 0) or 0),
        "low_24h": float(quote.get("low_24h", 0) or 0),
        "volume_24h": float(quote.get("volume_24h", 0) or 0),
        "market_cap": float(quote.get("market_cap", 0) or 0),
        "market_cap_rank": float(item.get("cmc_rank", 0) or 0),
        "source": "coinmarketcap",
    }


def fetch_cryptocompare_ticker(symbol: str) -> Optional[Dict[str, Any]]:
    if not CRYPTOCOMPARE_API_KEY:
        return None
    sym = _safe_symbol(symbol)
    headers = {"authorization": f"Apikey {CRYPTOCOMPARE_API_KEY}"}
    data = _req(f"{CRYPTOCOMPARE_BASE}/data/pricemultifull", params={"fsyms": sym, "tsyms": "USD"}, headers=headers)
    if not isinstance(data, dict):
        return None
    raw = (data.get("RAW") or {}).get(sym, {}).get("USD", {})
    if not isinstance(raw, dict):
        return None
    return {
        "price": float(raw.get("PRICE", 0) or 0),
        "price_change_percent": float(raw.get("CHANGEPCT24HOUR", 0) or 0),
        "high_24h": float(raw.get("HIGH24HOUR", 0) or 0),
        "low_24h": float(raw.get("LOW24HOUR", 0) or 0),
        "volume_24h": float(raw.get("VOLUME24HOURTO", 0) or 0),
        "market_cap": float(raw.get("MKTCAP", 0) or 0),
        "source": "cryptocompare",
    }


def fetch_coingecko_ticker(symbol: str) -> Optional[Dict[str, Any]]:
    coin_id = _get_coingecko_id(symbol)
    if not coin_id:
        return None
    data = _req(
        f"{COINGECKO_BASE}/coins/markets",
        params={"vs_currency": "usd", "ids": coin_id},
        headers=_cg_headers(),
    )
    if not isinstance(data, list) or not data:
        return None
    item = data[0]
    return {
        "price": float(item.get("current_price", 0) or 0),
        "price_change_percent": float(item.get("price_change_percentage_24h", 0) or 0),
        "high_24h": float(item.get("high_24h", 0) or 0),
        "low_24h": float(item.get("low_24h", 0) or 0),
        "volume_24h": float(item.get("total_volume", 0) or 0),
        "market_cap": float(item.get("market_cap", 0) or 0),
        "market_cap_rank": float(item.get("market_cap_rank", 0) or 0),
        "source": "coingecko",
    }


def fetch_market_snapshot(symbol: str) -> Optional[Dict[str, Any]]:
    providers = [
        fetch_binance_ticker,
        fetch_cmc_ticker,
        fetch_cryptocompare_ticker,
        fetch_coingecko_ticker,
    ]
    for provider in providers:
        data = provider(symbol)
        if data and data.get("price"):
            return data
    return None


def fetch_news(limit: int = 10) -> List[Dict[str, Any]]:
    news_key = CRYPTO_NEWS_API_KEY or CRYPTOCOMPARE_API_KEY
    if not news_key:
        return []
    headers = {"authorization": f"Apikey {news_key}"}
    data = _req(f"{CRYPTOCOMPARE_BASE}/data/v2/news/", params={"lang": "EN"}, headers=headers)
    if not isinstance(data, dict):
        return []
    items = data.get("Data") or []
    news = []
    for item in items[:limit]:
        if not isinstance(item, dict):
            continue
        news.append({
            "title": item.get("title"),
            "url": item.get("url"),
            "source": item.get("source"),
            "published_at": item.get("published_on"),
        })
    return news


def fetch_trending(limit: int = 10) -> List[Dict[str, Any]]:
    data = _req(f"{COINGECKO_BASE}/search/trending", headers=_cg_headers())
    if isinstance(data, dict):
        coins = data.get("coins") or []
        out = []
        for item in coins[:limit]:
            inner = item.get("item") if isinstance(item, dict) else None
            if not isinstance(inner, dict):
                continue
            out.append({
                "symbol": inner.get("symbol"),
                "name": inner.get("name"),
                "market_cap_rank": inner.get("market_cap_rank"),
            })
        if out:
            return out
    # fallback: CMC top list
    if CMC_API_KEY:
        headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY}
        data = _req(
            f"{CMC_BASE}/cryptocurrency/listings/latest",
            params={"convert": "USD", "limit": limit},
            headers=headers,
        )
        if isinstance(data, dict):
            items = data.get("data") or []
            out = []
            for item in items[:limit]:
                if not isinstance(item, dict):
                    continue
                out.append({
                    "symbol": item.get("symbol"),
                    "name": item.get("name"),
                    "market_cap_rank": item.get("cmc_rank"),
                })
            return out
    return []
