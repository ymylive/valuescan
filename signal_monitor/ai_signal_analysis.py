#!/usr/bin/env python3


"""


AI per-signal analysis.


Builds a compact snapshot (key levels, patterns, fund flow) and asks the


configured AI endpoint to produce a short professional read.


"""





import json


import os


import time


from pathlib import Path


from datetime import datetime, timedelta, timezone


from typing import Any, Dict, List, Optional





import requests

try:
    from .ai_api_utils import (
        AI_PROTOCOL_RESPONSES,
        build_payload,
        override_responses_token_key,
        parse_compatible_content,
        parse_responses_body,
        resolve_protocol_and_url,
        resolve_responses_token_key_override,
        should_force_responses_stream,
    )
except Exception:
    from ai_api_utils import (  # type: ignore[import-not-found]
        AI_PROTOCOL_RESPONSES,
        build_payload,
        override_responses_token_key,
        parse_compatible_content,
        parse_responses_body,
        resolve_protocol_and_url,
        resolve_responses_token_key_override,
        should_force_responses_stream,
    )
try:
    from .ai_request_queue import call_ai_with_queue
except Exception:
    from ai_request_queue import call_ai_with_queue  # type: ignore[import-not-found]





try:


    from .logger import logger


except Exception:


    try:


        from logger import logger


    except Exception:


        from signal_monitor.logger import logger


try:
    import config as signal_config
except Exception:
    signal_config = None


_SNAPSHOT_CACHE_TTL = int(os.getenv("NOFX_AI_SNAPSHOT_CACHE_TTL", "900") or 900)


_SNAPSHOT_CACHE: Dict[str, Dict[str, Any]] = {}
_YAHOO_KLINES_TTL = int(os.getenv("NOFX_YAHOO_KLINES_TTL", "21600") or 21600)
_YAHOO_KLINES_CACHE: Dict[str, Dict[str, Any]] = {}
_YAHOO_KLINES_CACHE_PATH = Path(__file__).parent / "yahoo_klines_cache.json"
_YAHOO_KLINES_CACHE_LOADED = False


try:
    _NOFX_PROMPT_LIMIT = int(os.getenv("NOFX_AI_NOFX_LIMIT", "10") or 10)
except ValueError:
    _NOFX_PROMPT_LIMIT = 10

try:
    _NOFX_STRATEGY_LIMIT = int(os.getenv("NOFX_AI_NOFX_STRATEGY_LIMIT", "5") or 5)
except ValueError:
    _NOFX_STRATEGY_LIMIT = 5











def get_ai_signal_config():
    """Load AI signal brief config from JSON file."""
    import json
    from pathlib import Path

    config_path = Path(__file__).parent / "ai_signal_config.json"
    default_enabled = True
    try:
        import config as signal_config
        default_enabled = bool(getattr(signal_config, "ENABLE_AI_SIGNAL_ANALYSIS", default_enabled))
    except Exception:
        pass

    default_protocol = os.getenv("NOFX_AI_SIGNAL_API_PROTOCOL", "auto").strip()
    defaults = {
        "enabled": default_enabled,
        "api_key": os.getenv("AI_SIGNAL_API_KEY", ""),
        "api_url": os.getenv("AI_SIGNAL_API_URL", "https://chat.cornna.xyz/v1"),
        "model": os.getenv("AI_SIGNAL_MODEL", "gemini-3-flash-search"),
        "api_protocol": default_protocol,
    }

    if config_path.exists():
        try:
            file_config = json.loads(config_path.read_text(encoding="utf-8"))
            return {**defaults, **file_config}
        except Exception:
            pass
    return defaults

from chart_pro_v10 import (


    get_klines,


    get_orderbook,


    calculate_atr,


    detect_channel,


    detect_best_flag,


    detect_best_wedge,


    detect_best_triangle,


    PATTERN_SCORE_THRESHOLDS,


)


from ai_key_levels_cache import set_levels


from ai_overlays_cache import set_overlays


from market_data_sources import fetch_market_snapshot
from fundamentals_sources import (
    fetch_fundamentals_snapshot,
    fetch_macro_snapshot,
    fetch_metals_fundamentals,
)
from macro_data import load_macro_data

# 资金流数据模块

try:
    from nofx_data_sources import (
        fetch_nofx_competition,
        fetch_nofx_public_strategies,
        fetch_nofx_top_traders,
    )
except ImportError:
    fetch_nofx_competition = None
    fetch_nofx_public_strategies = None
    fetch_nofx_top_traders = None


def _get_language() -> str:
    return "zh"
def _load_upcoming_events() -> Dict[str, Any]:


    raw = (os.getenv("NOFX_UPCOMING_EVENTS_JSON") or "").strip()


    if raw:


        try:


            data = json.loads(raw)


            if isinstance(data, dict):


                return data


            if isinstance(data, list):


                return {"items": data}


        except Exception:


            return {"note": "invalid_env_json"}


    path = Path(__file__).parent / "upcoming_events.json"


    if path.exists():


        try:


            data = json.loads(path.read_text(encoding="utf-8"))


            if isinstance(data, dict):


                return data


            if isinstance(data, list):


                return {"items": data}


        except Exception:


            return {"note": "invalid_file_json"}


    return {}








def _safe_symbol(symbol: str) -> str:
    return str(symbol or "").upper().replace("$", "").replace("USDT", "").strip()


