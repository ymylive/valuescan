"""
Market data sources with fallback polling.
Sources: Binance, CoinMarketCap, CryptoCompare, CoinGecko.
"""

import os
import time
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

import requests

try:
    from signal_monitor.logger import logger
except Exception:
    from logger import logger

try:
    from ccxt_data import fetch_ccxt_snapshot
except Exception:
    fetch_ccxt_snapshot = None

BINANCE_BASE = "https://api.binance.com"
BINANCE_FUT_BASE = "https://fapi.binance.com"
COINGECKO_BASE = "https://api.coingecko.com/api/v3"
CMC_BASE = "https://pro-api.coinmarketcap.com/v1"
CRYPTOCOMPARE_BASE = "https://min-api.cryptocompare.com"

COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY", "").strip()
CMC_API_KEY = os.getenv("COINMARKETCAP_API_KEY", "").strip()
CRYPTOCOMPARE_API_KEY = os.getenv("CRYPTOCOMPARE_API_KEY", "").strip()

if not (COINGECKO_API_KEY and CMC_API_KEY and CRYPTOCOMPARE_API_KEY):
    try:
        import config as signal_config
        if not COINGECKO_API_KEY:
            COINGECKO_API_KEY = getattr(signal_config, "COINGECKO_API_KEY", "").strip()
        if not CMC_API_KEY:
            CMC_API_KEY = getattr(signal_config, "COINMARKETCAP_API_KEY", "").strip()
        if not CRYPTOCOMPARE_API_KEY:
            CRYPTOCOMPARE_API_KEY = getattr(signal_config, "CRYPTOCOMPARE_API_KEY", "").strip()
    except Exception:
        pass



def _load_market_alert_config() -> dict:
    cfg_path = Path(__file__).with_name("market_alert_config.json")
    if not cfg_path.exists():
        return {}
    try:
        return json.loads(cfg_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _get_metals_config() -> dict:
    cfg = {
        "enabled": False,
        "symbols": ["XAUUSD", "XAGUSD", "XAUUSDT", "XAGUSDT", "XAU", "XAG"],
        "yahoo_symbol_map": {
            "XAUUSD": "GC=F",
            "XAGUSD": "SI=F",
        },
    }
    raw_symbols = os.getenv("NOFX_METALS_SYMBOLS", "").strip()
    if raw_symbols:
        symbols = [s.strip().upper() for s in raw_symbols.split(",") if s.strip()]
        if symbols:
            cfg["symbols"] = symbols
            cfg["enabled"] = True
    raw_map = os.getenv("NOFX_METALS_SYMBOL_MAP", "").strip()
    if raw_map:
        try:
            parsed = json.loads(raw_map)
            if isinstance(parsed, dict):
                cfg["yahoo_symbol_map"].update({str(k).upper(): str(v) for k, v in parsed.items()})
                cfg["enabled"] = True
        except Exception:
            pass
    file_cfg = _load_market_alert_config()
    metals_cfg = file_cfg.get("metals", {}) if isinstance(file_cfg, dict) else {}
    if isinstance(metals_cfg, dict):
        if "enabled" in metals_cfg:
            cfg["enabled"] = bool(metals_cfg.get("enabled"))
        if isinstance(metals_cfg.get("symbols"), list) and metals_cfg.get("symbols"):
            cfg["symbols"] = [str(s).upper() for s in metals_cfg["symbols"]]
        if isinstance(metals_cfg.get("yahoo_symbol_map"), dict):
            cfg["yahoo_symbol_map"].update({str(k).upper(): str(v) for k, v in metals_cfg["yahoo_symbol_map"].items()})
    return cfg


def _is_metal_symbol(symbol: str) -> bool:
    sym = _safe_symbol(symbol)
    cfg = _get_metals_config()
    symbols = cfg.get("symbols") if isinstance(cfg, dict) else []
    symbol_set = set([str(s).upper() for s in symbols])
    if sym in symbol_set:
        return True
    if sym in ("XAU", "XAG"):
        return True
    if f"{sym}USD" in symbol_set or f"{sym}USDT" in symbol_set:
        return True
    return False


def is_metal_symbol(symbol: str) -> bool:
    return _is_metal_symbol(symbol)


def _fetch_yahoo_quote(symbol: str) -> Optional[Dict[str, Any]]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
    }
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1m&range=1d"
    data = _req(url, headers=headers)
    result: List[Dict[str, Any]] = []
    if isinstance(data, dict):
        result = data.get("chart", {}).get("result", []) or []
    if not result:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1h&range=5d"
        data = _req(url, headers=headers)
        if not isinstance(data, dict):
            return None
        result = data.get("chart", {}).get("result", [])
        if not result:
            return None
    meta = result[0].get("meta", {})
    current = meta.get("regularMarketPrice")
    previous_close = meta.get("previousClose") or meta.get("chartPreviousClose")
    market_time = meta.get("regularMarketTime")
    if isinstance(market_time, (int, float, str)):
        try:
            market_time = int(float(market_time))
        except Exception:
            market_time = None
    if current is None or previous_close in (None, 0):
        return _fetch_yahoo_quote_v7(symbol)
    return {
        "price": float(current),
        "price_change_percent": ((float(current) - float(previous_close)) / float(previous_close)) * 100,
        "high_24h": float(meta.get("dayHigh", 0) or 0),
        "low_24h": float(meta.get("dayLow", 0) or 0),
        "volume_24h": float(meta.get("regularMarketVolume", 0) or 0),
        "market_time": market_time,
        "as_of": datetime.fromtimestamp(market_time, tz=timezone.utc).isoformat() if market_time else None,
        "source": "yahoo",
    }


