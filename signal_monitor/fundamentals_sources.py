"""
Fundamental data sources (optional, cached).
"""

from __future__ import annotations

import csv
import html as html_lib
import json
import os
import re
import time
from datetime import datetime, timedelta, timezone
from io import StringIO
from pathlib import Path
from typing import Any, Dict, Optional, List
from xml.etree import ElementTree
from zoneinfo import ZoneInfo

import requests

try:
    from signal_monitor.logger import logger
except Exception:
    from logger import logger
try:
    from signal_monitor.macro_data import load_macro_data
except Exception:
    from macro_data import load_macro_data
try:
    from signal_monitor.market_data_sources import get_coingecko_id, get_coingecko_headers
except Exception:
    from market_data_sources import get_coingecko_id, get_coingecko_headers

COINGECKO_BASE = "https://api.coingecko.com/api/v3"
DEFILLAMA_BASE = "https://api.llama.fi"
FNG_URL = "https://api.alternative.me/fng/"
ETHERSCAN_BASE = "https://api.etherscan.io/v2/api"
FRED_BASE = "https://api.stlouisfed.org/fred"
FRED_CSV_BASE = "https://fred.stlouisfed.org/graph/fredgraph.csv"
GITHUB_BASE = "https://api.github.com"
GDELT_BASE = "https://api.gdeltproject.org/api/v2/doc/doc"
FF_CALENDAR_JSON_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
FF_CALENDAR_CSV_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.csv"
FF_CALENDAR_XML_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.xml"
FF_CALENDAR_HTML_URL = "https://www.forexfactory.com/calendar"
FF_CALENDAR_CACHE_PATH = Path(__file__).resolve().parents[1] / "data" / "ff_calendar_cache.txt"
TELEGRAM_SCRAPE_BASE = "https://t.me/s"
TRADING_ECONOMICS_BASE = "https://api.tradingeconomics.com"

DEFAULT_FRED_RELEASE_IDS = "10,46,50,53,54,101"
DEFAULT_ERC20_CONTRACTS = {
    "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
    "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
    "DAI": "0x6B175474E89094C44Da98b954EedeAC495271d0F",
    "LINK": "0x514910771AF9Ca656af840dff83E8264EcF986CA",
    "UNI": "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984",
    "AAVE": "0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9",
    "LDO": "0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32",
    "MKR": "0x9f8F72aA9304c8B593d555F12eF6589cC3A579A2",
    "COMP": "0xc00e94Cb662C3520282E6f5717214004A7f26888",
}

_SESSION = requests.Session()
_CACHE: Dict[str, Dict[str, Any]] = {}
_CACHE_MAX_SIZE = int(os.getenv("NOFX_FUNDAMENTALS_CACHE_MAX_SIZE", "512") or 512)


def _prune_cache(max_size: int = _CACHE_MAX_SIZE) -> None:
    now = time.time()
    expired_keys = [key for key, value in _CACHE.items() if now - float(value.get("ts", 0)) > 86400]
    for key in expired_keys:
        _CACHE.pop(key, None)

    if max_size <= 0 or len(_CACHE) <= max_size:
        return

    ordered = sorted(_CACHE.items(), key=lambda item: float(item[1].get("ts", 0)))
    for key, _ in ordered[: len(_CACHE) - max_size]:
        _CACHE.pop(key, None)


def _env_or_config(name: str, default: str = "") -> str:
    raw = os.getenv(name)
    if raw is not None and raw != "":
        return str(raw)
    try:
        import config as signal_config
        value = getattr(signal_config, name, default)
        return str(value)
    except Exception:
        return default


def _split_symbols(raw: str) -> List[str]:
    if not raw:
        return []
    return [s.strip().upper() for s in raw.split(",") if s.strip()]


def _env_or_config_bool(name: str, default: bool = False) -> bool:
    raw = _env_or_config(name, "")
    if raw == "":
        return default
    return str(raw).strip().lower() in ("1", "true", "yes", "on")