def _load_market_alert_config() -> Dict[str, Any]:
    cfg_path = Path(__file__).parent / "market_alert_config.json"
    if not cfg_path.exists():
        return {}
    try:
        return json.loads(cfg_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _get_metals_config() -> Dict[str, Any]:
    cfg: Dict[str, Any] = {
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


def _get_metals_symbols() -> List[str]:
    cfg = _get_metals_config()
    symbols = cfg.get("symbols") if isinstance(cfg, dict) else None
    if isinstance(symbols, list) and symbols:
        return [str(s).upper() for s in symbols]
    return ["XAUUSD", "XAGUSD", "XAUUSDT", "XAGUSDT", "XAU", "XAG"]


def _get_metals_symbol_map() -> Dict[str, str]:
    cfg = _get_metals_config()
    symbol_map = cfg.get("yahoo_symbol_map") if isinstance(cfg, dict) else None
    if isinstance(symbol_map, dict):
        return {str(k).upper(): str(v) for k, v in symbol_map.items()}
    return {"XAUUSD": "GC=F", "XAGUSD": "SI=F"}


def _is_metal_symbol(symbol: str) -> bool:
    base = _safe_symbol(symbol).upper()
    symbols = set(_get_metals_symbols())
    if base in symbols:
        return True
    if base in ("XAU", "XAG"):
        return True
    if f"{base}USD" in symbols or f"{base}USDT" in symbols:
        return True
    return False








BEIJING_TZ = timezone(timedelta(hours=8))








def _load_recent_signal_settings() -> Dict[str, Any]:


    lookback_hours = None


    limit = None


    raw_lookback = os.getenv("NOFX_AI_SIGNAL_LOOKBACK_HOURS")


    raw_limit = os.getenv("NOFX_AI_SIGNAL_RECENT_LIMIT")


    if raw_lookback:


        try:


            lookback_hours = float(raw_lookback)


        except Exception:


            lookback_hours = None


    if raw_limit:


        try:


            limit = int(raw_limit)


        except Exception:


            limit = None





    if lookback_hours is None or limit is None:


        try:


            import config as signal_config


        except Exception:


            signal_config = None


        if signal_config:


            if lookback_hours is None:


                try:


                    lookback_hours = float(getattr(signal_config, "AI_SIGNAL_LOOKBACK_HOURS", 24))


                except Exception:


                    lookback_hours = None


            if limit is None:


                try:


                    limit = int(getattr(signal_config, "AI_SIGNAL_RECENT_LIMIT", 120))


                except Exception:


                    limit = None





    if lookback_hours is None:


        lookback_hours = 24.0


    if limit is None:


        limit = 0


    limit = int(limit)


    lookback_hours = max(1.0, float(lookback_hours))


    return {"lookback_hours": lookback_hours, "limit": limit}


def _format_beijing_time(timestamp_ms: Optional[int]) -> str:


    if not timestamp_ms:


        return ""


    try:


        dt = datetime.fromtimestamp(float(timestamp_ms) / 1000, tz=BEIJING_TZ)


    except Exception:


        return ""


    return dt.strftime("%Y-%m-%d %H:%M:%S")








def _classify_signal_sentiment(message_type: Any, title: str = "") -> str:


    bullish_types = {100, 101, 108, 110, 111}


    bearish_types = {102, 103, 109, 112}


    try:


        msg_type = int(message_type)


    except Exception:


        msg_type = None





    if msg_type in bullish_types:


        return "看涨"


    if msg_type in bearish_types:


        return "看跌"





    title_lower = (title or "").lower()


    bullish_tokens = ["看涨", "上涨", "拉升", "买入", "突破", "增持", "bull", "long"]


    bearish_tokens = ["看跌", "下跌", "回落", "卖出", "跌破", "减持", "bear", "short"]


    if any(token in title_lower for token in bullish_tokens):


        return "看涨"


    if any(token in title_lower for token in bearish_tokens):


        return "看跌"


    return "neutral"








def _compact_recent_signals(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:


    compacted: List[Dict[str, Any]] = []


    for msg in messages:


        if not isinstance(msg, dict):


            continue


        content = msg.get("content") or ""


        parsed_content = {}


        if isinstance(content, dict):


            parsed_content = content


        elif isinstance(content, str):


            stripped = content.strip()


            if stripped.startswith("{") and stripped.endswith("}"):


                try:


                    parsed_content = json.loads(stripped)


                except Exception:


                    parsed_content = {}





        title = msg.get("title") or parsed_content.get("titleSimplified") or parsed_content.get("title") or "未知信号"


        sentiment = _classify_signal_sentiment(msg.get("type"), title)


        compacted.append(


            {


                "name": title,


                "sentiment": sentiment,


            }


        )


    return compacted








def _get_recent_signals_for_symbol(symbol: str) -> Dict[str, Any]:


    settings = _load_recent_signal_settings()


    lookback_hours = settings.get("lookback_hours", 24.0)


    limit = settings.get("limit", 120)


    cutoff_ms = int((time.time() - (lookback_hours * 3600)) * 1000)


    messages: List[Dict[str, Any]] = []


    try:


        try:


            from database import MessageDatabase


        except Exception:


            from signal_monitor.database import MessageDatabase


        db = MessageDatabase()


        messages = db.get_recent_messages_for_symbol(


            _safe_symbol(symbol),


            limit=limit,


            since_timestamp_ms=cutoff_ms,


        )


    except Exception:


        messages = []


    return {


        "lookback_hours": lookback_hours,


        "total": len(messages),


        "coverage": "all",


        "items": _compact_recent_signals(messages),


    }








def _fetch_taker_flow(symbol: str) -> Dict[str, Dict[str, float]]:


    base = _safe_symbol(symbol)


    sym = f"{base}USDT"


    periods = ["15m", "1h", "4h", "1d"]


    result: Dict[str, Dict[str, float]] = {}


    for period in periods:


        try:


            url = "https://fapi.binance.com/futures/data/takerlongshortRatio"


            resp = requests.get(url, params={"symbol": sym, "period": period, "limit": 1}, timeout=10)


            if resp.status_code != 200:


                continue


            data = resp.json()


            if not isinstance(data, list) or not data:


                continue


            row = data[-1]


            buy_vol = float(row.get("buyVol", 0) or 0)


            sell_vol = float(row.get("sellVol", 0) or 0)


            total = buy_vol + sell_vol


            ratio = buy_vol / total if total > 0 else 0.5


            result[period] = {


                "buy_vol": buy_vol,


                "sell_vol": sell_vol,


                "net": buy_vol - sell_vol,


                "ratio": ratio,


            }


        except Exception:


            continue


    return result








def _get_cached_klines(symbol: str):


    key = str(symbol).upper().strip()


    entry = _SNAPSHOT_CACHE.get(key)


    if not entry:


        return None


    if time.time() - float(entry.get('ts', 0)) > _SNAPSHOT_CACHE_TTL:


        return None


    return entry.get('df')





def _update_cached_klines(symbol: str, df) -> None:


    key = str(symbol).upper().strip()


    _SNAPSHOT_CACHE[key] = {'ts': time.time(), 'df': df}


def _get_cached_yahoo_klines(symbol: str) -> Optional[List[Dict[str, Any]]]:
    _load_yahoo_klines_cache()
    key = str(symbol or "").upper().strip()
    entry = _YAHOO_KLINES_CACHE.get(key)
    if not entry:
        return None
    ts = entry.get("ts")
    if not isinstance(ts, (int, float)):
        return None
    if _YAHOO_KLINES_TTL > 0 and (time.time() - float(ts)) > _YAHOO_KLINES_TTL:
        return None
    data = entry.get("data")
    return data if isinstance(data, list) else None


def _update_cached_yahoo_klines(symbol: str, klines: List[Dict[str, Any]]) -> None:
    if not klines:
        return
    _load_yahoo_klines_cache()
    key = str(symbol or "").upper().strip()
    _YAHOO_KLINES_CACHE[key] = {"ts": time.time(), "data": klines}
    _save_yahoo_klines_cache()


def _load_yahoo_klines_cache() -> None:
    global _YAHOO_KLINES_CACHE_LOADED
    if _YAHOO_KLINES_CACHE_LOADED:
        return
    _YAHOO_KLINES_CACHE_LOADED = True
    if not _YAHOO_KLINES_CACHE_PATH.exists():
        return
    try:
        raw = json.loads(_YAHOO_KLINES_CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return
    if not isinstance(raw, dict):
        return
    for key, entry in raw.items():
        if not isinstance(entry, dict):
            continue
        ts = entry.get("ts")
        data = entry.get("data")
        if isinstance(ts, (int, float)) and isinstance(data, list):
            _YAHOO_KLINES_CACHE[str(key).upper()] = {"ts": ts, "data": data}


def _save_yahoo_klines_cache() -> None:
    if not _YAHOO_KLINES_CACHE:
        return
    try:
        payload = {
            key: {"ts": entry.get("ts"), "data": entry.get("data")}
            for key, entry in _YAHOO_KLINES_CACHE.items()
            if isinstance(entry, dict)
        }
        _YAHOO_KLINES_CACHE_PATH.write_text(
            json.dumps(payload, ensure_ascii=True, separators=(",", ":")),
            encoding="utf-8",
        )
    except Exception:
        pass







def _fetch_yahoo_klines(
    symbol: str,
    attempts: Optional[List[Dict[str, str]]] = None,
    min_points: Optional[int] = None,
) -> List[Dict[str, Any]]:
    cached = _get_cached_yahoo_klines(symbol)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
    }
    attempts = attempts or [
        {"interval": "1h", "range": "5d"},
        {"interval": "1d", "range": "6mo"},
    ]
    best: List[Dict[str, Any]] = []
    for attempt in attempts:
        try:
            url = (
                f"https://query1.finance.yahoo.com/v8/finance/chart/"
                f"{symbol}?interval={attempt['interval']}&range={attempt['range']}"
            )
            resp = requests.get(url, headers=headers, timeout=12)
            if resp.status_code != 200:
                continue
            data = resp.json()
            result = (data.get("chart") or {}).get("result") or []
            if not result:
                continue
            payload = result[0]
            timestamps = payload.get("timestamp") or []
            quote = (payload.get("indicators") or {}).get("quote") or []
            if not timestamps or not quote:
                continue
            quote = quote[0] if isinstance(quote, list) else quote
            opens = quote.get("open") or []
            highs = quote.get("high") or []
            lows = quote.get("low") or []
            closes = quote.get("close") or []
            volumes = quote.get("volume") or []
            klines = []
            for i, ts in enumerate(timestamps):
                try:
                    o = float(opens[i]) if opens[i] is not None else None
                    h = float(highs[i]) if highs[i] is not None else None
                    l = float(lows[i]) if lows[i] is not None else None
                    c = float(closes[i]) if closes[i] is not None else None
                    v = float(volumes[i]) if volumes and volumes[i] is not None else 0.0
                except Exception:
                    continue
                if o is None or h is None or l is None or c is None:
                    continue
                klines.append({
                    "ts": int(ts) * 1000,
                    "open": o,
                    "high": h,
                    "low": l,
                    "close": c,
                    "volume": v,
                })
            if klines:
                if not min_points or min_points <= 0:
                    _update_cached_yahoo_klines(symbol, klines)
                    return klines
                if len(klines) >= min_points:
                    _update_cached_yahoo_klines(symbol, klines)
                    return klines
                if len(klines) > len(best):
                    best = klines
        except Exception:
            continue
    if best:
        _update_cached_yahoo_klines(symbol, best)
        return best
    return cached or []


def _limit_klines(klines: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
    if not isinstance(klines, list) or not klines:
        return []
    if limit <= 0:
        return klines
    if all(isinstance(item, dict) and isinstance(item.get("ts"), (int, float)) for item in klines):
        klines = sorted(klines, key=lambda item: item.get("ts", 0))
    return klines[-limit:]


def _format_metals_fundamentals_hint(payload: Dict[str, Any]) -> str:
    if not isinstance(payload, dict) or not payload:
        return ""
    parts = []
    supply_demand = payload.get("supply_demand")
    if isinstance(supply_demand, dict):
        headline = supply_demand.get("headline") or supply_demand.get("summary")
        if headline:
            parts.append(f"??: {headline}")
        balance = supply_demand.get("balance")
        if balance is not None:
            parts.append(f"????: {balance}")
    news = payload.get("news")
    if isinstance(news, dict):
        articles = news.get("articles") or []
        if isinstance(articles, list) and articles:
            titles = [a.get("title") for a in articles if isinstance(a, dict) and a.get("title")]
            if titles:
                parts.append(f"??: {titles[0]}")
    return "; ".join(parts)


def _build_metals_snapshot(symbol: str) -> Optional[Dict[str, Any]]:
    if not _is_metal_symbol(symbol):
        return None
    symbol_map = _get_metals_symbol_map()
    base = _safe_symbol(symbol).upper()
    yahoo_symbol = symbol_map.get(base, base)

    klines = []
    provider_hint = None
    try:
        from metals_data_sources import fetch_metals_klines
    except Exception:
        fetch_metals_klines = None
    if fetch_metals_klines:
        try:
            interval = (os.getenv("NOFX_METALS_AI_INTERVAL") or "1h").strip()
            df = fetch_metals_klines(base, interval=interval, limit=200, force_refresh=True)
        except Exception:
            df = None
        if df is not None and not df.empty:
            try:
                provider_hint = df.attrs.get("provider")
            except Exception:
                provider_hint = None
            try:
                df = df.sort_values("timestamp")
                for _, row in df.iterrows():
                    klines.append({
                        "ts": int(row["timestamp"].timestamp() * 1000),
                        "open": float(row["open"]),
                        "high": float(row["high"]),
                        "low": float(row["low"]),
                        "close": float(row["close"]),
                        "volume": float(row.get("volume", 0) or 0),
                    })
            except Exception:
                klines = []
    allow_yahoo = str(os.getenv("NOFX_METALS_ALLOW_YAHOO_FALLBACK", "0")).strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    if not klines and allow_yahoo:
        klines = _fetch_yahoo_klines(
            yahoo_symbol,
            attempts=[
                {"interval": "1h", "range": "1mo"},
                {"interval": "1h", "range": "3mo"},
                {"interval": "1h", "range": "6mo"},
                {"interval": "1d", "range": "6mo"},
                {"interval": "1d", "range": "1y"},
            ],
            min_points=200,
        )
        klines = _limit_klines(klines, 200)
    latest_quote = fetch_market_snapshot(base, force_refresh=True) or {}
    if not klines:
        quote = latest_quote
        price = float(quote.get("price", 0) or 0)
        if price > 0:
            change_pct = float(quote.get("price_change_percent", 0) or 0)
            prev = price / (1 + change_pct / 100) if change_pct else price
            high = float(quote.get("high_24h", price) or price)
            low = float(quote.get("low_24h", price) or price)
            volume = float(quote.get("volume_24h", 0) or 0)
            klines = [{
                "ts": int(time.time()) * 1000,
                "open": prev,
                "high": high,
                "low": low,
                "close": price,
                "volume": volume,
            }]
    if not klines:
        return None

    current_price = float(klines[-1]["close"])
    first_close = float(klines[0]["close"]) if klines else current_price
    price_change_pct = ((current_price - first_close) / first_close * 100) if first_close else 0.0

    fundamentals = fetch_metals_fundamentals(base)
    macro_snapshot = fetch_macro_snapshot()
    try:
        macro_data = load_macro_data()
    except Exception:
        macro_data = {}

    fundamentals_status = {
        "news": bool((fundamentals or {}).get("news")),
        "supply_demand": bool((fundamentals or {}).get("supply_demand")),
    }
    fundamentals_hint = _format_metals_fundamentals_hint(fundamentals or {})

    return {
        "symbol": base,
        "current_price": current_price,
        "klines": klines,
        "orderbook": {},
        "patterns": {},
        "fund_flow": {},
        "fund_flow_summary": {},
        "market": {
            "price_change_pct_window": price_change_pct,
            "window_points": len(klines),
        },
        "fundamentals": fundamentals,
        "fundamentals_status": fundamentals_status,
        "fundamentals_hint": fundamentals_hint,
        "macro_snapshot": macro_snapshot,
        "macro_data": macro_data,
        "source_data": {
            "yahoo_symbol": yahoo_symbol,
            "kline_provider": provider_hint or "yahoo",
            "kline_points": len(klines),
        },
    }


def _build_snapshot_from_quote(symbol: str, quote: Dict[str, Any], interval: str = "1h") -> Optional[Dict[str, Any]]:
    if not isinstance(quote, dict):
        return None
    try:
        price = float(quote.get("price", 0) or 0)
    except Exception:
        price = 0.0
    if price <= 0:
        return None
    change_pct = float(quote.get("price_change_percent", 0) or 0)
    prev = price / (1 + change_pct / 100) if change_pct else price
    high = float(quote.get("high_24h", price) or price)
    low = float(quote.get("low_24h", price) or price)
    volume = float(quote.get("volume_24h", 0) or 0)
    klines = [{
        "ts": int(time.time()) * 1000,
        "open": prev,
        "high": high,
        "low": low,
        "close": price,
        "volume": volume,
    }]
    fundamentals = fetch_fundamentals_snapshot(symbol, include_macro=True)
    macro_snapshot = fetch_macro_snapshot()
    try:
        macro_data = load_macro_data()
    except Exception:
        macro_data = {}
    fundamentals_status = {
        "tokenomics": bool((fundamentals or {}).get("tokenomics")),
        "onchain": bool((fundamentals or {}).get("onchain")),
        "project": bool((fundamentals or {}).get("project")),
        "sentiment": bool((fundamentals or {}).get("sentiment")),
    }
    fundamentals_hint = _format_fundamentals_hint(fundamentals or {})
    return {
        "symbol": _safe_symbol(symbol),
        "interval": interval,
        "current_price": price,
        "klines": klines,
        "price_min": low,
        "price_max": high,
        "orderbook": {},
        "patterns": {},
        "fund_flow": {},
        "fund_flow_summary": {},
        "market": quote,
        "fundamentals": fundamentals,
        "fundamentals_status": fundamentals_status,
        "fundamentals_hint": fundamentals_hint,
        "macro_snapshot": macro_snapshot,
        "macro_data": macro_data,
        "source_data": {
            "snapshot_only": True,
            "source": quote.get("source"),
        },
    }

def _build_snapshot(


    symbol: str,


    interval: str = "1h",


    limit: int = 200,


) -> Optional[Dict[str, Any]]:


    if _is_metal_symbol(symbol):
        return _build_metals_snapshot(symbol)

    df = None


    for attempt in range(3):


        df = get_klines(symbol, timeframe=interval, limit=limit)


        if df is not None and not df.empty:


            break


        time.sleep(1 + attempt)


    if df is None or getattr(df, 'empty', True):


        cached = _get_cached_klines(symbol)


        if cached is None or getattr(cached, 'empty', True):


            quote = fetch_market_snapshot(symbol) or {}
            fallback = _build_snapshot_from_quote(symbol, quote, interval=interval)
            if fallback:
                return fallback
            return None


        df = cached


    _update_cached_klines(symbol, df)





    current_price = float(df["close"].iloc[-1])


    orderbook = get_orderbook(symbol, limit=100)





    klines = []


    if "timestamp" in df.columns:


        ts_ms = (df["timestamp"].astype("int64") // 10**6).astype("int64")


        for i, row in df.reset_index(drop=True).iterrows():


            klines.append(


                {


                    "ts": int(ts_ms.iloc[i]),


                    "open": float(row["open"]),


                    "high": float(row["high"]),


                    "low": float(row["low"]),


                    "close": float(row["close"]),


                    "volume": float(row["volume"]),


                }


            )





    orderbook_summary = {}


    if isinstance(orderbook, dict):


        bids = orderbook.get("bids") or []


        asks = orderbook.get("asks") or []


        orderbook_summary = {


            "bids": [


                {"price": float(p), "amount": float(a), "notional": float(p) * float(a)}


                for p, a in bids[:20]


            ],


            "asks": [


                {"price": float(p), "amount": float(a), "notional": float(p) * float(a)}


                for p, a in asks[:20]


            ],


        }





    atr = calculate_atr(df)


    channel = detect_channel(df, atr=atr, windows=(60, 80, 120), r2_min=0.55)


    flag = detect_best_flag(df, atr, impulse_lookback=20, windows=(12, 18, 24))


    wedge = detect_best_wedge(df, atr=atr, windows=(60, 80, 120), r2_min=0.5)


    triangle = detect_best_triangle(df, atr=atr, windows=(60, 80, 120), r2_min=0.5)





    market_snapshot = fetch_market_snapshot(symbol) or {}
    fundamentals = fetch_fundamentals_snapshot(symbol, include_macro=True)
    macro_snapshot = fetch_macro_snapshot()
    try:
        macro_data = load_macro_data()
    except Exception:
        macro_data = {}
    fundamentals_status = {
        "tokenomics": bool((fundamentals or {}).get("tokenomics")),
        "onchain": bool((fundamentals or {}).get("onchain")),
        "project": bool((fundamentals or {}).get("project")),
        "sentiment": bool((fundamentals or {}).get("sentiment")),
    }
    fundamentals_hint = _format_fundamentals_hint(fundamentals or {})

    source_data = None
    if fetch_nofx_competition or fetch_nofx_top_traders or fetch_nofx_public_strategies:
        source_payload = {}
        try:
            if fetch_nofx_competition:
                data = fetch_nofx_competition(limit=_NOFX_PROMPT_LIMIT)
                if data is not None:
                    source_payload["competition"] = data
            if fetch_nofx_top_traders:
                data = fetch_nofx_top_traders(limit=_NOFX_PROMPT_LIMIT)
                if data is not None:
                    source_payload["top_traders"] = data
            if fetch_nofx_public_strategies:
                data = fetch_nofx_public_strategies(limit=_NOFX_STRATEGY_LIMIT)
                if data is not None:
                    source_payload["public_strategies"] = data
        except Exception as exc:
            logger.debug("External data fetch failed: %s", exc)
            source_payload = {}
        if source_payload:
            source_data = source_payload


    taker_flow = _fetch_taker_flow(symbol)


    fund_flow_summary = _summarize_fund_flow(_format_fund_flow(taker_flow or {}))
    lows = [k.get("low") for k in klines if isinstance(k.get("low"), (int, float))]


    highs = [k.get("high") for k in klines if isinstance(k.get("high"), (int, float))]


    price_min = min(lows) if lows else None


    price_max = max(highs) if highs else None





    overlay_candidates = _build_overlay_candidates(


        {


            "channel": channel,


            "flag": flag,


            "wedge": wedge,


            "triangle": triangle,


        },


        len(klines),


    )





    
    return {


        "symbol": _safe_symbol(symbol),


        "interval": interval,


        "current_price": current_price,


        "klines": klines,


        "price_min": price_min,


        "price_max": price_max,


        "orderbook": orderbook_summary,


        "patterns": {


            "channel": channel,


            "flag": flag,


            "wedge": wedge,


            "triangle": triangle,


        },


        "fund_flow": taker_flow or {},


        "fund_flow_summary": fund_flow_summary,


        "market": market_snapshot,
        "fundamentals": fundamentals,
        "fundamentals_status": fundamentals_status,
        "fundamentals_hint": fundamentals_hint,
        "macro_snapshot": macro_snapshot,
        "macro_data": macro_data,
        "source_data": source_data,


        "overlay_candidates": overlay_candidates,





    }








def _format_patterns(patterns: Dict[str, Any]) -> List[Dict[str, Any]]:


    out = []


    if not isinstance(patterns, dict):


        return out





    for key, value in patterns.items():


        if not value or not isinstance(value, dict):


            continue


        score = float(value.get("score", 0))


        threshold = PATTERN_SCORE_THRESHOLDS.get(key, 0.6)


        if score < threshold:


            continue


        out.append(


            {


                "name": key,


                "type": value.get("type"),


                "score": round(score, 2),


                "window": value.get("window"),


            }


        )


    return out








def _build_overlay_candidates(patterns: Dict[str, Any], klines_len: int) -> List[Dict[str, Any]]:


    candidates: List[Dict[str, Any]] = []


    if not isinstance(patterns, dict) or klines_len < 20:


        return candidates





    style_map = {


        "channel": "solid",


        "flag": "dashed",


        "wedge": "dashdot",


        "triangle": "dot",


    }





    for key in ("channel", "flag", "wedge", "triangle"):


        pattern = patterns.get(key)


        if not isinstance(pattern, dict):


            continue


        score = float(pattern.get("score", 0))


        threshold = PATTERN_SCORE_THRESHOLDS.get(key, 0.6)


        if score < threshold:


            continue


        window = int(pattern.get("window") or 0)


        if window < 20 or window > klines_len:


            continue


        upper = pattern.get("upper")


        lower = pattern.get("lower")


        if not (isinstance(upper, (list, tuple)) and isinstance(lower, (list, tuple))):


            continue


        if len(upper) < 2 or len(lower) < 2:


            continue


        slope_u, intercept_u = float(upper[0]), float(upper[1])


        slope_l, intercept_l = float(lower[0]), float(lower[1])


        x_start = klines_len - window


        x1 = x_start


        x2 = x_start + window - 1


        y1_u = slope_u * 0 + intercept_u


        y2_u = slope_u * (window - 1) + intercept_u


        y1_l = slope_l * 0 + intercept_l


        y2_l = slope_l * (window - 1) + intercept_l


        style = style_map.get(key, "solid")


        candidates.append(


            {


                "id": f"{key}_top",


                "x1": x1,


                "y1": y1_u,


                "x2": x2,


                "y2": y2_u,


                "style": style,


                "label": f"{key}_top",


                "type": key,


            }


        )


        candidates.append(


            {


                "id": f"{key}_bottom",


                "x1": x1,


                "y1": y1_l,


                "x2": x2,


                "y2": y2_l,


                "style": style,


                "label": f"{key}_bottom",


                "type": key,


            }


        )





    return candidates








def _format_fund_flow(fund_flow: Dict[str, Any]) -> Dict[str, Any]:


    if not isinstance(fund_flow, dict):


        return {}


    result = {}


    for period in ("15m", "1h", "4h", "1d"):


        data = fund_flow.get(period)


        if not isinstance(data, dict):


            continue


        result[period] = {


            "net": data.get("net"),


            "ratio": data.get("ratio"),


        }


    return result








def _summarize_fund_flow(fund_flow: Dict[str, Any]) -> Dict[str, Any]:


    if not isinstance(fund_flow, dict) or not fund_flow:


        return {"max_positive": None, "max_positive_period": None, "all_negative": None}


    nets = []


    max_positive = None


    max_positive_period = None


    for period, data in fund_flow.items():


        if not isinstance(data, dict):


            continue


        value = data.get("net")


        try:


            net = float(value)


        except Exception:


            continue


        nets.append(net)


        if net > 0 and (max_positive is None or net > max_positive):


            max_positive = net


            max_positive_period = period


    all_negative = bool(nets) and all(net < 0 for net in nets)


    return {


        "max_positive": max_positive,


        "max_positive_period": max_positive_period,


        "all_negative": all_negative,


    }





















def _format_fundamentals_hint(fundamentals: Dict[str, Any]) -> str:
    if not isinstance(fundamentals, dict) or not fundamentals:
        return ""

    def _fmt_num(value: Any) -> str:
        if value is None:
            return "N/A"
        try:
            num = float(value)
        except (TypeError, ValueError):
            return str(value)
        if abs(num) >= 1e12:
            return f"{num / 1e12:.2f}T"
        if abs(num) >= 1e9:
            return f"{num / 1e9:.2f}B"
        if abs(num) >= 1e6:
            return f"{num / 1e6:.2f}M"
        if abs(num) >= 1e3:
            return f"{num / 1e3:.2f}K"
        return f"{num:.4f}" if abs(num) < 1 else f"{num:.2f}"

    parts: List[str] = []
    tokenomics = fundamentals.get("tokenomics") or {}
    if isinstance(tokenomics, dict) and tokenomics:
        circ = tokenomics.get("circulating_supply")
        total = tokenomics.get("total_supply")
        max_supply = tokenomics.get("max_supply")
        fdv = tokenomics.get("fdv")
        parts.append(
            "tokenomics: circ "
            f"{_fmt_num(circ)}, total {_fmt_num(total)}, max {_fmt_num(max_supply)}, fdv {_fmt_num(fdv)}"
        )

    onchain = fundamentals.get("onchain") or {}
    if isinstance(onchain, dict) and onchain:
        eth_stats = onchain.get("eth_stats") or {}
        daily_txn = onchain.get("daily_txn") or {}
        token_supply = onchain.get("token_supply") or {}
        defillama = onchain.get("defillama") or {}
        if eth_stats:
            parts.append(
                "onchain: eth_supply "
                f"{_fmt_num(eth_stats.get('eth_supply'))}, eth_price {_fmt_num(eth_stats.get('eth_price_usd'))}"
            )
        if daily_txn:
            parts.append(f"onchain: daily_tx {_fmt_num(daily_txn.get('tx_count'))}")
        if token_supply:
            parts.append(f"onchain: token_supply {_fmt_num(token_supply.get('supply'))}")
        if defillama:
            parts.append(
                "onchain: tvl "
                f"{_fmt_num(defillama.get('tvl'))}, 1d {_fmt_num(defillama.get('tvl_change_1d'))},"
                f" 7d {_fmt_num(defillama.get('tvl_change_7d'))}"
            )

    project = fundamentals.get("project") or {}
    if isinstance(project, dict) and project:
        parts.append(
            "project: commits_4w "
            f"{project.get('dev_commits_4w')}, stars {project.get('github_stars')},"
            f" forks {project.get('github_forks')}"
        )

    sentiment = fundamentals.get("sentiment") or {}
    if isinstance(sentiment, dict) and sentiment:
        parts.append(f"sentiment: {sentiment.get('classification')}({sentiment.get('value')})")

    return "; ".join([p for p in parts if p])




def _build_metals_prompt(
    symbol: str,
    snapshot: Dict[str, Any],
    signal_payload: Optional[Dict[str, Any]] = None,
    recent_signals: Optional[Dict[str, Any]] = None,
    analysis_time_bj: Optional[str] = None,
    language: str = "zh",
) -> str:
    signal_info = {}
    if isinstance(signal_payload, dict):
        item = signal_payload.get("item") or {}
        content = signal_payload.get("parsed_content") or {}
        anomaly = signal_payload.get("anomaly") or {}
        signal_info = {
            "title": item.get("title"),
            "type": item.get("type") or item.get("messageType"),
            "source": content.get("source"),
            "tradeType": content.get("tradeType"),
            "fundsMovementType": content.get("fundsMovementType"),
            "anomaly_type": anomaly.get("type"),
            "anomaly_direction": anomaly.get("direction"),
            "anomaly_severity": anomaly.get("severity"),
            "anomaly_description": anomaly.get("description"),
            "anomaly_triggers": anomaly.get("triggers", []),
            "anomaly_data": anomaly.get("data", {}),
        }

    payload = {
        "symbol": symbol,
        "price": snapshot.get("current_price"),
        "klines": snapshot.get("klines", []),
        "market": snapshot.get("market", {}),
        "fundamentals": snapshot.get("fundamentals", {}),
        "fundamentals_status": snapshot.get("fundamentals_status", {}),
        "fundamentals_hint": snapshot.get("fundamentals_hint", ""),
        "macro_snapshot": snapshot.get("macro_snapshot", {}),
        "macro_data": snapshot.get("macro_data", {}),
        "source_data": snapshot.get("source_data"),
        "signal": signal_info,
    }

    if analysis_time_bj:
        payload["analysis_time_bj"] = analysis_time_bj
    if recent_signals is not None:
        payload["recent_signals_24h"] = recent_signals

    payload_json = json.dumps(payload, ensure_ascii=False, default=str)

    lines = [
        "You are a precious-metals analyst focused on gold/silver macro and event drivers.",
        "This is a single-symbol signal brief. Return strict JSON only.",
        'JSON schema: {"analysis":"...","trend_status":"uptrend/downtrend/sideways","supports":[...],"resistances":[...],"stop_loss":null,"take_profit":null,"rr":null,"risk_level":"low/medium/high","entry_decision":"yes/no","direction":"long/short/none","leverage_suggestion":"1-5x/5-10x/10-20x/no_trade","overlays":[]}',
        "- Must use macro_snapshot/macro_data/macro_fred/macro_gdelt when present (e.g., NFP/CPI/Fed policy/news).",
        "Requirements:",
        "- Use only raw price action (structure/range/high-low) + supply/demand + geopolitics/major news.",
        "- Do NOT use or mention RSI/MACD/MAs/VWAP/ATR or any indicators.",
        "- Must reference macro_snapshot/macro_data/macro_fred/macro_gdelt when present (e.g., NFP/CPI/Fed policy/news).",
        "- If supply/demand or news is missing, explicitly state insufficient data.",
        "Rules:",
        "0. Must cover: trend, price structure, supply/demand, geopolitics/news, macro backdrop, risks.",
        "1. Support/resistance must come from price structure/ranges only (1-5 levels).",
        "2. Do not mention data source names; only say 'based on signals/data'.",
        "3. entry_decision=yes requires stop_loss/take_profit/rr and rr >= 2.0.",
        "4. entry_decision=no => direction=none and stop_loss/take_profit/rr=null.",
        "5. 操作建议必须基于严格分析，只在趋势与结构确认后给出右侧交易结论。",
        "6. 禁止出现“信心/置信度/胜率/概率/阈值/不足xx%”等措辞，不要输出信心类百分比；方向强弱可用百分比但不要称为信心。",
        "7. analysis must include an operation advice line (e.g., 🎯操作建议: ...). If entry_decision=no, advise wait/observe.",
        "analysis field (120-220 chars): 5-7 lines, each line starts with an emoji.",
        "analysis must be in Chinese.",
        "Input data:",
        payload_json,
    ]
    return "\n".join(lines)

def _build_prompt(
    symbol: str,
    snapshot: Dict[str, Any],
    signal_payload: Optional[Dict[str, Any]] = None,
    recent_signals: Optional[Dict[str, Any]] = None,
    analysis_time_bj: Optional[str] = None,
    language: str = "zh",
) -> str:
    patterns = _format_patterns(snapshot.get("patterns", {}))
    fund_flow = _format_fund_flow(snapshot.get("fund_flow", {}))

    signal_info = {}
    if isinstance(signal_payload, dict):
        item = signal_payload.get("item") or {}
        content = signal_payload.get("parsed_content") or {}
        anomaly = signal_payload.get("anomaly") or {}
        signal_info = {
            "title": item.get("title"),
            "type": item.get("type") or item.get("messageType"),
            "source": content.get("source"),
            "tradeType": content.get("tradeType"),
            "fundsMovementType": content.get("fundsMovementType"),
            "anomaly_type": anomaly.get("type"),
            "anomaly_direction": anomaly.get("direction"),
            "anomaly_severity": anomaly.get("severity"),
            "anomaly_description": anomaly.get("description"),
            "anomaly_triggers": anomaly.get("triggers", []),
            "anomaly_is_independent": anomaly.get("is_independent", False),
            "anomaly_data": anomaly.get("data", {}),
        }

    payload = {
        "symbol": symbol,
        "price": snapshot.get("current_price"),
        "klines": snapshot.get("klines", []),
        "orderbook": snapshot.get("orderbook", {}),
        "patterns": patterns,
        "fund_flow": fund_flow,
        "fund_flow_summary": snapshot.get("fund_flow_summary", {}),
        "market": snapshot.get("market", {}),
        "fundamentals": snapshot.get("fundamentals", {}),
        "fundamentals_status": snapshot.get("fundamentals_status", {}),
        "fundamentals_hint": snapshot.get("fundamentals_hint", ""),
        "macro_snapshot": snapshot.get("macro_snapshot", {}),
        "macro_data": snapshot.get("macro_data", {}),
        "source_data": snapshot.get("source_data"),
        "signal": signal_info,
    }

    if analysis_time_bj:
        payload["analysis_time_bj"] = analysis_time_bj
    if recent_signals is not None:
        payload["recent_signals_24h"] = recent_signals

    payload_json = json.dumps(payload, ensure_ascii=False, default=str)

    # 专业量化分析提示词 - 技术指标驱动
    lines = [
        "你是专业的加密合约分析师，基于输入数据输出结论。",
        "这是单币信号简评，不是宏观市场分析。",
        "仅返回严格 JSON，不要附加任何文本。",
        'JSON schema: {"analysis":"...","trend_status":"uptrend/downtrend/sideways","supports":[...],"resistances":[...],"stop_loss":null,"take_profit":null,"rr":null,"risk_level":"low/medium/high","entry_decision":"yes/no","direction":"long/short/none","leverage_suggestion":"1-5x/5-10x/10-20x/no_trade","overlays":[]}',
        "数据使用说明：",
        "- 需要综合所有输入字段：K线、盘口、形态、资金流、市场概览、基本面、宏观快照/宏观日历、众包/策略、信号上下文与近24小时信号。",
        "- 与技术面、资金流、盘口与宏观交叉验证，并指出冲突或缺失。",
        "- 若有指标数据（EMA/RSI/MACD/VWAP/ATR等），必须在分析中明确提及并给出结论。",
        "规则：",
        "0. 必须覆盖：结构/趋势、动能、流动性/资金流、盘口、宏观/市场状态、风险与冲突；缺失数据需说明。",
        "1. 支撑/阻力各 1-5 个，多源证据>=2 才可确认。",
        "2. 权重参考：盘口流动性 30%，资金流 25%，结构/形态 20%，指标 15%，众包+宏观 10%。",
        "3. 不要提及任何数据源名称，只能说“基于信号”或“基于数据”。",
        '4. 每个价位对象格式：{"price": number, "strength": 0-100, "reason": "来源+理由"}。',
        "5. 支撑 < 价格 < 阻力；唯一且升序。",
        "6. entry_decision=yes：必须给出 stop_loss/take_profit/rr，且 rr >= 2.0。",
        "7. entry_decision=no：direction=none，stop_loss/take_profit/rr=null。",
        "8. direction=long：stop_loss < price < take_profit。",
        "9. direction=short：stop_loss > price > take_profit。",
        "10. 操作建议必须基于严格分析，只在趋势与结构确认后给出右侧交易结论。",
        "11. 禁止出现“信心/置信度/胜率/概率/阈值/不足xx%”等措辞，不要输出信心类百分比；方向强弱可用百分比但不要称为信心。",
        "analysis 字段(120-280字)：必须结构化，使用 5-7 行，每行以 emoji 开头。",
        "格式示例：",
        "📌方向：偏多 70%",
        "📈结构：...",
        "📊指标：EMA/RSI/MACD/VWAP/ATR 结论 ...",
        "💧流动性/资金：...",
        "🧩宏观/市场：...",
        "⚠️风险：...",
        "🎯计划：...",
        "说明：不要出现数据源名称，只能写“基于信号/基于数据”。",
        "输入数据：",
        payload_json,
    ]
    return "\n".join(lines)


def _build_key_levels_prompt(symbol: str, snapshot: Dict[str, Any], language: str = "zh") -> str:
    payload = {
        "symbol": symbol,
        "price": snapshot.get("current_price"),
        "orderbook": snapshot.get("orderbook", {}),
        "fund_flow": _format_fund_flow(snapshot.get("fund_flow", {})),
        "fund_flow_summary": snapshot.get("fund_flow_summary", {}),
        "patterns": _format_patterns(snapshot.get("patterns", {})),
        "market": snapshot.get("market", {}),
        "macro_snapshot": snapshot.get("macro_snapshot", {}),
        "source_data": snapshot.get("source_data"),
    }
    payload_json = json.dumps(payload, ensure_ascii=False, default=str)

    lines = [
        "仅返回严格 JSON，不要附加任何文本。",
        "目标：基于多源证据选出 1-5 个支撑与 1-5 个阻力。",
        "权重参考：盘口/流动性 35%，资金流 25%，结构/形态 20%，市场/宏观 10%，众包数据 10%。",
        "需要综合波动率、成交量节点与盘口墙，指出冲突或数据不足。",
        "不要提及任何数据源名称，只能说“基于信号”或“基于数据”。",
        "reason 字段必须使用中文。",
        "优先使用 >=2 源确认的价位，弱化单一来源的离群点。",
        "若信号冲突，优先考虑最强的流动性墙与成交量节点。",
        "保持 supports < price < resistances；唯一、升序、靠近关键价位。",
        "输出 JSON 格式：",
        '{"supports":[{"price":0,"strength":0-100,"sources":["orderbook","fund_flow"],"reason":"..."}],"resistances":[{"price":0,"strength":0-100,"sources":["orderbook","patterns"],"reason":"..."}]}',
        payload_json,
    ]
    return "\n".join(lines)


def _strip_thoughts(text: str) -> str:


    """Return only the final answer when the model includes thought markers."""


    if not text:


        return text


    cleaned = text.strip()


    markers = [
        "</think>",
        "Final Answer:",
        "Final:",
        "Answer:",
    ]


    for marker in markers:


        if marker in cleaned:


            cleaned = cleaned.split(marker, 1)[-1].strip()


    if "<think>" in cleaned:


        cleaned = cleaned.split("<think>", 1)[0].strip()


    return cleaned





def _parse_ai_response(raw: str) -> Dict[str, Any]:


    if not raw:


        return {


            "analysis": "",


            "market_phase": "idle",


            "supports": [],


            "resistances": [],


            "risk_level": "medium",


            "entry_decision": "no",


            "direction": "none",


        }


    cleaned = raw.strip()


    if cleaned.startswith("```"):


        first_newline = cleaned.find("\n")


        if first_newline != -1:


            cleaned = cleaned[first_newline + 1 :]


        if cleaned.endswith("```"):


            cleaned = cleaned[:-3]


        cleaned = cleaned.strip()


    elif "```" in cleaned:


        try:


            import re





            match = re.search(r"```(?:json)?\\s*(\\{.*?\\})\\s*```", cleaned, flags=re.S)


            if match:


                cleaned = match.group(1).strip()


        except Exception:


            pass


    data = None


    try:


        data = json.loads(cleaned)


    except Exception:


        start = cleaned.find("{")


        end = cleaned.rfind("}")


        if start != -1 and end != -1 and end > start:


            try:


                data = json.loads(cleaned[start:end + 1])


            except Exception:


                data = None


    if not isinstance(data, dict):


        return {


            "analysis": cleaned,


            "supports": [],


            "resistances": [],


            "risk_level": "medium",


            "entry_decision": "no",


            "direction": "none",


        }


    return data








def _extract_confidence_from_text(text: str) -> Optional[float]:
    if not text:
        return None
    try:
        import re
    except Exception:
        return None

    match = re.search(r"(\\d{1,3}(?:\\.\\d+)?)\\s*%", text)
    if match:
        try:
            value = float(match.group(1))
            if 0 < value <= 100:
                return value
        except Exception:
            pass

    match = re.search(
        r"(?:confidence|bias|probability|prob|win rate|winrate|胜率|置信度|概率)[^0-9]{0,6}(\\d{1,3}(?:\\.\\d+)?)",
        text,
        flags=re.I,
    )
    if match:
        try:
            value = float(match.group(1))
            if 0 < value <= 1:
                return value * 100.0
            if 0 < value <= 100:
                return value
        except Exception:
            pass
    return None


def _normalize_confidence(value: Any, analysis_text: str) -> Optional[float]:
    if isinstance(value, (int, float)):
        val = float(value)
        if 0 < val <= 1:
            return val * 100.0
        if 0 < val <= 100:
            return val
        return None
    if isinstance(value, str):
        stripped = value.strip().lower()
        if stripped.endswith("%"):
            try:
                return float(stripped[:-1])
            except Exception:
                return None
        try:
            val = float(stripped)
        except Exception:
            val = None
        if val is not None:
            if 0 < val <= 1:
                return val * 100.0
            if 0 < val <= 100:
                return val
            return None
    return _extract_confidence_from_text(analysis_text)


def _normalize_entry_decision(value: Any) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (int, float)):
        return "yes" if value > 0 else "no"
    if isinstance(value, str):
        val = value.strip().lower()
        yes_values = {
            "yes",
            "y",
            "true",
            "1",
            "entry",
            "enter",
            "open",
            "long",
            "short",
            "bullish",
            "bearish",
            "?",
            "??",
            "?",
            "??",
            "??",
            "??",
            "??",
            "??",
            "?",
            "?",
            "??",
            "??",
            "??",
            "??",
        }
        no_values = {
            "no",
            "n",
            "false",
            "0",
            "skip",
            "hold",
            "wait",
            "?",
            "?",
            "??",
            "??",
            "??",
            "??",
            "??",
            "??",
            "?",
        }
        if val in yes_values:
            return "yes"
        if val in no_values:
            return "no"
    return "no"


def _normalize_risk_level(value: Any) -> str:
    if isinstance(value, str):
        val = value.strip().lower()
        mapping = {
            "low": "low",
            "medium": "medium",
            "high": "high",
            "l": "low",
            "m": "medium",
            "h": "high",
            "?": "low",
            "??": "low",
            "??": "low",
            "?": "medium",
            "??": "medium",
            "??": "medium",
            "??": "medium",
            "?": "high",
            "??": "high",
            "??": "high",
        }
        if val in mapping:
            return mapping[val]
    return "medium"


def _normalize_direction(value: Any) -> str:
    if isinstance(value, str):
        val = value.strip().lower()
        if val in {"long", "bull", "bullish", "up", "buy", "?", "??", "??", "??", "??", "??"}:
            return "long"
        if val in {"short", "bear", "bearish", "down", "sell", "?", "??", "??", "??", "??", "??"}:
            return "short"
        if val in {"none", "neutral", "sideways", "flat", "?", "??", "??", "??", "??", "??"}:
            return "none"
    return "none"


def _normalize_trend_status(value: Any) -> str:
    """规范化趋势状态"""
    if isinstance(value, str):
        val = value.strip().lower()
        if val in {"uptrend", "up", "bullish", "上涨", "多头", "上升"}:
            return "uptrend"
        if val in {"downtrend", "down", "bearish", "下跌", "空头", "下降"}:
            return "downtrend"
        if val in {"sideways", "range", "neutral", "震荡", "横盘", "整理"}:
            return "sideways"
    return "sideways"


def _normalize_leverage_suggestion(value: Any) -> str:
    """规范化杠杆建议"""
    if isinstance(value, str):
        val = value.strip().lower()
        if "no" in val or "不" in val:
            return "no_trade"
        if "10" in val or "20" in val:
            return "10-20x"
        if "5" in val and "10" in val:
            return "5-10x"
        if "1" in val or "5" in val or "低" in val:
            return "1-5x"
    return "no_trade"


def _trim_analysis_length(text: str, target: int = 150, max_chars: int = 200) -> str:
    if not text:
        return text
    return text.strip()

def _strip_confidence_threshold_notes(text: str) -> str:
    import re
    if not text:
        return text
    confidence_terms = re.compile(r"(信心指数|置信度|信心|confidence|胜率|概率)", flags=re.IGNORECASE)
    soft_block_terms = re.compile(r"(未达|不达|不足|偏低|过低|低于|<|未满足|不满足|阈值|指标)", flags=re.IGNORECASE)
    cleaned = []
    for line in text.splitlines():
        raw = line.strip()
        if not raw:
            continue
        original = raw
        if confidence_terms.search(raw):
            if soft_block_terms.search(raw):
                raw = ""
            else:
                raw = ""
        raw = re.sub(
            r"(\u7f6e\u4fe1\u5ea6|\u4fe1\u5fc3|\u4fe1\u5fc3\u6307\u6570|confidence)[^?.!?\n]*\u9608\u503c[^?.!?\n]*",
            "",
            raw,
            flags=re.IGNORECASE,
        ).strip()
        raw = re.sub(r"\u4f4e\u4e8e\u9608\u503c[^?.!?\n]*", "", raw).strip()
        if not raw and "低于阈值" in original:
            raw = "观望为主"
        if raw:
            cleaned.append(raw)
    if not cleaned:
        return "观望为主"
    return "\n".join(cleaned)
def _sanitize_fundamentals_note(analysis: str, status: Optional[Dict[str, Any]]) -> str:
    if not analysis or not isinstance(status, dict):
        return analysis
    return analysis



def _infer_direction_from_levels(price: float, stop_loss: Optional[float], take_profit: Optional[float]) -> str:


    if stop_loss is None or take_profit is None:


        return "none"


    if stop_loss < price < take_profit:


        return "long"


    if stop_loss > price > take_profit:


        return "short"


    return "none"








def _normalize_levels(values: Any, price: float, is_support: bool) -> List[float]:


    if not isinstance(values, list):


        return []


    out = []


    for item in values:


        val = None


        if isinstance(item, (int, float)):


            val = float(item)


        elif isinstance(item, dict):


            if isinstance(item.get("price"), (int, float)):


                val = float(item["price"])


        if val is None:


            continue


        if is_support and val >= price:


            continue


        if not is_support and val <= price:


            continue


        out.append(val)


    return out[:3]








def _normalize_price_value(value: Any) -> Optional[float]:


    if isinstance(value, (int, float)):


        return float(value)


    if isinstance(value, dict):


        val = value.get("price")


        if isinstance(val, (int, float)):


            return float(val)


    return None








def _extract_trade_levels(


    parsed: Dict[str, Any],


    price: float,


    supports: List[float],


    resistances: List[float],


    entry_decision: str,


    direction: str,


):


    if entry_decision != "yes" or direction == "none":


        return None, None, None





    stop_loss = _normalize_price_value(parsed.get("stop_loss"))


    take_profit = _normalize_price_value(parsed.get("take_profit"))





    if direction == "long":


        if stop_loss is None and supports:


            stop_loss = min(supports)


        if take_profit is None and resistances:


            take_profit = max(resistances)


        if stop_loss is not None and stop_loss >= price:


            stop_loss = None


        if take_profit is not None and take_profit <= price:


            take_profit = None


    elif direction == "short":


        if stop_loss is None and resistances:


            stop_loss = max(resistances)


        if take_profit is None and supports:


            take_profit = min(supports)


        if stop_loss is not None and stop_loss <= price:


            stop_loss = None


        if take_profit is not None and take_profit >= price:


            take_profit = None


    else:


        return None, None, None





    rr_val = parsed.get("rr")


    rr = None


    if isinstance(rr_val, (int, float)) and rr_val > 0:


        rr = float(rr_val)


    elif stop_loss is not None and take_profit is not None:


        if direction == "long" and price > stop_loss:


            rr = (take_profit - price) / (price - stop_loss)


        elif direction == "short" and stop_loss > price:


            rr = (price - take_profit) / (stop_loss - price)


    if stop_loss is None or take_profit is None:


        rr = None


    return stop_loss, take_profit, rr








def _is_fomo_intensify(signal_payload: Optional[Dict[str, Any]]) -> bool:


    if not isinstance(signal_payload, dict):


        return False


    item = signal_payload.get("item") or {}


    content = signal_payload.get("parsed_content") or {}


    text = " ".join(


        str(val)


        for val in [


            item.get("title"),


            content.get("source"),


            content.get("titleSimplified"),


            content.get("title"),


        ]


        if val


    ).lower()


    tokens = ["\u52a0\u5267", "\u5f3a\u5316", "\u7206\u53d1", "intensify", "intensified", "spike", "surge"]


    if "fomo" in text and any(token in text for token in tokens):


        return True


    if item.get("type") in (112,):


        return True


    if content.get("fundsMovementType") == 7:


        return True


    return text.count("fomo") >= 2








def _line_touches(series: List[float], line: Dict[str, Any], tolerance: float = 0.015) -> int:


    x1 = int(round(line["x1"]))


    x2 = int(round(line["x2"]))


    if x2 == x1:


        return 0


    if x1 > x2:


        x1, x2 = x2, x1


    x1 = max(0, x1)


    x2 = min(len(series) - 1, x2)


    if x2 <= x1:


        return 0


    slope = (line["y2"] - line["y1"]) / (line["x2"] - line["x1"])


    intercept = line["y1"] - slope * line["x1"]


    touches = 0


    for idx in range(x1, x2 + 1):


        y_line = slope * idx + intercept


        if y_line == 0:


            continue


        if abs(series[idx] - y_line) / y_line <= tolerance:


            touches += 1


    return touches








def _normalize_overlays(


    values: Any,


    max_x: int,


    price_min: Optional[float],


    price_max: Optional[float],


    lows: List[float],


    highs: List[float],


    candidates: List[Dict[str, Any]],


) -> List[Dict[str, Any]]:


    if not isinstance(values, list):


        return []


    out = []


    candidate_list = candidates if isinstance(candidates, list) else []


    price_range = None


    if isinstance(price_min, (int, float)) and isinstance(price_max, (int, float)):


        price_range = max(1e-9, price_max - price_min)


    for item in values:


        if not isinstance(item, dict):


            continue


        x1 = item.get("x1")


        y1 = item.get("y1")


        x2 = item.get("x2")


        y2 = item.get("y2")


        if not all(isinstance(v, (int, float)) for v in (x1, y1, x2, y2)):


            continue


        x1 = max(0, min(float(x1), max_x))


        x2 = max(0, min(float(x2), max_x))


        if abs(x2 - x1) < 20:


            continue


        if isinstance(price_min, (int, float)) and isinstance(price_max, (int, float)):


            lower = price_min * 0.95


            upper = price_max * 1.05


            if not (lower <= float(y1) <= upper and lower <= float(y2) <= upper):


                continue


        overlay = {


            "x1": x1,


            "y1": float(y1),


            "x2": x2,


            "y2": float(y2),


            "style": item.get("style", "solid"),


            "label": item.get("label", ""),


            "type": item.get("type", ""),


            "color": item.get("color", ""),


        }





        if candidate_list:


            best = None


            best_dist = None


            for cand in candidate_list:


                if not isinstance(cand, dict):


                    continue


                try:


                    dx = abs(float(cand.get("x1", 0)) - float(overlay["x1"])) + abs(float(cand.get("x2", 0)) - float(overlay["x2"]))


                    dy = abs(float(cand.get("y1", 0)) - float(overlay["y1"])) + abs(float(cand.get("y2", 0)) - float(overlay["y2"]))


                except Exception:


                    continue


                dist = dx + (dy / (price_range or 1.0))


                if best_dist is None or dist < best_dist:


                    best_dist = dist


                    best = cand


            if not best:


                continue


            x_tol = 2.5


            y_tol = (price_range or 1.0) * 0.03


            if (


                abs(float(best.get("x1", 0)) - float(overlay["x1"])) > x_tol


                or abs(float(best.get("x2", 0)) - float(overlay["x2"])) > x_tol


                or abs(float(best.get("y1", 0)) - float(overlay["y1"])) > y_tol


                or abs(float(best.get("y2", 0)) - float(overlay["y2"])) > y_tol


            ):


                continue


            overlay.update(


                {


                    "x1": float(best.get("x1", overlay["x1"])),


                    "y1": float(best.get("y1", overlay["y1"])),


                    "x2": float(best.get("x2", overlay["x2"])),


                    "y2": float(best.get("y2", overlay["y2"])),


                    "style": best.get("style", overlay["style"]),


                    "label": best.get("label", overlay["label"]),


                    "type": best.get("type", overlay["type"]),


                }


            )


        out.append(overlay)


    if not out:


        return []





    # Validate channel parallelism if both rails exist.


    channel_lines = [o for o in out if "channel" in str(o.get("label", "")).lower() or o.get("type") == "channel"]


    if len(channel_lines) >= 2:


        top = None


        bottom = None


        for item in channel_lines:


            label = str(item.get("label", "")).lower()


            if "top" in label and top is None:


                top = item


            elif "bottom" in label and bottom is None:


                bottom = item


        if top and bottom:


            dx = float(top["x2"]) - float(top["x1"])


            dx2 = float(bottom["x2"]) - float(bottom["x1"])


            if dx != 0 and dx2 != 0:


                slope_top = (float(top["y2"]) - float(top["y1"])) / dx


                slope_bottom = (float(bottom["y2"]) - float(bottom["y1"])) / dx2


                diff = abs(slope_top - slope_bottom)


                tol = max(0.05, abs(slope_top) * 0.2)


                if diff > tol:


                    out = [o for o in out if o not in (top, bottom)]


            # Require pivot touches for channel rails.


            if highs and lows and top and bottom:


                top_hits = _line_touches(highs, top, tolerance=0.02)


                bottom_hits = _line_touches(lows, bottom, tolerance=0.02)


                if top_hits < 2 or bottom_hits < 2:


                    out = [o for o in out if o not in (top, bottom)]





    return out[:6]








def _get_ai_proxies() -> Optional[Dict[str, str]]:


    proxy_url = (


        os.getenv("NOFX_AI_PROXY")


        or os.getenv("NOFX_PROXY")


        or os.getenv("HTTPS_PROXY")


        or os.getenv("HTTP_PROXY")


        or ""


    ).strip()


    if not proxy_url:


        try:


            from config import HTTP_PROXY as CONFIG_HTTP_PROXY


        except Exception:


            CONFIG_HTTP_PROXY = ""


        if isinstance(CONFIG_HTTP_PROXY, str) and CONFIG_HTTP_PROXY.strip():


            proxy_url = CONFIG_HTTP_PROXY.strip()


    if not proxy_url:


        try:


            from config import AI_SUMMARY_PROXY as CONFIG_AI_SUMMARY_PROXY


        except Exception:


            CONFIG_AI_SUMMARY_PROXY = ""


        if isinstance(CONFIG_AI_SUMMARY_PROXY, str) and CONFIG_AI_SUMMARY_PROXY.strip():


            proxy_url = CONFIG_AI_SUMMARY_PROXY.strip()


    if not proxy_url:


        return None


    return {"http": proxy_url, "https": proxy_url}








def _call_ai_api(prompt: str, config: Dict[str, Any], language: str = "zh") -> Optional[str]:


    api_key = (config.get("api_key") or "").strip()


    api_url = (config.get("api_url") or "").strip()


    model = (config.get("model") or "").strip()


    max_retries = int(os.getenv("NOFX_AI_API_RETRY", "1") or 1)


    timeout_sec = int(os.getenv("NOFX_AI_API_TIMEOUT", "90") or 90)


    connect_timeout = float(os.getenv("NOFX_AI_CONNECT_TIMEOUT", "15") or 15)


    max_tokens = int(os.getenv("NOFX_AI_MAX_TOKENS", "8000") or 8000)





    if not api_key or not api_url or not model:


        return None





    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}


    system_prompt = "你是专业的量化分析师，要求多维度全面分析，仅返回严格 JSON，analysis 字段必须使用中文。"





    protocol, resolved_url = resolve_protocol_and_url(api_url, config.get("api_protocol"))
    stream = should_force_responses_stream(resolved_url, protocol)
    payload = build_payload(
        protocol,
        resolved_url,
        model,
        system_prompt,
        prompt,
        max_tokens,
        0.4,
        stream,
    )





    proxies = _get_ai_proxies()


    use_env_proxy = os.getenv("NOFX_AI_TRUST_ENV", "0").lower() in ("1", "true", "yes", "on")


    for attempt in range(max_retries + 1):


        try:


            session = requests.Session()


            session.trust_env = bool(use_env_proxy and not proxies)


            if protocol == AI_PROTOCOL_RESPONSES:
                headers["Accept"] = "text/event-stream" if stream else "application/json"
            resp = session.post(
                resolved_url,
                headers=headers,
                json=payload,
                timeout=(connect_timeout, timeout_sec),
                proxies=proxies,
            )
            if resp.status_code != 200:
                if resp.status_code == 429:
                    raise RuntimeError(f"AI_429: {resp.text[:200]}")
                if protocol == AI_PROTOCOL_RESPONSES and resp.status_code == 400:
                    override_key = resolve_responses_token_key_override(resp.text)
                    if override_key is not None:
                        payload = override_responses_token_key(payload, override_key, max_tokens)
                        resp = session.post(
                            resolved_url,
                            headers=headers,
                            json=payload,
                            timeout=(connect_timeout, timeout_sec),
                            proxies=proxies,
                        )
                if resp.status_code != 200:
                    logger.warning("AI API call failed: %s - %s", resp.status_code, resp.text[:200])
                    if attempt < max_retries and resp.status_code >= 500:
                        time.sleep(2 + attempt * 2)
                        continue
                    return None

            if protocol == AI_PROTOCOL_RESPONSES:
                try:
                    content = parse_responses_body(resp.text)
                except Exception as exc:
                    logger.warning("AI API response parse error: %s", exc)
                    content = ""
            else:
                data = resp.json()
                content = parse_compatible_content(data)

            if content:
                return _strip_thoughts(content)



            if attempt < max_retries:


                time.sleep(2 + attempt * 2)


                continue


            return None


        except Exception as exc:


            logger.warning("AI API call error: %s", exc)


            if attempt < max_retries:


                time.sleep(2 + attempt * 2)


                continue


            return None








def generate_ai_key_levels(symbol: str) -> Optional[Dict[str, Any]]:


    """Generate AI key levels and populate the in-memory cache."""


    logger.info("[AI Key Levels] Start for %s", symbol)





    try:


        from ai_key_levels_config import get_ai_levels_config


    except Exception:


        from signal_monitor.ai_key_levels_config import get_ai_levels_config





    config = get_ai_levels_config()


    logger.info(


        "[AI Key Levels] Config: enabled=%s, has_api_key=%s",


        config.get("enabled"),


        bool(config.get("api_key")),


    )





    if not config.get("enabled", True):


        logger.info("[AI Key Levels] Disabled, skipping.")


        return None


    if not config.get("api_key"):


        logger.warning("[AI Key Levels] Missing API key, skipping.")


        return None





    snapshot = _build_snapshot(symbol)


    if not snapshot:


        logger.warning("[AI Key Levels] Snapshot unavailable for %s", symbol)


        return None

    language = _get_language()


    prompt = _build_key_levels_prompt(_safe_symbol(symbol), snapshot, language=language)


    logger.info("[AI Key Levels] Calling AI API for %s", symbol)


    raw = call_ai_with_queue(lambda: _call_ai_api(prompt, config, language=language))


    if not raw:


        logger.warning("[AI Key Levels] AI API returned empty response.")


        return None


    logger.info("[AI Key Levels] AI API response received (%s chars)", len(raw))





    parsed = _parse_ai_response(raw)


    price = float(snapshot.get("current_price", 0) or 0)


    supports = _normalize_levels(parsed.get("supports"), price, True)


    resistances = _normalize_levels(parsed.get("resistances"), price, False)


    logger.info(


        "[AI Key Levels] Parsed levels: supports=%s, resistances=%s",


        len(supports),


        len(resistances),


    )





    if supports or resistances:


        safe_symbol = _safe_symbol(symbol)


        set_levels(safe_symbol, supports, resistances, meta={"source": "ai-key-levels"})


        logger.info(


            "[AI Key Levels] Cached: %s supports, %s resistances",


            len(supports),


            len(resistances),


        )


    else:


        logger.warning("[AI Key Levels] No valid levels parsed.")





    return {"supports": supports, "resistances": resistances}








def _analyze_us_market(us_market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """分析美股数据对加密市场的影响"""
    config = get_ai_signal_config()
    if not config.get("enabled", True) or not config.get("api_key"):
        return None

    summary = us_market_data.get("us_market_summary", {})
    vix = us_market_data.get("vix")

    prompt_lines = [
        "# 角色定位",
        "你是顶级跨市场分析师，专注于美股与加密货币市场的联动分析。",
        "",
        "# 输出格式",
        "仅返回严格 JSON：",
        '{"analysis":"...","direction":"long/short/none"}',
        "",
        "# 分析框架（analysis字段，100-150字中文）",
        "要求：多因子交叉验证，若缺少关键数据需说明。",
        "",
        "## 1. 美股整体情绪",
        "- 大盘指数(SPY/QQQ/DIA)涨跌反映风险偏好",
        "- 科技股表现与加密市场高度相关",
        "",
        "## 2. 加密概念股信号",
        "- COIN/MSTR/MARA/RIOT 是加密市场先行指标",
        "- 概念股大涨 → 机构看好加密 → BTC/ETH利好",
        "- 概念股大跌 → 机构撤退 → 加密承压",
        "",
        "## 3. 宏观指标",
        "- VIX > 20: 恐慌情绪，风险资产承压",
        "- VIX < 15: 市场平静，利好风险资产",
        "- 黄金(GLD)上涨: 避险情绪，加密可能受益",
        "- 国债(TLT)上涨: 利率预期下降，利好加密",
        "",
        "## 4. 联动逻辑",
        "- 美股大涨 + 科技股领涨 → 风险偏好上升 → 加密看涨",
        "- 美股大跌 + VIX飙升 → 避险情绪 → 加密短期承压",
        "- 加密概念股独立上涨 → 行业利好 → 加密强势",
        "",
        "# 输出要点",
        "1. 开头明确标注：【利好加密】或【利空加密】或【影响中性】",
        "2. 说明美股各板块表现",
        "3. 重点分析加密概念股信号",
        "4. 给出对加密整体市场与BTC/ETH类别的短期影响预判（分开说明）",
        "",
        "# 输入数据",
        json.dumps(us_market_data, ensure_ascii=False, default=str),
    ]

    prompt = "\n".join(prompt_lines)
    raw = call_ai_with_queue(lambda: _call_ai_api(prompt, config, language="zh"))

    if not raw:
        return None

    parsed = _parse_ai_response(raw)
    return {
        "analysis": parsed.get("analysis", ""),
        "direction": parsed.get("direction", "none"),
    }


def analyze_signal(symbol: str, signal_payload: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:


    """AI signal brief."""


    logger.info(f"[AI Signal] 开始分析 {symbol}...")

    # 美股分析特殊处理
    if symbol == "US_MARKET" and signal_payload and "us_market" in signal_payload:
        return _analyze_us_market(signal_payload["us_market"])




    # AI简评使�?ai_signal_config.json 配置


    config = get_ai_signal_config()


    logger.info(f"[AI Signal] 配置: enabled={config.get('enabled')}, has_api_key={bool(config.get('api_key'))}")


    logger.info(


        "[AI Signal] Using model=%s url=%s",


        config.get("model"),


        config.get("api_url"),


    )


    


    if not config.get("enabled", True):


        logger.info(f"[AI Signal] 模块已禁用，跳过分析")


        return None


    


    if not config.get("api_key"):


        logger.warning(f"[AI Signal] Missing API Key; skip analysis.")


        return None





    is_metals = _is_metal_symbol(symbol)

    snapshot = _build_snapshot(symbol)


    if not snapshot:


        logger.warning(f"[AI Signal] 无法构建 {symbol} 快照数据")


        return None


    language = _get_language()


    analysis_time_bj = datetime.now(tz=BEIJING_TZ).strftime("%Y-%m-%d %H:%M:%S")


    recent_signals = _get_recent_signals_for_symbol(symbol)


    prompt = (
        _build_metals_prompt(
            _safe_symbol(symbol),
            snapshot,
            signal_payload=signal_payload,
            recent_signals=recent_signals,
            analysis_time_bj=analysis_time_bj,
            language=language,
        )
        if is_metals
        else _build_prompt(
            _safe_symbol(symbol),
            snapshot,
            signal_payload=signal_payload,
            recent_signals=recent_signals,
            analysis_time_bj=analysis_time_bj,
            language=language,
        )
    )


    logger.info(f"[AI Signal] 调用 AI API 分析 {symbol}...")


    raw = call_ai_with_queue(lambda: _call_ai_api(prompt, config, language=language))


    if not raw:


        logger.warning(f"[AI Signal] AI API returned empty response.")


        return None





    logger.info(f"[AI Signal] AI API 返回成功，解析结�?..")


    parsed = _parse_ai_response(raw)


    analysis = (parsed.get("analysis") or "").strip()


    price = float(snapshot.get("current_price", 0) or 0)


    entry_decision = _normalize_entry_decision(parsed.get("entry_decision"))


    risk_level = _normalize_risk_level(parsed.get("risk_level"))


    direction = _normalize_direction(parsed.get("direction"))


    raw_stop_loss = _normalize_price_value(parsed.get("stop_loss"))


    raw_take_profit = _normalize_price_value(parsed.get("take_profit"))


    confidence = _normalize_confidence(parsed.get("confidence"), analysis)


    if entry_decision == "yes" and direction == "none":


        direction = _infer_direction_from_levels(price, raw_stop_loss, raw_take_profit)


    if entry_decision != "yes":


        direction = "none"





    is_fomo_intensify = _is_fomo_intensify(signal_payload)


    if analysis and entry_decision == "yes" and not is_fomo_intensify:


        if "止盈" in analysis or "take profit" in analysis.lower():


            # Keep the model wording; avoid forcing a generic risk-only phrase.
            pass


    if analysis and entry_decision == "yes" and is_fomo_intensify:


        if "止盈" not in analysis and "take profit" not in analysis.lower():


            if _get_language() == "en":


                analysis = f"{analysis} Risk spikes; take profit in time."


            else:


                analysis = f"{analysis} 风险升温，注意及时止盈。"


    fundamentals_status = snapshot.get("fundamentals_status")
    analysis = _sanitize_fundamentals_note(analysis, fundamentals_status)
    analysis = _trim_analysis_length(analysis)
    analysis = _strip_confidence_threshold_notes(analysis)
    supports = _normalize_levels(parsed.get("supports"), price, True)


    resistances = _normalize_levels(parsed.get("resistances"), price, False)


    stop_loss, take_profit, rr = _extract_trade_levels(


        parsed,


        price,


        supports,


        resistances,


        entry_decision,


        direction,


    )

    min_rr = 2.0
    if entry_decision == "yes" and (rr is None or rr < min_rr):
        entry_decision = "no"
        direction = "none"
        stop_loss = None
        take_profit = None
        rr = None


    overlays = _normalize_overlays(


        parsed.get("overlays"),


        max(0, len(snapshot.get("klines", [])) - 1),


        snapshot.get("price_min"),


        snapshot.get("price_max"),


        [k.get("low") for k in snapshot.get("klines", []) if isinstance(k.get("low"), (int, float))],


        [k.get("high") for k in snapshot.get("klines", []) if isinstance(k.get("high"), (int, float))],


        snapshot.get("overlay_candidates", []),


    )





    if supports or resistances:


        set_levels(symbol, supports, resistances, meta={"source": "ai"})


        logger.info(f"[AI Signal] 缓存关键�? {len(supports)} 支撑, {len(resistances)} 阻力")


    if overlays:


        set_overlays(symbol, overlays, meta={"source": "ai"})


        logger.info(f"[AI Signal] Cached overlays: {len(overlays)}")





    logger.info(f"[AI Signal] �?{symbol} 分析完成: {analysis[:50]}..." if analysis else f"[AI Signal] �?{symbol} 分析完成")





    leverage_suggestion = _normalize_leverage_suggestion(parsed.get("leverage_suggestion"))
    if entry_decision != "yes":
        leverage_suggestion = "no_trade"

    analysis = (analysis or "").strip()
    if not analysis:
        fallback = _strip_confidence_threshold_notes(raw or "")
        fallback = _trim_analysis_length(fallback)
        analysis = (fallback or "").strip()
    if not analysis:
        analysis = "????"

    result = {


        "analysis": analysis,


        "market_phase": _normalize_trend_status(parsed.get("trend_status") or parsed.get("market_phase")),
        "trend_status": _normalize_trend_status(parsed.get("trend_status") or parsed.get("market_phase")),
        "leverage_suggestion": leverage_suggestion,
        "confidence": confidence,


        "supports": supports,


        "resistances": resistances,


        "stop_loss": stop_loss,


        "take_profit": take_profit,


        "rr": rr,


        "risk_level": risk_level,


        "entry_decision": entry_decision,


        "direction": direction,


        "overlays": overlays,


    }
    return result








def test_ai_single(symbol: str = "BTC") -> Optional[Dict[str, Any]]:


    """Run AI analysis for one symbol and render a chart locally."""


    result = analyze_signal(symbol)


    if not result:


        logger.warning("AI analysis failed or missing API config.")


        return None





    from chart_pro_v10 import generate_chart_v10





    image_data = generate_chart_v10(symbol, interval="1h", limit=200)


    if not image_data:


        logger.warning("Chart generation failed.")


        return result





    os.makedirs("output", exist_ok=True)


    image_path = os.path.join("output", f"ai_single_{symbol}.png")


    json_path = os.path.join("output", f"ai_single_{symbol}.json")





    with open(image_path, "wb") as f:


        f.write(image_data)


    with open(json_path, "w", encoding="utf-8") as f:


        json.dump(result, f, ensure_ascii=False, indent=2)





    logger.info("Saved AI single output: %s", image_path)


    logger.info("Saved AI single JSON: %s", json_path)


    return result