def _fetch_yahoo_quote_v7(symbol: str) -> Optional[Dict[str, Any]]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
    }
    url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={symbol}"
    data = _req(url, headers=headers)
    if not isinstance(data, dict):
        return None
    result = data.get("quoteResponse", {}).get("result", [])
    if not result:
        return None
    item = result[0]
    current = item.get("regularMarketPrice")
    previous_close = item.get("regularMarketPreviousClose") or item.get("regularMarketPreviousClose")
    market_time = item.get("regularMarketTime")
    if isinstance(market_time, (int, float, str)):
        try:
            market_time = int(float(market_time))
        except Exception:
            market_time = None
    if current is None or previous_close in (None, 0):
        return None
    return {
        "price": float(current),
        "price_change_percent": ((float(current) - float(previous_close)) / float(previous_close)) * 100,
        "high_24h": float(item.get("regularMarketDayHigh", 0) or 0),
        "low_24h": float(item.get("regularMarketDayLow", 0) or 0),
        "volume_24h": float(item.get("regularMarketVolume", 0) or 0),
        "market_time": market_time,
        "as_of": datetime.fromtimestamp(market_time, tz=timezone.utc).isoformat() if market_time else None,
        "source": "yahoo",
    }

_session = requests.Session()
_coin_id_cache: Dict[str, str] = {}
_coin_id_last_fetch = 0.0
_SNAPSHOT_CACHE_TTL = int(os.getenv("NOFX_SNAPSHOT_CACHE_TTL", "600") or 600)
_METALS_SNAPSHOT_TTL = int(os.getenv("NOFX_METALS_SNAPSHOT_TTL", "0") or 0)
_METALS_FRESH_SECS = int(os.getenv("NOFX_METALS_FRESH_SECS", "900") or 900)
_SNAPSHOT_CACHE_MAX_SIZE = int(os.getenv("NOFX_SNAPSHOT_CACHE_MAX_SIZE", "512") or 512)
_SNAPSHOT_CACHE: Dict[str, Dict[str, Any]] = {}
COINGECKO_ID_OVERRIDES = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "BNB": "binancecoin",
    "SOL": "solana",
    "ADA": "cardano",
    "XRP": "ripple",
    "DOGE": "dogecoin",
    "LTC": "litecoin",
    "AVAX": "avalanche-2",
    "MATIC": "matic-network",
    "ARB": "arbitrum",
    "OP": "optimism",
    "LINK": "chainlink",
    "UNI": "uniswap",
    "AAVE": "aave",
    "LDO": "lido-dao",
    "MKR": "maker",
    "COMP": "compound-governance-token",
    "USDT": "tether",
    "USDC": "usd-coin",
    "DAI": "dai",
}