def _req(url: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> Optional[Any]:
    proxies = {}
    proxy = _env_or_config("NOFX_PROXY") or os.getenv("HTTP_PROXY") or os.getenv("HTTPS_PROXY")
    if proxy:
        proxies = {"http": proxy, "https": proxy}
    try:
        resp = _SESSION.get(url, params=params, headers=headers, timeout=12, proxies=proxies or None)
        if resp.status_code == 200:
            return resp.json()
    except Exception as exc:
        logger.debug("fundamental request failed: %s", exc)
    return None


def _req_text(url: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> Optional[str]:
    proxies = {}
    proxy = _env_or_config("NOFX_PROXY") or os.getenv("HTTP_PROXY") or os.getenv("HTTPS_PROXY")
    if proxy:
        proxies = {"http": proxy, "https": proxy}
    try:
        resp = _SESSION.get(url, params=params, headers=headers, timeout=12, proxies=proxies or None)
        if resp.status_code == 200:
            return resp.text
    except Exception as exc:
        logger.debug("fundamental request text failed: %s", exc)
    return None


def _cache_get(key: str, ttl: int) -> Optional[Dict[str, Any]]:
    _prune_cache()
    cached = _CACHE.get(key)
    if not cached:
        return None
    if (time.time() - cached["ts"]) > ttl:
        return None
    return cached.get("value")


def _cache_set(key: str, value: Dict[str, Any]) -> None:
    _prune_cache()
    _CACHE[key] = {"ts": time.time(), "value": value}
    _prune_cache()


def _coingecko_number(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, dict):
        return float(value.get("usd")) if value.get("usd") is not None else None
    try:
        return float(value)
    except Exception:
        return None


def _fetch_coingecko_coin(symbol: str) -> Optional[Dict[str, Any]]:
    coin_id = get_coingecko_id(symbol)
    if not coin_id:
        return None
    params = {
        "localization": "false",
        "tickers": "false",
        "market_data": "true",
        "community_data": "true",
        "developer_data": "true",
        "sparkline": "false",
    }
    return _req(f"{COINGECKO_BASE}/coins/{coin_id}", params=params, headers=get_coingecko_headers())


def _fetch_defillama_chain_tvl(symbol: str) -> Optional[Dict[str, Any]]:
    chain_map = {
        "ETH": "Ethereum",
        "BTC": "Bitcoin",
        "BNB": "Binance",
        "SOL": "Solana",
        "ARB": "Arbitrum",
        "OP": "Optimism",
        "AVAX": "Avalanche",
        "MATIC": "Polygon",
    }
    chain = chain_map.get(symbol.upper())
    if not chain:
        return None
    data = _req(f"{DEFILLAMA_BASE}/chains")
    if not isinstance(data, list):
        return None
    for item in data:
        if isinstance(item, dict) and str(item.get("chain")) == chain:
            return {
                "chain": chain,
                "tvl": item.get("tvl"),
                "tvl_change_1d": item.get("change_1d"),
                "tvl_change_7d": item.get("change_7d"),
            }
    return None


def _fetch_fear_greed() -> Optional[Dict[str, Any]]:
    data = _req(FNG_URL, params={"limit": 1, "format": "json"})
    if not isinstance(data, dict):
        return None
    items = data.get("data") or []
    if not items:
        return None
    item = items[0] if isinstance(items[0], dict) else None
    if not item:
        return None
    return {
        "value": item.get("value"),
        "classification": item.get("value_classification"),
        "timestamp": item.get("timestamp"),
        "source": "alternative.me",
    }


def _fetch_etherscan_json(params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    api_key = _env_or_config("ETHERSCAN_API_KEY")
    if api_key:
        params["apikey"] = api_key
    params.setdefault("chainid", "1")
    data = _req(ETHERSCAN_BASE, params=params)
    if not isinstance(data, dict):
        return None
    if data.get("status") not in ("1", 1, None):
        return None
    return data


def _fetch_etherscan_eth_stats() -> Optional[Dict[str, Any]]:
    supply = _fetch_etherscan_json({"module": "stats", "action": "ethsupply"})
    price = _fetch_etherscan_json({"module": "stats", "action": "ethprice"})
    if not supply and not price:
        return None
    out: Dict[str, Any] = {}
    if supply and supply.get("result"):
        out["eth_supply"] = supply.get("result")
    if price and isinstance(price.get("result"), dict):
        result = price["result"]
        out["eth_price_usd"] = result.get("ethusd")
        out["eth_btc"] = result.get("ethbtc")
    return out or None


def _fetch_etherscan_daily_txn(days: int = 7) -> Optional[Dict[str, Any]]:
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=days)
    params = {
        "module": "stats",
        "action": "dailytxn",
        "startdate": start.strftime("%Y-%m-%d"),
        "enddate": end.strftime("%Y-%m-%d"),
        "sort": "desc",
    }
    data = _fetch_etherscan_json(params)
    items = data.get("result") if isinstance(data, dict) else None
    if not isinstance(items, list) or not items:
        return None
    latest = items[0] if isinstance(items[0], dict) else None
    if not latest:
        return None
    return {
        "date": latest.get("unixTime") or latest.get("date"),
        "tx_count": latest.get("transactionCount"),
    }


def _fetch_etherscan_token_supply(symbol: str) -> Optional[Dict[str, Any]]:
    raw = _env_or_config("NOFX_ERC20_CONTRACTS")
    mapping: Dict[str, Any] = {}
    if raw:
        try:
            mapping = json.loads(raw)
        except Exception:
            mapping = {}
    if not mapping:
        mapping = dict(DEFAULT_ERC20_CONTRACTS)
    if not isinstance(mapping, dict):
        return None
    contract = mapping.get(symbol.upper())
    if not contract:
        return None
    data = _fetch_etherscan_json({"module": "stats", "action": "tokensupply", "contractaddress": contract})
    if not isinstance(data, dict):
        return None
    return {"contract": contract, "supply": data.get("result")}


def _fetch_fred_series_csv(series_id: str, limit: int = 3) -> Optional[Dict[str, Any]]:
    params = {"id": series_id}
    text = _req_text(FRED_CSV_BASE, params=params)
    if not text:
        return None
    try:
        reader = csv.reader(StringIO(text))
        rows = list(reader)
    except Exception:
        return None
    if len(rows) < 2 or not rows[0]:
        return None
    header = rows[0]
    if len(header) < 2:
        return None
    try:
        value_idx = header.index(series_id)
    except ValueError:
        value_idx = 1
    observations = []
    for row in rows[1:]:
        if len(row) <= value_idx:
            continue
        date = row[0]
        value = row[value_idx]
        if not value or value == ".":
            continue
        observations.append({"date": date, "value": value})
    if not observations:
        return None
    observations = list(reversed(observations))[: max(1, int(limit))]
    titles_en = {
        "PAYEMS": "Nonfarm Payrolls",
        "CPIAUCSL": "CPI (All Urban Consumers)",
        "UNRATE": "Unemployment Rate",
        "FEDFUNDS": "Fed Funds Rate",
        "GDP": "Gross Domestic Product",
        "PCE": "Personal Consumption Expenditures",
        "PPIACO": "Producer Price Index",
        "RSAFS": "Retail Sales",
        "PMI": "Purchasing Managers Index",
    }
    titles_cn = {
        "PAYEMS": "非农就业",
        "CPIAUCSL": "CPI（全美城市消费者）",
        "UNRATE": "失业率",
        "FEDFUNDS": "联邦基金利率",
        "GDP": "国内生产总值",
        "PCE": "个人消费支出",
        "PPIACO": "PPI（生产者物价指数）",
        "RSAFS": "零售销售",
        "PMI": "采购经理指数",
    }
    title_en = titles_en.get(series_id, series_id)
    title_cn = titles_cn.get(series_id, title_en)
    return {
        "series_id": series_id,
        "title": title_cn,
        "title_en": title_en,
        "observations": observations,
    }


def _fetch_fred_series(series_id: str, limit: int = 3) -> Optional[Dict[str, Any]]:
    api_key = _env_or_config("FRED_API_KEY")
    if not api_key:
        return _fetch_fred_series_csv(series_id, limit)
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "sort_order": "desc",
        "limit": limit,
    }
    data = _req(f"{FRED_BASE}/series/observations", params=params)
    if not isinstance(data, dict):
        return None
    obs = data.get("observations")
    if not isinstance(obs, list) or not obs:
        return None
    titles_en = {
        "PAYEMS": "Nonfarm Payrolls",
        "CPIAUCSL": "CPI (All Urban Consumers)",
        "UNRATE": "Unemployment Rate",
        "FEDFUNDS": "Fed Funds Rate",
        "GDP": "Gross Domestic Product",
        "PCE": "Personal Consumption Expenditures",
        "PPIACO": "Producer Price Index",
        "RSAFS": "Retail Sales",
        "PMI": "Purchasing Managers Index",
    }
    titles_cn = {
        "PAYEMS": "非农就业",
        "CPIAUCSL": "CPI（全美城市消费者）",
        "UNRATE": "失业率",
        "FEDFUNDS": "联邦基金利率",
        "GDP": "国内生产总值",
        "PCE": "个人消费支出",
        "PPIACO": "PPI（生产者物价指数）",
        "RSAFS": "零售销售",
        "PMI": "采购经理指数",
    }
    title_en = titles_en.get(series_id, series_id)
    title_cn = titles_cn.get(series_id, title_en)
    return {
        "series_id": series_id,
        "title": title_cn,
        "title_en": title_en,
        "observations": obs,
    }


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    return text.replace("\n", " ").replace("\r", " ").strip()


def _translate_macro_title(title: str) -> str:
    if not title:
        return ""
    raw = str(title).strip()
    lower = raw.lower()
    if "bank holiday" in lower:
        return "银行假日"
    if "interest rate decision" in lower:
        return "利率决议"
    if "rate decision" in lower:
        return "利率决议"
    if "policy statement" in lower:
        return "政策声明"
    if "press conference" in lower:
        return "新闻发布会"
    if "fomc statement" in lower:
        return "FOMC声明"
    if "fomc minutes" in lower or "meeting minutes" in lower:
        return "FOMC会议纪要"
    if "non-farm" in lower or "nonfarm" in lower or "nfp" in lower:
        return "非农就业"
    if "unemployment rate" in lower:
        return "失业率"
    if "average hourly earnings" in lower:
        return "平均时薪"
    if "retail sales" in lower and ("m/m" in lower or "mom" in lower):
        return "零售销售环比"
    if "retail sales" in lower and ("y/y" in lower or "yoy" in lower):
        return "零售销售同比"
    if "cpi" in lower and ("y/y" in lower or "yoy" in lower):
        return "CPI同比"
    if "cpi" in lower and ("m/m" in lower or "mom" in lower):
        return "CPI环比"
    if "core cpi" in lower and ("y/y" in lower or "yoy" in lower):
        return "核心CPI同比"
    if "core cpi" in lower and ("m/m" in lower or "mom" in lower):
        return "核心CPI环比"
    if "ppi" in lower and ("y/y" in lower or "yoy" in lower):
        return "PPI同比"
    if "ppi" in lower and ("m/m" in lower or "mom" in lower):
        return "PPI环比"
    if "gdp" in lower and ("q/q" in lower or "qoq" in lower):
        return "GDP环比"
    if "manufacturing pmi" in lower:
        return "制造业PMI"
    if "services pmi" in lower:
        return "服务业PMI"
    if "composite pmi" in lower:
        return "综合PMI"
    if "jobless claims" in lower:
        return "初请失业金"
    if "nonfarm" in lower or "nfp" in lower:
        return "非农就业"
    if "consumer price index" in lower or lower.startswith("cpi"):
        return "CPI"
    if "unemployment" in lower or lower.startswith("unrate"):
        return "失业率"
    if "fed funds" in lower or "fomc" in lower or "rate decision" in lower:
        return "美联储利率决议"
    if "interest rate" in lower:
        return "利率决议"
    if "gdp" in lower:
        return "GDP"
    if "pce" in lower:
        return "PCE"
    if "ppi" in lower:
        return "PPI"
    if "retail sales" in lower:
        return "零售销售"
    if "pmi" in lower:
        return "PMI"
    if "jobless claims" in lower or "initial jobless" in lower:
        return "初请失业金"
    if "adp" in lower and "employment" in lower:
        return "ADP就业变动"
    if "core cpi" in lower:
        return "核心CPI"
    if "core pce" in lower:
        return "核心PCE"
    if "pce price" in lower:
        return "PCE物价指数"
    if "ism" in lower and "manufacturing" in lower:
        return "ISM制造业PMI"
    if "ism" in lower and ("non-manufacturing" in lower or "services" in lower):
        return "ISM非制造业PMI"
    if "s&p" in lower and "pmi" in lower:
        return "S&P全球PMI"
    if "manufacturing pmi" in lower:
        return "制造业PMI"
    if "services pmi" in lower:
        return "服务业PMI"
    if "composite pmi" in lower:
        return "综合PMI"
    if "retail sales" in lower:
        return "零售销售"
    if "industrial production" in lower:
        return "工业产出"
    if "factory orders" in lower:
        return "工厂订单"
    if "durable goods" in lower:
        return "耐用品订单"
    if "consumer confidence" in lower:
        return "消费者信心"
    if "michigan" in lower and "sentiment" in lower:
        return "密歇根消费者信心"
    if "housing starts" in lower:
        return "新屋开工"
    if "building permits" in lower:
        return "营建许可"
    if "existing home sales" in lower:
        return "成屋销售"
    if "new home sales" in lower:
        return "新屋销售"
    if "trade balance" in lower:
        return "贸易差额"
    if "current account" in lower:
        return "经常账户"
    if "fed" in lower and "minutes" in lower:
        return "美联储会议纪要"
    if "fed" in lower and ("speech" in lower or "testimony" in lower):
        return "美联储主席讲话"
    if "ecb" in lower and "rate" in lower:
        return "欧洲央行利率决议"
    if "boe" in lower and "rate" in lower:
        return "英国央行利率决议"
    if "boj" in lower and "rate" in lower:
        return "日本央行利率决议"
    if "pboc" in lower or "pbo" in lower:
        return "中国央行政策"
    if "rba" in lower and "rate" in lower:
        return "澳洲联储利率决议"
    if "rbnz" in lower and "rate" in lower:
        return "新西兰央行利率决议"
    if "snb" in lower and "rate" in lower:
        return "瑞士央行利率决议"
    if "boc" in lower and "rate" in lower:
        return "加拿大央行利率决议"
    if "rate decision" in lower:
        return "利率决议"
    if "policy" in lower or "regulation" in lower:
        return "政策/监管"
    return raw


def _format_macro_item(item: Dict[str, Any]) -> Optional[str]:
    if not isinstance(item, dict):
        return None
    title = (
        item.get("title")
        or item.get("event")
        or item.get("name")
        or item.get("indicator")
        or item.get("id")
        or item.get("release_id")
        or item.get("series_id")
    )
    if not title:
        return None
    title = _translate_macro_title(_safe_text(title))
    def _norm_value(value: Any) -> Optional[str]:
        if value is None:
            return None
        text = _safe_text(value)
        if not text:
            return None
        if text.lower() in ("n/a", "na", "null", "none", "-"):
            return None
        if text in ("0", "0.0", "0.00", "0.000", "0%", "0.0%", "0.00%"):
            return None
        return text

    actual = _norm_value(item.get("actual") or item.get("value"))
    forecast = _norm_value(item.get("forecast") or item.get("consensus") or item.get("expected"))
    previous = _norm_value(item.get("previous") or item.get("prior"))
    date = item.get("date") or item.get("time") or item.get("release_time")
    parts = [f"{_safe_text(title)}"]
    if actual:
        parts.append(f"实际 {actual}")
    if forecast:
        parts.append(f"预期 {forecast}")
    if previous:
        parts.append(f"前值 {previous}")

        parts.append(f"时间 {_safe_text(date)}")
    return " | ".join(parts)


def _match_keywords(text: str, keywords: List[str]) -> bool:
    if not text:
        return False
    lower = str(text).lower()
    for keyword in keywords:
        if not keyword:
            continue
        key = keyword.lower()
        if key.isalpha() and len(key) <= 3:
            if re.search(rf"\b{re.escape(key)}\b", lower):
                return True
            continue
        if key in lower:
            return True
    return False


def _contains_chinese(text: str) -> bool:
    if not text:
        return False
    return any("\u4e00" <= ch <= "\u9fff" for ch in str(text))


def _is_chinese_language(value: Any) -> bool:
    if not value:
        return False
    text = str(value).strip().lower()
    return text in ("zh", "zh-cn", "zh-tw", "zh-hk", "chinese", "cn", "zho")


def _extract_macro_items(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("items", "data", "events", "calendar", "releases"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def _compact_macro_items(items: List[Dict[str, Any]], max_items: int = 5) -> List[Dict[str, Any]]:
    compacted: List[Dict[str, Any]] = []
    for item in items:
        title = (
            item.get("title")
            or item.get("event")
            or item.get("name")
            or item.get("indicator")
            or item.get("id")
            or item.get("release_id")
            or item.get("series_id")
        )
        if not title:
            continue
        compacted.append(
            {
                "title": _translate_macro_title(_safe_text(title)),
                "actual": item.get("actual") or item.get("value"),
                "forecast": item.get("forecast") or item.get("consensus") or item.get("expected"),
                "previous": item.get("previous") or item.get("prior"),
                "time": item.get("date") or item.get("time") or item.get("release_time"),
                "importance": item.get("importance") or item.get("impact") or item.get("level"),
            }
        )
        if len(compacted) >= max_items:
            break
    return compacted


def _compact_gdelt_articles(payload: Dict[str, Any], max_items: int = 5) -> List[Dict[str, Any]]:
    articles = payload.get("articles") if isinstance(payload, dict) else None
    if not isinstance(articles, list):
        return []
    compacted: List[Dict[str, Any]] = []
    for item in articles:
        if not isinstance(item, dict):
            continue
        title = item.get("title")
        if not title:
            continue
        language = item.get("language")
        if language and not _is_chinese_language(language) and not _contains_chinese(title):
            continue
        compacted.append(
            {
                "title": _safe_text(title),
                "time": item.get("seendate"),
                "source": item.get("domain") or item.get("sourcecountry"),
                "url": item.get("url"),
                "language": language,
            }
        )
        if len(compacted) >= max_items:
            break
    return compacted


def _merge_calendar_items(base: Dict[str, Any], extra: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(base, dict):
        base = {}
    if not isinstance(extra, dict):
        return base
    extra_calendar = extra.get("calendar") if isinstance(extra.get("calendar"), dict) else None
    if not extra_calendar:
        return base
    extra_items = extra_calendar.get("items")
    if not isinstance(extra_items, list) or not extra_items:
        return base
    calendar = base.get("calendar")
    if not isinstance(calendar, dict):
        calendar = {"items": []}
        base["calendar"] = calendar
    base_items = calendar.get("items")
    if not isinstance(base_items, list):
        base_items = []
        calendar["items"] = base_items
    seen = set()
    for item in base_items:
        if not isinstance(item, dict):
            continue
        seen.add((item.get("title"), item.get("date"), item.get("country")))
    for item in extra_items:
        if not isinstance(item, dict):
            continue
        key = (item.get("title"), item.get("date"), item.get("country"))
        if key in seen:
            continue
        base_items.append(item)
        seen.add(key)
    return base


def _merge_news_payloads(*payloads: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    articles: List[Dict[str, Any]] = []
    sources: List[str] = []
    seen = set()
    for payload in payloads:
        if not isinstance(payload, dict):
            continue
        source = payload.get("source") or payload.get("channel")
        if source:
            sources.append(str(source))
        items = payload.get("articles") or payload.get("items")
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            title = item.get("title") or ""
            language = item.get("language")
            if language and not _is_chinese_language(language) and not _contains_chinese(title):
                continue
            key = (item.get("title"), item.get("seendate") or item.get("time"), item.get("url"))
            if key in seen:
                continue
            seen.add(key)
            articles.append(item)
    if not articles:
        return None
    return {"source": "+".join([s for s in sources if s]), "articles": articles}


def _format_fred_series_brief(item: Dict[str, Any]) -> Optional[str]:
    title = item.get("title") or item.get("title_cn") or item.get("series_id")
    if not title:
        return None
    observations = item.get("observations")
    if not isinstance(observations, list) or not observations:
        return None
    latest = observations[0] if isinstance(observations[0], dict) else None
    if not latest:
        return None
    value = latest.get("value")
    date = latest.get("date")
    if value is None:
        return None
    line = f"{_safe_text(title)}: {value}"
    if date:
        line = f"{line} ({_safe_text(date)})"
    return line


def _build_macro_focus(
    macro_data: Dict[str, Any],
    macro_fred: Optional[Dict[str, Any]],
    macro_gdelt: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    economic_keywords = [
        "cpi", "pce", "ppi", "gdp", "payroll", "nonfarm", "nfp", "employment", "unemployment",
        "rate", "fomc", "fed", "interest", "pmi", "retail", "inflation", "jobless", "claims",
        "通胀", "非农", "就业", "失业", "利率", "央行", "pmi", "零售", "gdp",
    ]
    policy_keywords = [
        "policy", "regulation", "regulatory", "rate decision", "policy statement", "minutes",
        "fomc", "central bank", "fed", "ecb", "boj", "boe", "pboc", "treasury", "sec", "ban",
        "approval", "law", "tariff",
        "政策", "监管", "利率决议", "央行", "法案", "禁令", "批准", "税", "财政", "货币",
        "宽松", "紧缩", "缩表", "扩表",
    ]
    event_keywords = [
        "war", "conflict", "geopolit", "sanction", "attack", "strike", "crisis", "default",
        "election", "protest", "riot", "earthquake", "hurricane", "explosion", "military",
        "战争", "冲突", "地缘", "制裁", "袭击", "罢工", "危机", "违约", "选举", "示威", "地震", "飓风",
        "爆炸", "军事",
    ]

    policy_event_keywords = [
        "rate decision", "policy", "statement", "minutes", "meeting", "press conference",
        "speech", "testimony", "rate", "interest", "monetary",
        "利率", "政策", "声明", "纪要", "会议", "新闻发布会",
        "讲话", "证词",
    ]

    calendar_items = _extract_macro_items((macro_data or {}).get("calendar"))
    recent_items = _extract_macro_items((macro_data or {}).get("recent_releases"))
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(days=7)

    def _has_actual(item: Dict[str, Any]) -> bool:
        actual = item.get("actual") or item.get("value")
        if actual is None:
            return False
        if isinstance(actual, str) and not actual.strip():
            return False
        return True

    def _event_time(item: Dict[str, Any]) -> Optional[datetime]:
        for key in ("date", "time", "release_time", "datetime"):
            dt = _parse_macro_time(item.get(key))
            if dt:
                return dt
        return None

    def _within_window(item: Dict[str, Any], start: datetime, end: datetime) -> bool:
        dt = _event_time(item)
        if not dt:
            return False
        return start <= dt <= end

    def _impact_level(item: Dict[str, Any]) -> str:
        impact = item.get("impact") or item.get("importance") or item.get("level") or ""
        return str(impact).strip().lower()

    def _is_high(item: Dict[str, Any]) -> bool:
        return "high" in _impact_level(item)

    def _is_medium(item: Dict[str, Any]) -> bool:
        return "medium" in _impact_level(item)

    recent_window_items = [item for item in calendar_items if _within_window(item, window_start, now)]
    recent_all = recent_items + recent_window_items

    economic_calendar = [item for item in calendar_items if _match_keywords(str(item), economic_keywords)]
    economic_recent = [item for item in recent_all if _match_keywords(str(item), economic_keywords) and _within_window(item, window_start, now)]
    policy_calendar = [item for item in calendar_items if _match_keywords(str(item), policy_keywords) and not _match_keywords(str(item), economic_keywords)]
    policy_recent = [item for item in recent_all if _match_keywords(str(item), policy_keywords) and not _match_keywords(str(item), economic_keywords)]
    policy_recent = [item for item in policy_recent if _within_window(item, window_start, now)]

    economic_data = {
        "recent_releases": _compact_macro_items(economic_recent, max_items=6),
        "upcoming": _compact_macro_items(economic_calendar, max_items=6),
        "fred_series": [],
        "brief": [],
    }
    if isinstance(macro_fred, dict):
        series = macro_fred.get("series") if isinstance(macro_fred.get("series"), list) else []
        upcoming = macro_fred.get("upcoming") if isinstance(macro_fred.get("upcoming"), list) else []
        economic_data["fred_series"] = [
            {
                "series_id": item.get("series_id"),
                "title": item.get("title") or item.get("title_cn") or item.get("series_id"),
                "latest": (item.get("observations") or [{}])[0].get("value") if isinstance(item.get("observations"), list) and item.get("observations") else None,
                "date": (item.get("observations") or [{}])[0].get("date") if isinstance(item.get("observations"), list) and item.get("observations") else None,
            }
            for item in series
            if isinstance(item, dict)
        ]
        economic_data["upcoming"].extend(_compact_macro_items([item for item in upcoming if isinstance(item, dict)], max_items=6))

    brief_lines: List[str] = []
    for item in economic_data["recent_releases"]:
        line = _format_macro_item(item)
        if line:
            brief_lines.append(line)
            if len(brief_lines) >= 2:
                break
    economic_data["brief"] = brief_lines

    major_events = []
    gdelt_articles = _compact_gdelt_articles(macro_gdelt or {}, max_items=12)
    for item in gdelt_articles:
        title = item.get("title") or ""
        if not title:
            continue
        if not _contains_chinese(title):
            continue
        if _match_keywords(title, event_keywords):
            major_events.append(item)
        if len(major_events) >= 6:
            break
    if not major_events:
        for item in calendar_items:
            if not isinstance(item, dict):
                continue
            text_blob = str(item)
            if not _match_keywords(text_blob, event_keywords):
                continue
            impact = str(item.get("impact") or "").lower()
            if impact and "high" not in impact and "medium" not in impact:
                continue
            title = _translate_macro_title(
                _safe_text(item.get("title") or item.get("event") or item.get("name") or "")
            )
            if not title:
                continue
            major_events.append(
                {
                    "title": title,
                    "time": item.get("date") or item.get("time") or item.get("release_time"),
                    "impact": item.get("impact"),
                    "source": item.get("source") or "calendar",
                }
            )
            if len(major_events) >= 6:
                break
    major_event_brief = []
    for item in major_events:
        title = item.get("title")
        if title:
            major_event_brief.append(title)
        if len(major_event_brief) >= 3:
            break

    major_policies = []
    for item in policy_recent + policy_calendar:
        raw_title = _safe_text(item.get("name") or item.get("event") or item.get("title"))
        if not raw_title:
            continue
        raw_lower = raw_title.strip().lower()
        if raw_lower in ("policy", "regulation", "regulatory", "policy/regulation"):
            continue
        if not _match_keywords(raw_title, policy_event_keywords):
            continue
        title_cn = _translate_macro_title(raw_title)
        if title_cn.strip() in ("政策/监管", "政策监管"):
            continue
        major_policies.append(
            {
                "title": title_cn,
                "time": item.get("date") or item.get("time") or item.get("release_time"),
                "importance": item.get("importance") or item.get("impact") or item.get("level"),
            }
        )
        if len(major_policies) >= 6:
            break

    policy_brief = []
    for item in major_policies:
        title = item.get("title")
        if title:
            policy_brief.append(title)
        if len(policy_brief) >= 3:
            break

    return {
        "economic_data": economic_data,
        "major_events": {"items": major_events, "brief": major_event_brief},
        "major_policies": {"items": major_policies, "brief": policy_brief},
    }


def build_macro_brief(max_items: int = 3) -> List[str]:
    payload = fetch_macro_snapshot()
    if not isinstance(payload, dict):
        return []
    lines: List[str] = []

    macro = payload.get("macro") if isinstance(payload.get("macro"), dict) else {}
    macro_fred = payload.get("macro_fred") if isinstance(payload.get("macro_fred"), dict) else {}
    macro_gdelt = payload.get("macro_gdelt") if isinstance(payload.get("macro_gdelt"), dict) else {}

    focus = _build_macro_focus(macro, macro_fred, macro_gdelt)
    economic = focus.get("economic_data") if isinstance(focus.get("economic_data"), dict) else {}
    events = focus.get("major_events") if isinstance(focus.get("major_events"), dict) else {}
    policies = focus.get("major_policies") if isinstance(focus.get("major_policies"), dict) else {}

    econ_brief = economic.get("brief") if isinstance(economic.get("brief"), list) else []
    event_brief = events.get("brief") if isinstance(events.get("brief"), list) else []
    policy_brief = policies.get("brief") if isinstance(policies.get("brief"), list) else []

    if econ_brief:
        lines.append(f"经济数据: {econ_brief[0]}")
    else:
        lines.append("经济数据: 暂无")
    if event_brief:
        lines.append(f"重大事件: {event_brief[0]}")
    else:
        lines.append("重大事件: 暂无")
    if policy_brief:
        lines.append(f"重大政策: {policy_brief[0]}")
    else:
        lines.append("重大政策: 暂无")

    if not lines:
        return []
    return lines[: max(1, int(max_items))]


def _fetch_fred_release_dates() -> Optional[Dict[str, Any]]:
    api_key = _env_or_config("FRED_API_KEY")
    raw_ids = _env_or_config("NOFX_FRED_RELEASE_IDS") or DEFAULT_FRED_RELEASE_IDS
    if not api_key or not raw_ids:
        return None
    release_ids = _split_symbols(raw_ids)
    if not release_ids:
        return None
    upcoming = []
    now = datetime.now(timezone.utc)
    for rid in release_ids:
        params = {
            "release_id": rid,
            "api_key": api_key,
            "file_type": "json",
            "include_release_dates_with_no_data": "true",
        }
        data = _req(f"{FRED_BASE}/release/dates", params=params)
        dates = data.get("release_dates") if isinstance(data, dict) else None
        if not isinstance(dates, list):
            continue
        for item in dates:
            if not isinstance(item, dict):
                continue
            date_str = item.get("date")
            if not date_str:
                continue
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            except Exception:
                continue
            if dt >= now and (dt - now).days <= 7:
                upcoming.append({"release_id": rid, "date": date_str})
    return {"upcoming": upcoming} if upcoming else None


def _parse_ff_json(data: Any) -> List[Dict[str, Any]]:
    if not isinstance(data, list):
        return []
    items = []
    for item in data:
        if not isinstance(item, dict):
            continue
        title = item.get("title") or item.get("event") or item.get("name")
        if not title:
            continue
        date_value = _normalize_ff_datetime(item.get("date"))
        items.append(
            {
                "title": title,
                "country": item.get("country"),
                "date": date_value,
                "impact": item.get("impact"),
                "forecast": item.get("forecast"),
                "previous": item.get("previous"),
                "actual": item.get("actual"),
                "source": "forexfactory",
            }
        )
    return items


def _parse_ff_csv(text: str) -> List[Dict[str, Any]]:
    if not text:
        return []
    try:
        reader = csv.DictReader(StringIO(text))
    except Exception:
        return []
    items = []
    for row in reader:
        if not isinstance(row, dict):
            continue
        title = row.get("title") or row.get("event") or row.get("name")
        if not title:
            continue
        date_value = _normalize_ff_datetime(row.get("date"))
        items.append(
            {
                "title": title,
                "country": row.get("country"),
                "date": date_value,
                "impact": row.get("impact"),
                "forecast": row.get("forecast"),
                "previous": row.get("previous"),
                "actual": row.get("actual"),
                "source": "forexfactory",
            }
        )
    return items


def _parse_ff_xml(text: str) -> List[Dict[str, Any]]:
    if not text:
        return []
    try:
        root = ElementTree.fromstring(text)
    except Exception:
        return []
    items = []
    for event in root.findall(".//event"):
        title = _safe_text(event.findtext("title"))
        if not title:
            continue
        country = _safe_text(event.findtext("country"))
        date_raw = _safe_text(event.findtext("date"))
        time_raw = _safe_text(event.findtext("time"))
        date_value = _normalize_ff_datetime(date_raw, time_raw)
        items.append(
            {
                "title": title,
                "country": country,
                "date": date_value or date_raw or time_raw,
                "impact": _safe_text(event.findtext("impact")),
                "forecast": _safe_text(event.findtext("forecast")),
                "previous": _safe_text(event.findtext("previous")),
                "actual": _safe_text(event.findtext("actual")),
                "source": "forexfactory",
            }
        )
    return items


def _fetch_ff_calendar() -> Optional[Dict[str, Any]]:
    if not _env_or_config_bool("NOFX_FF_CALENDAR_ENABLED", True):
        return None
    try:
        ttl = int(_env_or_config("NOFX_FF_CALENDAR_TTL_SEC", "1800") or 1800)
    except ValueError:
        ttl = 1800
    cached = _cache_get("ff_calendar", ttl)
    if cached is not None:
        return cached
    items: List[Dict[str, Any]] = []

    data = _req(FF_CALENDAR_JSON_URL)
    items = _parse_ff_json(data)

    if not items:
        csv_text = _req_text(FF_CALENDAR_CSV_URL)
        items = _parse_ff_csv(csv_text or "")

    if not items:
        xml_text = _req_text(FF_CALENDAR_XML_URL)
        items = _parse_ff_xml(xml_text or "")

    if items:
        try:
            FF_CALENDAR_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            FF_CALENDAR_CACHE_PATH.write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    if not items:
        try:
            if FF_CALENDAR_CACHE_PATH.exists():
                max_age = int(_env_or_config("NOFX_FF_CALENDAR_CACHE_MAX_AGE_SEC", "86400") or 86400)
                if (time.time() - FF_CALENDAR_CACHE_PATH.stat().st_mtime) <= max_age:
                    cached_text = FF_CALENDAR_CACHE_PATH.read_text(encoding="utf-8", errors="ignore")
                    cached_items = json.loads(cached_text) if cached_text else []
                    if isinstance(cached_items, list):
                        items = cached_items
        except Exception:
            items = []

    if not items:
        return None
    if not items:
        return None
    payload = {"calendar": {"items": items}, "source": "forexfactory"}
    _cache_set("ff_calendar", payload)
    return payload


def fetch_forexfactory_calendar() -> Dict[str, Any]:
    """Public wrapper for ForexFactory calendar (free source)."""
    data = _fetch_ff_calendar()
    return data or {}


def _fetch_te_calendar() -> Optional[Dict[str, Any]]:
    if not _env_or_config_bool("NOFX_TE_CALENDAR_ENABLED", True):
        return None
    api_key = _env_or_config("TRADING_ECONOMICS_API_KEY") or _env_or_config("NOFX_TE_API_KEY")
    if not api_key:
        return None
    try:
        ttl = int(_env_or_config("NOFX_TE_CALENDAR_TTL_SEC", "900") or 900)
    except ValueError:
        ttl = 900
    cached = _cache_get("te_calendar", ttl)
    if cached is not None:
        return cached
    params = {"c": api_key}
    data = _req(f"{TRADING_ECONOMICS_BASE}/calendar", params=params)
    if not isinstance(data, list):
        return None
    items: List[Dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        title = item.get("Event") or item.get("event") or item.get("Title") or item.get("title")
        if not title:
            continue
        date_value = _normalize_ff_datetime(item.get("Date") or item.get("date"))
        items.append(
            {
                "title": title,
                "country": item.get("Country") or item.get("country"),
                "date": date_value,
                "impact": item.get("Importance") or item.get("importance") or item.get("Impact"),
                "forecast": item.get("Forecast") or item.get("forecast"),
                "previous": item.get("Previous") or item.get("previous"),
                "actual": item.get("Actual") or item.get("actual"),
                "source": "tradingeconomics",
            }
        )
    if not items:
        return None
    payload = {"calendar": {"items": items}, "source": "tradingeconomics"}
    _cache_set("te_calendar", payload)
    return payload


def _strip_html(raw: str) -> str:
    if not raw:
        return ""
    text = raw.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
    text = re.sub(r"<\s*a[^>]*>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"</\s*a\s*>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = html_lib.unescape(text)
    return " ".join(text.split())


def _normalize_ff_datetime(date_value: Any, time_value: Optional[str] = None) -> str:
    text = _safe_text(date_value)
    time_text = _safe_text(time_value)
    if not text and not time_text:
        return ""
    if time_text and time_text.lower() in ("all day", "tentative"):
        time_text = ""
    combined = f"{text} {time_text}".strip() if time_text else text
    dt = _parse_macro_time(combined)
    if dt:
        return dt.astimezone(timezone.utc).isoformat()
    return combined


def _parse_macro_time(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = _safe_text(value)
    if not text:
        return None
    text = text.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            tz_name = _env_or_config("NOFX_FF_CALENDAR_TZ", "America/New_York")
            try:
                dt = dt.replace(tzinfo=ZoneInfo(tz_name))
            except Exception:
                dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass
    formats = (
        "%m-%d-%Y %I:%M%p",
        "%m-%d-%Y %H:%M",
        "%m-%d-%Y",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%Y/%m/%d",
        "%m/%d/%Y %H:%M",
        "%m/%d/%Y",
    )
    for fmt in formats:
        try:
            dt = datetime.strptime(text, fmt)
            tz_name = _env_or_config("NOFX_FF_CALENDAR_TZ", "America/New_York")
            try:
                dt = dt.replace(tzinfo=ZoneInfo(tz_name))
            except Exception:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            continue
    return None


def _parse_telegram_channel_page(html_text: str, channel: str) -> Dict[str, Any]:
    items: List[Dict[str, Any]] = []
    min_id: Optional[int] = None
    for block in html_text.split("tgme_widget_message_wrap"):
        if "data-post" not in block:
            continue
        post_match = re.search(r'data-post="([^"]+)"', block)
        if not post_match:
            continue
        post = post_match.group(1)
        msg_id = post.split("/")[-1]
        try:
            msg_id_int = int(msg_id)
        except Exception:
            msg_id_int = None
        if msg_id_int is not None:
            min_id = msg_id_int if min_id is None else min(min_id, msg_id_int)
        text_match = re.search(r'tgme_widget_message_text[^>]*>([\s\S]*?)</div>', block)
        if not text_match:
            continue
        text = _strip_html(text_match.group(1))
        if not text:
            continue
        time_match = re.search(r'datetime="([^"]+)"', block)
        time_value = time_match.group(1) if time_match else ""
        items.append(
            {
                "id": msg_id,
                "title": text,
                "seendate": time_value,
                "domain": "telegram",
                "url": f"https://t.me/{channel}/{msg_id}" if msg_id else "",
                "language": "zh",
            }
        )
    return {"items": items, "min_id": min_id}


def _fetch_jin10_telegram_news(limit: int = 100) -> Optional[Dict[str, Any]]:
    if not _env_or_config_bool("NOFX_JIN10_TG_ENABLED", True):
        return None
    channel = (_env_or_config("NOFX_JIN10_TG_CHANNEL", "jin10data") or "jin10data").strip().strip("@")
    try:
        ttl = int(_env_or_config("NOFX_JIN10_TG_TTL_SEC", "300") or 300)
    except ValueError:
        ttl = 300
    cache_key = f"jin10_tg:{channel}"
    cached = _cache_get(cache_key, ttl)
    if cached is not None:
        return cached
    try:
        max_pages = int(_env_or_config("NOFX_JIN10_TG_MAX_PAGES", "8") or 8)
    except ValueError:
        max_pages = 8
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html",
    }
    before: Optional[int] = None
    seen: set = set()
    articles: List[Dict[str, Any]] = []
    for _ in range(max_pages):
        url = f"{TELEGRAM_SCRAPE_BASE}/{channel}"
        if before:
            url = f"{url}?before={before}"
        text = _req_text(url, headers=headers)
        if not text:
            break
        parsed = _parse_telegram_channel_page(text, channel)
        page_items = parsed.get("items") if isinstance(parsed, dict) else []
        if not isinstance(page_items, list) or not page_items:
            break
        for item in page_items:
            if not isinstance(item, dict):
                continue
            msg_id = item.get("id")
            if msg_id and msg_id in seen:
                continue
            if msg_id:
                seen.add(msg_id)
            articles.append(item)
            if len(articles) >= limit:
                break
        if len(articles) >= limit:
            break
        before = parsed.get("min_id") if isinstance(parsed, dict) else None
        if not before:
            break
    if not articles:
        return None
    payload = {"source": "telegram", "channel": channel, "articles": articles[:limit]}
    _cache_set(cache_key, payload)
    return payload


def _fetch_gdelt_news(
    query: Optional[str] = None,
    timespan: Optional[str] = None,
    max_records: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    if not _env_or_config_bool("NOFX_GDELT_ENABLED", True):
        return None
    query = query or _env_or_config(
        "NOFX_GDELT_QUERY",
        "(crypto OR bitcoin OR ethereum OR regulation OR policy OR fed OR inflation OR cpi OR payroll OR geopolitics OR war OR sanctions)",
    )
    try:
        max_records = int(max_records or _env_or_config("NOFX_GDELT_MAX_RECORDS", "8") or 8)
    except ValueError:
        max_records = 8
    timespan = timespan or _env_or_config("NOFX_GDELT_TIMESPAN", "1d") or "1d"
    params = {
        "query": query,
        "mode": "artlist",
        "maxrecords": max_records,
        "format": "json",
        "sort": "hybridrel",
        "timespan": timespan,
    }
    data = _req(GDELT_BASE, params=params)
    if not isinstance(data, dict):
        return None
    articles = data.get("articles")
    if not isinstance(articles, list) or not articles:
        return None
    cleaned = []
    for item in articles[:max_records]:
        if not isinstance(item, dict):
            continue
        cleaned.append({
            "title": item.get("title"),
            "url": item.get("url"),
            "seendate": item.get("seendate"),
            "sourcecountry": item.get("sourcecountry"),
            "domain": item.get("domain"),
            "language": item.get("language"),
        })
    if not cleaned:
        return None
    return {"query": query, "timespan": timespan, "articles": cleaned}


def _load_json_payload(env_name: str, file_path: str) -> Dict[str, Any]:
    raw = _env_or_config(env_name, "")
    if raw:
        try:
            data = json.loads(raw)
            return data if isinstance(data, dict) else {"items": data}
        except Exception:
            return {"note": "invalid_env_json"}
    path = Path(file_path)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {"items": data}
    except Exception:
        return {"note": "invalid_file_json"}


def load_metals_supply_demand() -> Dict[str, Any]:
    return _load_json_payload(
        "NOFX_METALS_SUPPLY_DEMAND_JSON",
        str(Path(__file__).parent / "metals_supply_demand.json"),
    )


def fetch_metals_fundamentals(symbol: str) -> Dict[str, Any]:
    sym = str(symbol or "").upper().strip()
    if not sym:
        return {}
    base = sym.replace("USD", "")
    metals_payload: Dict[str, Any] = {}

    supply_demand = load_metals_supply_demand()
    if supply_demand:
        item = supply_demand.get(sym) or supply_demand.get(base) or supply_demand
        if item:
            metals_payload["supply_demand"] = item

    timespan = _env_or_config("NOFX_GDELT_TIMESPAN_METALS", "3d") or "3d"
    if base in ("XAU", "GOLD"):
        query = _env_or_config(
            "NOFX_GDELT_QUERY_GOLD",
            "(gold OR xau OR bullion OR central bank gold OR gold reserves OR geopolitics OR war OR sanctions OR conflict)",
        )
    elif base in ("XAG", "SILVER"):
        query = _env_or_config(
            "NOFX_GDELT_QUERY_SILVER",
            "(silver OR xag OR industrial demand OR solar demand OR geopolitics OR war OR sanctions OR conflict)",
        )
    else:
        query = _env_or_config(
            "NOFX_GDELT_QUERY_METALS",
            "(precious metals OR gold OR silver OR geopolitics OR war OR sanctions OR conflict)",
        )
    news = _fetch_gdelt_news(query=query, timespan=timespan)
    if news:
        metals_payload["news"] = news

    return metals_payload


def _fetch_github_repo(repo: str) -> Optional[Dict[str, Any]]:
    token = _env_or_config("GITHUB_TOKEN") or _env_or_config("NOFX_GITHUB_TOKEN")
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = _req(f"{GITHUB_BASE}/repos/{repo}", headers=headers)
    if not isinstance(data, dict):
        return None
    return {
        "full_name": data.get("full_name"),
        "stargazers": data.get("stargazers_count"),
        "forks": data.get("forks_count"),
        "open_issues": data.get("open_issues_count"),
        "subscribers": data.get("subscribers_count"),
        "updated_at": data.get("updated_at"),
        "pushed_at": data.get("pushed_at"),
    }


def fetch_fundamentals_snapshot(
    symbol: str,
    include_macro: bool = True,
    ttl_sec: Optional[int] = None,
) -> Dict[str, Any]:
    ttl = int(ttl_sec or os.getenv("NOFX_FUNDAMENTALS_TTL_SEC", "600") or 600)
    cache_key = f"{symbol.upper()}:{int(include_macro)}"
    cached = _cache_get(cache_key, ttl)
    if cached is not None:
        return cached

    payload: Dict[str, Any] = {}

    coin = _fetch_coingecko_coin(symbol)
    if isinstance(coin, dict):
        market = coin.get("market_data") or {}
        payload["tokenomics"] = {
            "circulating_supply": market.get("circulating_supply"),
            "total_supply": market.get("total_supply"),
            "max_supply": market.get("max_supply"),
            "fdv": _coingecko_number(market.get("fully_diluted_valuation")),
        }
        payload["project"] = {
            "dev_commits_4w": (coin.get("developer_data") or {}).get("commit_count_4_weeks"),
            "github_stars": (coin.get("developer_data") or {}).get("stars"),
            "github_forks": (coin.get("developer_data") or {}).get("forks"),
            "twitter_followers": (coin.get("community_data") or {}).get("twitter_followers"),
            "reddit_subscribers": (coin.get("community_data") or {}).get("reddit_subscribers"),
        }
        repos = ((coin.get("links") or {}).get("repos_url") or {}).get("github")
        if isinstance(repos, list) and repos:
            repo = str(repos[0]).strip().rstrip("/").replace("https://github.com/", "")
            if repo:
                gh = _fetch_github_repo(repo)
                if gh:
                    payload["project"]["github"] = gh

    onchain = _fetch_defillama_chain_tvl(symbol)
    if onchain:
        payload.setdefault("onchain", {})
        payload["onchain"]["defillama"] = onchain
    if symbol.upper() == "ETH":
        eth_stats = _fetch_etherscan_eth_stats()
        daily_txn = _fetch_etherscan_daily_txn()
        if eth_stats:
            payload.setdefault("onchain", {})
            payload["onchain"]["eth_stats"] = eth_stats
        if daily_txn:
            payload.setdefault("onchain", {})
            payload["onchain"]["daily_txn"] = daily_txn
    token_supply = _fetch_etherscan_token_supply(symbol)
    if token_supply:
        payload.setdefault("onchain", {})
        payload["onchain"]["token_supply"] = token_supply

    sentiment = _fetch_fear_greed()
    if sentiment:
        payload["sentiment"] = sentiment

    if include_macro:
        macro_data = load_macro_data()
        ff_calendar = _fetch_ff_calendar()
        te_calendar = _fetch_te_calendar()
        if ff_calendar:
            macro_data = _merge_calendar_items(macro_data or {}, ff_calendar)
        if te_calendar:
            macro_data = _merge_calendar_items(macro_data or {}, te_calendar)
        if macro_data:
            payload["macro"] = macro_data
        fred_series_raw = _env_or_config("NOFX_FRED_SERIES", "PAYEMS,CPIAUCSL,UNRATE,FEDFUNDS")
        fred_series = _split_symbols(fred_series_raw)
        fred_items = []
        if fred_series:
            for series_id in fred_series[:8]:
                item = _fetch_fred_series(series_id)
                if item:
                    fred_items.append(item)
        fred_releases = _fetch_fred_release_dates()
        if fred_items or fred_releases:
            payload["macro_fred"] = {}
            if fred_items:
                payload["macro_fred"]["series"] = fred_items
            if fred_releases:
                payload["macro_fred"]["upcoming"] = fred_releases.get("upcoming")
        gdelt = _fetch_gdelt_news()
        jin10_tg = _fetch_jin10_telegram_news(limit=100)
        merged_news = _merge_news_payloads(gdelt, jin10_tg)
        if gdelt:
            payload["macro_gdelt_raw"] = gdelt
        if jin10_tg:
            payload["macro_jin10"] = jin10_tg
        if merged_news:
            payload["macro_gdelt"] = merged_news
        focus = _build_macro_focus(
            payload.get("macro", {}) if isinstance(payload.get("macro"), dict) else {},
            payload.get("macro_fred") if isinstance(payload.get("macro_fred"), dict) else {},
            payload.get("macro_gdelt") if isinstance(payload.get("macro_gdelt"), dict) else {},
        )
        payload["economic_data"] = focus.get("economic_data", {})
        payload["major_events"] = focus.get("major_events", {})
        payload["major_policies"] = focus.get("major_policies", {})
        payload["macro_brief"] = build_macro_brief(max_items=5)

    _cache_set(cache_key, payload)
    return payload


def fetch_macro_snapshot(ttl_sec: Optional[int] = None) -> Dict[str, Any]:
    ttl = int(ttl_sec or os.getenv("NOFX_FUNDAMENTALS_TTL_SEC", "600") or 600)
    cache_key = "macro"
    cached = _cache_get(cache_key, ttl)
    if cached is not None:
        return cached

    payload: Dict[str, Any] = {}
    macro_data = load_macro_data()
    ff_calendar = _fetch_ff_calendar()
    te_calendar = _fetch_te_calendar()
    if ff_calendar:
        macro_data = _merge_calendar_items(macro_data or {}, ff_calendar)
    if te_calendar:
        macro_data = _merge_calendar_items(macro_data or {}, te_calendar)
    if macro_data:
        payload["macro"] = macro_data

    fred_series_raw = _env_or_config("NOFX_FRED_SERIES", "PAYEMS,CPIAUCSL,UNRATE,FEDFUNDS")
    fred_series = _split_symbols(fred_series_raw)
    fred_items = []
    if fred_series:
        for series_id in fred_series[:8]:
            item = _fetch_fred_series(series_id)
            if item:
                fred_items.append(item)
    fred_releases = _fetch_fred_release_dates()
    if fred_items or fred_releases:
        payload["macro_fred"] = {}
        if fred_items:
            payload["macro_fred"]["series"] = fred_items
        if fred_releases:
            payload["macro_fred"]["upcoming"] = fred_releases.get("upcoming")

    gdelt = _fetch_gdelt_news()
    jin10_tg = _fetch_jin10_telegram_news(limit=100)
    merged_news = _merge_news_payloads(gdelt, jin10_tg)
    if gdelt:
        payload["macro_gdelt_raw"] = gdelt
    if jin10_tg:
        payload["macro_jin10"] = jin10_tg
    if merged_news:
        payload["macro_gdelt"] = merged_news

    focus = _build_macro_focus(
        payload.get("macro", {}) if isinstance(payload.get("macro"), dict) else {},
        payload.get("macro_fred") if isinstance(payload.get("macro_fred"), dict) else {},
        payload.get("macro_gdelt") if isinstance(payload.get("macro_gdelt"), dict) else {},
    )
    payload["economic_data"] = focus.get("economic_data", {})
    payload["major_events"] = focus.get("major_events", {})
    payload["major_policies"] = focus.get("major_policies", {})

    _cache_set(cache_key, payload)
    return payload


def fetch_jin10_news_latest(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Fetch latest Jin10 news items.

    Returns:
        List of news items matching SCHEMAS_V3.md format:
        {
            "time": str (ISO 8601),
            "title": str,
            "content": str,
            "tags": [str],
            "importance": "high|medium|low",
            "source": "jin10"
        }
    """
    try:
        from signal_monitor.jin10_news import fetch_jin10_news
        return fetch_jin10_news(limit=limit)
    except Exception as exc:
        logger.error("Failed to fetch Jin10 news: %s", exc)
        return []


def fetch_econ_events_upcoming() -> List[Dict[str, Any]]:
    """
    Fetch upcoming economic events.

    Returns:
        List of economic events matching SCHEMAS_V3.md format:
        {
            "name": str,
            "country": str,
            "importance": "high|medium|low",
            "time": str (ISO 8601),
            "previous": float,
            "forecast": float,
            "actual": float,
            "description": str
        }
    """
    macro = fetch_macro_snapshot()
    calendar_items = _extract_macro_items((macro.get("macro") or {}).get("calendar"))

    now = datetime.now(timezone.utc)
    upcoming = []

    for item in calendar_items:
        if not isinstance(item, dict):
            continue

        event_time = _parse_macro_time(item.get("date") or item.get("time"))
        if not event_time or event_time < now:
            continue

        name = _translate_macro_title(_safe_text(
            item.get("title") or item.get("event") or item.get("name") or ""
        ))
        if not name:
            continue

        upcoming.append({
            "name": name,
            "country": item.get("country") or "US",
            "importance": str(item.get("importance") or item.get("impact") or "medium").lower(),
            "time": event_time.isoformat(),
            "previous": item.get("previous"),
            "forecast": item.get("forecast") or item.get("consensus"),
            "actual": item.get("actual"),
            "description": _safe_text(item.get("description") or "")
        })

    return upcoming[:50]


def fetch_econ_events_history(days: int = 7) -> List[Dict[str, Any]]:
    """
    Fetch historical economic events.

    Args:
        days: Number of days to look back

    Returns:
        List of economic events matching SCHEMAS_V3.md format
    """
    macro = fetch_macro_snapshot()
    recent_items = _extract_macro_items((macro.get("macro") or {}).get("recent_releases"))

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)
    history = []

    for item in recent_items:
        if not isinstance(item, dict):
            continue

        event_time = _parse_macro_time(item.get("date") or item.get("time"))
        if not event_time or event_time < cutoff or event_time > now:
            continue

        name = _translate_macro_title(_safe_text(
            item.get("title") or item.get("event") or item.get("name") or ""
        ))
        if not name:
            continue

        history.append({
            "name": name,
            "country": item.get("country") or "US",
            "importance": str(item.get("importance") or item.get("impact") or "medium").lower(),
            "time": event_time.isoformat(),
            "previous": item.get("previous"),
            "forecast": item.get("forecast") or item.get("consensus"),
            "actual": item.get("actual"),
            "description": _safe_text(item.get("description") or "")
        })

    return history[:50]