def _cache_snapshot(symbol: str, snapshot: Dict[str, Any]) -> None:
    if not snapshot:
        return
    _prune_snapshot_cache()
    _SNAPSHOT_CACHE[symbol] = {"ts": time.time(), "data": snapshot}
    _prune_snapshot_cache()


def _get_snapshot_ttl(symbol: str) -> int:
    return _METALS_SNAPSHOT_TTL if _is_metal_symbol(symbol) else _SNAPSHOT_CACHE_TTL


def _prune_snapshot_cache() -> None:
    now = time.time()

    expired: List[str] = []
    for key, entry in _SNAPSHOT_CACHE.items():
        ts = entry.get("ts")
        if not isinstance(ts, (int, float)):
            expired.append(key)
            continue
        ttl = _get_snapshot_ttl(key)
        if ttl > 0 and now-ts > ttl:
            expired.append(key)

    for key in expired:
        _SNAPSHOT_CACHE.pop(key, None)

    if _SNAPSHOT_CACHE_MAX_SIZE <= 0 or len(_SNAPSHOT_CACHE) <= _SNAPSHOT_CACHE_MAX_SIZE:
        return

    oldest_keys = sorted(
        _SNAPSHOT_CACHE.items(),
        key=lambda item: float(item[1].get("ts", 0)),
    )
    for key, _ in oldest_keys[: len(_SNAPSHOT_CACHE) - _SNAPSHOT_CACHE_MAX_SIZE]:
        _SNAPSHOT_CACHE.pop(key, None)


def _get_cached_snapshot(symbol: str) -> Optional[Dict[str, Any]]:
    _prune_snapshot_cache()
    entry = _SNAPSHOT_CACHE.get(symbol)
    if not entry:
        return None
    ts = entry.get("ts")
    if not isinstance(ts, (int, float)):
        return None
    ttl = _get_snapshot_ttl(symbol)
    if ttl <= 0:
        return None
    if time.time() - ts > ttl:
        return None
    data = entry.get("data")
    return data if isinstance(data, dict) else None

CRYPTO_SOURCE_WEIGHTS = {
    "binance": 0.3,
    "ccxt": 0.2,
    "coingecko": 0.2,
    "coinmarketcap": 0.15,
    "cryptocompare": 0.15,
}


def _merge_snapshots(base: Dict[str, Any], extra: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base)
    for key, value in (extra or {}).items():
        if value is None:
            continue
        if key == "source":
            if merged.get("source"):
                if value not in str(merged["source"]):
                    merged["source"] = f"{merged['source']}+{value}"
            else:
                merged["source"] = value
            continue
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            nested = dict(merged[key])
            for sub_key, sub_val in value.items():
                if sub_val is None:
                    continue
                if nested.get(sub_key) in (None, 0, "", []):
                    nested[sub_key] = sub_val
            merged[key] = nested
            continue
        if merged.get(key) in (None, 0, "", []):
            merged[key] = value
    return merged


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
    sym = _safe_symbol(symbol).upper()
    override = COINGECKO_ID_OVERRIDES.get(sym)
    if override:
        return override
    sym = sym.lower()
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


def get_coingecko_id(symbol: str) -> Optional[str]:
    return _get_coingecko_id(symbol)


def _cg_headers() -> Optional[Dict[str, str]]:
    if COINGECKO_API_KEY:
        return {"x-cg-demo-api-key": COINGECKO_API_KEY}
    return None


def get_coingecko_headers() -> Optional[Dict[str, str]]:
    return _cg_headers()


def fetch_binance_ticker(symbol: str) -> Optional[Dict[str, Any]]:
    sym = _safe_symbol(symbol)
    url = f"{BINANCE_BASE}/api/v3/ticker/24hr"
    data = _req(url, params={"symbol": f"{sym}USDT"})
    if not isinstance(data, dict):
        return None
    close_time = data.get("closeTime")
    if isinstance(close_time, (int, float, str)):
        try:
            close_time = int(float(close_time))
        except Exception:
            close_time = None
    return {
        "price": float(data.get("lastPrice", 0) or 0),
        "price_change_percent": float(data.get("priceChangePercent", 0) or 0),
        "high_24h": float(data.get("highPrice", 0) or 0),
        "low_24h": float(data.get("lowPrice", 0) or 0),
        "volume_24h": float(data.get("quoteVolume", 0) or 0),
        "open_24h": float(data.get("openPrice", 0) or 0),
        "market_time": close_time,
        "as_of": datetime.fromtimestamp(close_time / 1000, tz=timezone.utc).isoformat() if close_time else None,
        "source": "binance",
    }


def _fetch_binance_futures_ticker(symbol: str) -> Optional[Dict[str, Any]]:
    sym = _safe_symbol(symbol)
    if sym in ("XAUUSD", "XAGUSD"):
        sym = f"{sym}T"
    if not sym.endswith("USDT"):
        sym = f"{sym}USDT"
    url = f"{BINANCE_FUT_BASE}/fapi/v1/ticker/24hr"
    data = _req(url, params={"symbol": sym})
    if not isinstance(data, dict):
        return None
    close_time = data.get("closeTime")
    if isinstance(close_time, (int, float, str)):
        try:
            close_time = int(float(close_time))
        except Exception:
            close_time = None
    return {
        "price": float(data.get("lastPrice", 0) or 0),
        "price_change_percent": float(data.get("priceChangePercent", 0) or 0),
        "high_24h": float(data.get("highPrice", 0) or 0),
        "low_24h": float(data.get("lowPrice", 0) or 0),
        "volume_24h": float(data.get("quoteVolume", 0) or 0),
        "open_24h": float(data.get("openPrice", 0) or 0),
        "market_time": close_time,
        "as_of": datetime.fromtimestamp(close_time / 1000, tz=timezone.utc).isoformat() if close_time else None,
        "source": "binance_futures",
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


def fetch_market_snapshot(symbol: str, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
    cache_key = _safe_symbol(symbol)
    cached = None if force_refresh else _get_cached_snapshot(cache_key)
    if cached:
        return cached
    fallback_cached = _get_cached_snapshot(cache_key) if force_refresh else None
    if _is_metal_symbol(symbol):
        base = _safe_symbol(symbol)
        data = _fetch_binance_futures_ticker(base)
        if data:
            _cache_snapshot(cache_key, data)
            return data
    providers = [
        fetch_ccxt_snapshot,
        fetch_binance_ticker,
        fetch_cmc_ticker,
        fetch_cryptocompare_ticker,
        fetch_coingecko_ticker,
    ]
    merged: Dict[str, Any] = {}
    for provider in providers:
        if not provider:
            continue
        data = provider(symbol)
        if not isinstance(data, dict):
            continue
        merged = _merge_snapshots(merged, data)
    if merged and merged.get("price"):
        _cache_snapshot(cache_key, merged)
        return merged
    if fallback_cached:
        return fallback_cached
    cached = _get_cached_snapshot(cache_key)
    if cached:
        return cached
    return None


def fetch_market_snapshot_with_sources(symbol: str) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    providers = [
        ("ccxt", fetch_ccxt_snapshot),
        ("binance", fetch_binance_ticker),
        ("coinmarketcap", fetch_cmc_ticker),
        ("cryptocompare", fetch_cryptocompare_ticker),
        ("coingecko", fetch_coingecko_ticker),
    ]
    merged: Dict[str, Any] = {}
    sources: List[Dict[str, Any]] = []
    for name, provider in providers:
        if not provider:
            continue
        data = provider(symbol)
        if not isinstance(data, dict):
            continue
        sources.append({"name": name, "weight": CRYPTO_SOURCE_WEIGHTS.get(name, 0.1), "data": data})
        merged = _merge_snapshots(merged, data)
    snapshot = merged if merged and merged.get("price") else None
    return snapshot, sources


def fetch_news(limit: int = 10) -> List[Dict[str, Any]]:
    if not CRYPTOCOMPARE_API_KEY:
        return []
    headers = {"authorization": f"Apikey {CRYPTOCOMPARE_API_KEY}"}
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


def _calc_liquidation_stats(items: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(items, list) or not items:
        return None
    buy_notional = 0.0
    sell_notional = 0.0
    buy_count = 0
    sell_count = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        try:
            price = float(item.get("price", 0) or 0)
            qty = float(item.get("origQty", 0) or 0)
        except Exception:
            continue
        notional = price * qty
        side = str(item.get("side") or "").upper()
        if side == "BUY":
            buy_notional += notional
            buy_count += 1
        elif side == "SELL":
            sell_notional += notional
            sell_count += 1
    total = buy_notional + sell_notional
    return {
        "buy_notional": buy_notional,
        "sell_notional": sell_notional,
        "buy_count": buy_count,
        "sell_count": sell_count,
        "total_notional": total,
    }


def fetch_binance_futures_snapshot(symbol: str) -> Optional[Dict[str, Any]]:
    sym = _safe_symbol(symbol)
    if not sym:
        return None
    pair = f"{sym}USDT"

    payload: Dict[str, Any] = {"source": "binance_futures"}
    end_ms = int(time.time() * 1000)
    start_ms = end_ms - 24 * 60 * 60 * 1000

    requests_map = {
        "funding": (
            f"{BINANCE_FUT_BASE}/fapi/v1/fundingRate",
            {"symbol": pair, "limit": 1},
        ),
        "open_interest": (
            f"{BINANCE_FUT_BASE}/fapi/v1/openInterest",
            {"symbol": pair},
        ),
        "oi_hist": (
            f"{BINANCE_FUT_BASE}/futures/data/openInterestHist",
            {"symbol": pair, "period": "1h", "limit": 2},
        ),
        "ls_ratio": (
            f"{BINANCE_FUT_BASE}/futures/data/globalLongShortAccountRatio",
            {"symbol": pair, "period": "5m", "limit": 1},
        ),
        "taker": (
            f"{BINANCE_FUT_BASE}/futures/data/takerlongshortRatio",
            {"symbol": pair, "period": "15m", "limit": 1},
        ),
        "liq": (
            f"{BINANCE_FUT_BASE}/fapi/v1/forceOrders",
            {"symbol": pair, "startTime": start_ms, "endTime": end_ms, "limit": 1000},
        ),
    }

    results: Dict[str, Any] = {}
    with ThreadPoolExecutor(max_workers=len(requests_map)) as executor:
        future_map = {
            key: executor.submit(_req, url, params=params)
            for key, (url, params) in requests_map.items()
        }
        for key, future in future_map.items():
            try:
                results[key] = future.result()
            except Exception:
                results[key] = None

    funding = results.get("funding")
    if isinstance(funding, list) and funding:
        try:
            payload["funding_rate"] = float(funding[-1].get("fundingRate", 0) or 0)
            payload["funding_time"] = funding[-1].get("fundingTime")
        except Exception:
            pass

    open_interest = results.get("open_interest")
    if isinstance(open_interest, dict):
        try:
            payload["open_interest"] = float(open_interest.get("openInterest", 0) or 0)
        except Exception:
            pass

    oi_hist = results.get("oi_hist")
    if isinstance(oi_hist, list) and len(oi_hist) >= 2:
        try:
            prev = float(oi_hist[-2].get("sumOpenInterest", 0) or 0)
            curr = float(oi_hist[-1].get("sumOpenInterest", 0) or 0)
            if prev > 0:
                payload["open_interest_change_1h_pct"] = (curr - prev) / prev * 100.0
        except Exception:
            pass

    ls_ratio = results.get("ls_ratio")
    if isinstance(ls_ratio, list) and ls_ratio:
        row = ls_ratio[-1] if isinstance(ls_ratio[-1], dict) else None
        if row:
            payload["long_short_ratio"] = {
                "ratio": row.get("longShortRatio"),
                "long_account": row.get("longAccount"),
                "short_account": row.get("shortAccount"),
                "timestamp": row.get("timestamp"),
            }

    taker = results.get("taker")
    if isinstance(taker, list) and taker:
        row = taker[-1] if isinstance(taker[-1], dict) else None
        if row:
            try:
                buy_vol = float(row.get("buyVol", 0) or 0)
                sell_vol = float(row.get("sellVol", 0) or 0)
            except Exception:
                buy_vol = 0.0
                sell_vol = 0.0
            total = buy_vol + sell_vol
            payload["taker_flow_15m"] = {
                "buy_vol": buy_vol,
                "sell_vol": sell_vol,
                "net": buy_vol - sell_vol,
                "ratio": buy_vol / total if total > 0 else 0.5,
            }

    liq = results.get("liq")
    liq_stats = _calc_liquidation_stats(liq)
    if liq_stats:
        payload["liquidations_24h"] = liq_stats

    return payload if len(payload) > 1 else None
