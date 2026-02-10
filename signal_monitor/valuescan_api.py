#!/usr/bin/env python3
"""
ValueScan API helpers for token detail data and dense area levels.
"""

import json
import os
import time
import ssl
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
import socket
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager

try:
    from .logger import logger
except Exception:
    try:
        from logger import logger
    except Exception:
        logger = None  # type: ignore[assignment]


BASE_URL = os.getenv("VALUESCAN_API_BASE", "https://api.valuescan.io").rstrip("/")
DEFAULT_LOCALSTORAGE = Path(
    os.getenv("VALUESCAN_TOKEN_FILE") or (Path(__file__).parent / "valuescan_localstorage.json")
)
DEFAULT_COOKIES = Path(
    os.getenv("VALUESCAN_COOKIES_FILE") or (Path(__file__).parent / "valuescan_cookies.json")
)
DEFAULT_ORIGIN = "https://www.valuescan.io"
ACCESS_TICKET_FALLBACK = (os.getenv("VALUESCAN_ACCESS_TICKET_FALLBACK") or "LNe1VTyHk0bij3cyWB2gxg==").strip()

_CACHE_TTL_SEC = 120
DEFAULT_DENSE_DAYS = int(os.getenv("VALUESCAN_KEY_LEVELS_DAYS", "15") or 15)
_keyword_cache: Dict[str, Dict[str, Any]] = {}
_dense_cache: Dict[str, Dict[str, Any]] = {}
_hold_cost_cache: Dict[int, Dict[str, Any]] = {}


def _force_ipv4() -> None:
    if os.getenv("VALUESCAN_FORCE_IPV4", "1").lower() not in ("1", "true", "yes", "on"):
        return
    try:
        import urllib3.util.connection as urllib3_cn
        urllib3_cn.allowed_gai_family = lambda: socket.AF_INET
    except Exception as exc:
        _log("warning", "[ValueScan] Failed to force IPv4: %s", exc)


_force_ipv4()


def _now() -> float:
    return time.time()


def _log(level: str, msg: str, *args: Any) -> None:
    if logger:
        getattr(logger, level, logger.info)(msg, *args)


def _load_localstorage(path: Optional[Path] = None) -> Dict[str, Any]:
    target = path or DEFAULT_LOCALSTORAGE
    if not target or not target.exists():
        return {}
    try:
        return json.loads(target.read_text(encoding="utf-8"))
    except Exception as exc:
        _log("warning", "[ValueScan] Failed to read localstorage: %s", exc)
        return {}


def _load_cookies(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    target = path or DEFAULT_COOKIES
    if not target or not target.exists():
        return []
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except Exception as exc:
        _log("warning", "[ValueScan] Failed to read cookies: %s", exc)
        return []
    cookies: Optional[List[Any]] = None
    if isinstance(payload, list):
        cookies = payload
    elif isinstance(payload, dict):
        if isinstance(payload.get("cookies"), list):
            cookies = payload.get("cookies")
        elif isinstance(payload.get("data"), list):
            cookies = payload.get("data")
    if not isinstance(cookies, list):
        return []
    return [item for item in cookies if isinstance(item, dict)]


def _cookie_header_value(cookies: List[Dict[str, Any]]) -> str:
    pairs: List[str] = []
    for cookie in cookies:
        name = cookie.get("name") or cookie.get("Name")
        if not isinstance(name, str) or not name.strip():
            continue
        value = cookie.get("value") if "value" in cookie else cookie.get("Value")
        if value is None:
            continue
        pairs.append(f"{name.strip()}={str(value)}")
    return "; ".join(pairs)


def _extract_token(localstorage: Dict[str, Any]) -> str:
    token = (
        localstorage.get("account_token")
        or localstorage.get("accessToken")
        or localstorage.get("token")
        or ""
    )
    if isinstance(token, str):
        return token.strip()
    return ""


def _extract_access_ticket(localstorage: Dict[str, Any]) -> str:
    keys = ("access_ticket", "accessTicket", "accessTicketValue", "access-ticket")
    for key in keys:
        val = localstorage.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    if isinstance(localstorage.get("data"), dict):
        nested = localstorage["data"]
        for key in keys:
            val = nested.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
    return ACCESS_TICKET_FALLBACK


def _auth_headers(token: str, access_ticket: str, cookie_header: str = "") -> Dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Origin": DEFAULT_ORIGIN,
        "Referer": f"{DEFAULT_ORIGIN}/",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if access_ticket:
        headers["Access-Ticket"] = access_ticket
    if cookie_header:
        headers["Cookie"] = cookie_header
    return headers


def _get_valuescan_proxies() -> Optional[Dict[str, str]]:
    proxy_url = (
        os.getenv("VALUESCAN_API_PROXY")
        or os.getenv("VALUESCAN_PROXY")
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
        return None
    return {"http": proxy_url, "https": proxy_url}


class _TLS12Adapter(HTTPAdapter):
    def __init__(self, verify: bool) -> None:
        self._verify = bool(verify)
        super().__init__()

    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        ctx = ssl.create_default_context()
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        ctx.maximum_version = ssl.TLSVersion.TLSv1_2
        if not self._verify:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        self.poolmanager = PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            ssl_context=ctx,
        )


def build_valuescan_session(verify: bool) -> requests.Session:
    session = requests.Session()
    force_tls12 = os.getenv("VALUESCAN_API_FORCE_TLS12", "1").lower() in ("1", "true", "yes", "on")
    if force_tls12:
        try:
            session.mount("https://", _TLS12Adapter(verify))
        except Exception as exc:
            _log("warning", "[ValueScan] TLS12 adapter init failed: %s", exc)
    return session


def build_valuescan_headers() -> Dict[str, str]:
    """Build ValueScan API auth headers from localstorage/token info."""
    localstorage = _load_localstorage()
    token = _extract_token(localstorage)
    access_ticket = _extract_access_ticket(localstorage)
    cookie_header = _cookie_header_value(_load_cookies())
    return _auth_headers(token, access_ticket, cookie_header)


def get_valuescan_base_url() -> str:
    return BASE_URL


def get_valuescan_proxies() -> Optional[Dict[str, str]]:
    return _get_valuescan_proxies()


def _post(path: str, payload: Any, token: Optional[str] = None) -> Optional[Dict[str, Any]]:
    _force_ipv4()
    localstorage = _load_localstorage()
    token = (token or _extract_token(localstorage)).strip()
    access_ticket = _extract_access_ticket(localstorage)
    if not token:
        _log("warning", "[ValueScan] Missing token for %s, trying access ticket only", path)
    cookie_header = _cookie_header_value(_load_cookies())
    url = f"{BASE_URL}{path}"
    max_retries = int(os.getenv("VALUESCAN_API_RETRY", "3") or 3)
    timeout_sec = float(os.getenv("VALUESCAN_API_TIMEOUT", "15") or 15)
    connect_timeout = float(os.getenv("VALUESCAN_API_CONNECT_TIMEOUT", "8") or 8)
    verify = os.getenv("VALUESCAN_API_VERIFY", "1").lower() not in ("0", "false", "no", "off")
    proxies = _get_valuescan_proxies()
    use_env_proxy = os.getenv("VALUESCAN_API_TRUST_ENV", "0").lower() in ("1", "true", "yes", "on")
    for attempt in range(max_retries + 1):
        try:
            session = build_valuescan_session(verify)
            session.trust_env = bool(use_env_proxy and not proxies)
            resp = session.post(
                url,
                headers=_auth_headers(token, access_ticket, cookie_header),
                json=payload,
                timeout=(connect_timeout, timeout_sec),
                proxies=proxies,
                verify=verify,
            )
        except Exception as exc:
            if attempt < max_retries:
                time.sleep(0.6 + attempt * 0.6)
                continue
            _log("warning", "[ValueScan] Request failed %s: %s", path, exc)
            return None
        try:
            return resp.json()
        except Exception as exc:
            if attempt < max_retries:
                time.sleep(0.6 + attempt * 0.6)
                continue
            _log("warning", "[ValueScan] Bad JSON for %s: %s", path, exc)
            return None


def _get(path: str, params: Optional[Dict[str, Any]] = None, token: Optional[str] = None) -> Optional[Dict[str, Any]]:
    _force_ipv4()
    localstorage = _load_localstorage()
    token = (token or _extract_token(localstorage)).strip()
    access_ticket = _extract_access_ticket(localstorage)
    if not token:
        _log("warning", "[ValueScan] Missing token for %s, trying access ticket only", path)
    cookie_header = _cookie_header_value(_load_cookies())
    url = f"{BASE_URL}{path}"
    max_retries = int(os.getenv("VALUESCAN_API_RETRY", "3") or 3)
    timeout_sec = float(os.getenv("VALUESCAN_API_TIMEOUT", "15") or 15)
    connect_timeout = float(os.getenv("VALUESCAN_API_CONNECT_TIMEOUT", "8") or 8)
    verify = os.getenv("VALUESCAN_API_VERIFY", "1").lower() not in ("0", "false", "no", "off")
    proxies = _get_valuescan_proxies()
    use_env_proxy = os.getenv("VALUESCAN_API_TRUST_ENV", "0").lower() in ("1", "true", "yes", "on")
    for attempt in range(max_retries + 1):
        try:
            session = build_valuescan_session(verify)
            session.trust_env = bool(use_env_proxy and not proxies)
            resp = session.get(
                url,
                headers=_auth_headers(token, access_ticket, cookie_header),
                params=params,
                timeout=(connect_timeout, timeout_sec),
                proxies=proxies,
                verify=verify,
            )
        except Exception as exc:
            if attempt < max_retries:
                time.sleep(0.6 + attempt * 0.6)
                continue
            _log("warning", "[ValueScan] Request failed %s: %s", path, exc)
            return None
        try:
            return resp.json()
        except Exception as exc:
            if attempt < max_retries:
                time.sleep(0.6 + attempt * 0.6)
                continue
            _log("warning", "[ValueScan] Bad JSON for %s: %s", path, exc)
            return None


def _normalize_symbol(symbol: str) -> str:
    return str(symbol or "").upper().replace("$", "").replace("USDT", "").strip()


def _parse_token_history(localstorage: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw = localstorage.get("token_history")
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    if isinstance(raw, str):
        try:
            data = json.loads(raw)
        except Exception:
            return []
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
    return []


def _parse_query_list(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    if data.get("code") != 200:
        return []
    container = data.get("data") or {}
    items = container.get("list")
    if isinstance(items, list):
        return [item for item in items if isinstance(item, dict)]
    return []


def query_coin(keyword: str) -> List[Dict[str, Any]]:
    payload = {"search": keyword, "page": 1, "pageSize": 20}
    data = _post("/api/vs-token/queryCoin", payload) or {}
    items = _parse_query_list(data)
    if items:
        return items
    fallback = _post("/api/vs-token/queryCoin", {"keyword": keyword}) or {}
    return _parse_query_list(fallback)


def resolve_keyword(symbol: str) -> Optional[int]:
    normalized = _normalize_symbol(symbol)
    if not normalized:
        return None

    cached = _keyword_cache.get(normalized)
    if cached and _now() - cached["ts"] < _CACHE_TTL_SEC:
        return cached["value"]

    localstorage = _load_localstorage()
    for item in _parse_token_history(localstorage):
        if str(item.get("symbol", "")).upper() == normalized:
            keyword = item.get("keyword") or item.get("vsTokenId")
            try:
                value = int(float(keyword))
            except Exception:
                value = None
            if value:
                _keyword_cache[normalized] = {"value": value, "ts": _now()}
                return value

    items = query_coin(normalized)
    match = None
    for item in items:
        if str(item.get("symbol", "")).upper() == normalized:
            match = item
            break
    if not match:
        return None
    keyword = match.get("vsTokenId") or match.get("keyword")
    try:
        value = int(float(keyword))
    except Exception:
        return None
    _keyword_cache[normalized] = {"value": value, "ts": _now()}
    return value


def _point_time_ms(point: Dict[str, Any]) -> int:
    if not isinstance(point, dict):
        return 0
    for key in (
        "time",
        "ts",
        "timestamp",
        "dateTime",
        "date",
        "createTime",
        "create_time",
        "updateTime",
        "update_time",
        "timeStamp",
    ):
        value = point.get(key)
        if value is None:
            continue
        try:
            ts = int(float(value))
        except Exception:
            if isinstance(value, str):
                text = value.strip().replace("Z", "+00:00")
                dt = None
                try:
                    dt = datetime.fromisoformat(text)
                except Exception:
                    for fmt in (
                        "%Y-%m-%d %H:%M:%S",
                        "%Y-%m-%d %H:%M",
                        "%Y/%m/%d %H:%M:%S",
                        "%Y/%m/%d %H:%M",
                        "%Y-%m-%d",
                        "%Y/%m/%d",
                    ):
                        try:
                            dt = datetime.strptime(text, fmt)
                            break
                        except Exception:
                            continue
                if dt:
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return int(dt.timestamp() * 1000)
            continue
        if ts <= 0:
            continue
        return ts if ts > 10**12 else ts * 1000
    return 0


def _filter_points_by_days(points: List[Dict[str, Any]], days: int) -> List[Dict[str, Any]]:
    if days <= 0:
        return points
    cutoff_ms = int(_now() * 1000) - days * 24 * 60 * 60 * 1000
    return [p for p in points if _point_time_ms(p) >= cutoff_ms]


def _extract_data(resp: Optional[Dict[str, Any]]) -> Optional[Any]:
    if not isinstance(resp, dict):
        return None
    if resp.get("code") != 200:
        return None
    return resp.get("data")


def _extract_dense_points(resp: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not isinstance(resp, dict):
        return []
    data = resp.get("data")
    if isinstance(data, list):
        if data and isinstance(data[0], (list, tuple)) and len(data[0]) >= 2:
            converted = []
            for row in data:
                if not isinstance(row, (list, tuple)) or len(row) < 2:
                    continue
                converted.append({"time": row[0], "price": row[1]})
            return converted
        return data
    if isinstance(data, dict):
        for key in ("list", "records", "items", "history", "historyList", "kline", "klineList", "bars"):
            if isinstance(data.get(key), list):
                return data.get(key) or []
    return []


def _dense_point_price(item: Dict[str, Any]) -> Optional[float]:
    if not isinstance(item, dict):
        return None
    for key in (
        "price",
        "levelPrice",
        "val",
        "value",
        "cost",
        "priceLevel",
        "avgPrice",
        "priceAvg",
        "costPrice",
        "avg_cost",
        "close",
        "last",
    ):
        value = item.get(key)
        if value is None:
            continue
        try:
            return float(value)
        except Exception:
            continue
    low = item.get("low") or item.get("minPrice") or item.get("priceMin")
    high = item.get("high") or item.get("maxPrice") or item.get("priceMax")
    if low is not None and high is not None:
        try:
            return (float(low) + float(high)) / 2
        except Exception:
            pass
    text = item.get("priceRange") or item.get("range") or ""
    if isinstance(text, str) and "-" in text:
        parts = [p.strip() for p in text.split("-", 1)]
        if len(parts) == 2:
            try:
                low = float(parts[0])
                high = float(parts[1])
                return (low + high) / 2
            except Exception:
                return None
    return None


def _dedupe_levels(levels: List[float], precision: int = 6) -> List[float]:
    seen = set()
    out: List[float] = []
    for value in levels:
        try:
            price = float(value)
        except Exception:
            continue
        key = round(price, precision)
        if key in seen:
            continue
        seen.add(key)
        out.append(price)
    return out


def _merge_close_levels(levels: List[float], threshold_pct: float = 0.5) -> List[Dict[str, Any]]:
    """
    合并相近的主力位为密集区，标记为强主力位。
    当2-3个主力位价格差距在threshold_pct%以内时，合并为一个密集区。

    Args:
        levels: 主力位价格列表
        threshold_pct: 合并阈值百分比，默认0.5%

    Returns:
        合并后的主力位列表，每个元素包含:
        - price: 价格（密集区取中间值）
        - is_strong: 是否为强主力位（密集区）
        - merged_count: 合并的主力位数量
        - range: 密集区价格范围 [min, max]（仅密集区有）
    """
    if not levels:
        return []

    sorted_levels = sorted(levels)
    result: List[Dict[str, Any]] = []
    i = 0

    while i < len(sorted_levels):
        current = sorted_levels[i]
        cluster = [current]

        # 查找相近的主力位
        j = i + 1
        while j < len(sorted_levels):
            next_level = sorted_levels[j]
            # 计算与cluster中最后一个价格的差距百分比
            diff_pct = abs(next_level - cluster[-1]) / cluster[-1] * 100
            if diff_pct <= threshold_pct:
                cluster.append(next_level)
                j += 1
            else:
                break

        if len(cluster) >= 2:
            # 2个或以上相近主力位，合并为密集区（强主力位）
            avg_price = sum(cluster) / len(cluster)
            result.append({
                "price": avg_price,
                "is_strong": True,
                "merged_count": len(cluster),
                "range": [min(cluster), max(cluster)],
            })
        else:
            # 单独的主力位
            result.append({
                "price": current,
                "is_strong": False,
                "merged_count": 1,
            })

        i = j

    return result


def _fetch_symbol_price(symbol: str) -> Optional[float]:
    items = query_coin(symbol)
    target = None
    for item in items:
        if str(item.get("symbol", "")).upper() == _normalize_symbol(symbol):
            target = item
            break
    if not target:
        return None
    try:
        return float(target.get("price", 0) or 0)
    except Exception:
        return None


def get_dense_area(keyword: int, days: int = DEFAULT_DENSE_DAYS) -> Optional[Dict[str, Any]]:
    cache_key = f"{keyword}:{days}"
    cached = _dense_cache.get(cache_key)
    if cached and _now() - cached["ts"] < _CACHE_TTL_SEC:
        return cached["value"]

    end_ms = int(_now() * 1000)
    begin_ms = end_ms - days * 24 * 60 * 60 * 1000
    payload = {
        "vsTokenId": str(keyword),
        "beginTime": begin_ms,
        "endTime": end_ms,
    }
    resp = _post("/api/dense/getDenseAreaKLineHistory", payload) or {}
    if resp.get("code") == 200 and resp.get("data"):
        _dense_cache[cache_key] = {"value": resp, "ts": _now()}
        return resp

    fallback = _post(
        "/api/dense/getDenseAreaKLineHistory",
        {"beginTime": begin_ms, "endTime": end_ms},
    )
    if isinstance(fallback, dict):
        _dense_cache[cache_key] = {"value": fallback, "ts": _now()}
    return fallback or resp


def get_main_force(symbol: str, days: int = DEFAULT_DENSE_DAYS) -> Dict[str, Any]:
    keyword = resolve_keyword(symbol)
    if not keyword:
        return {"code": 404, "error": f"Coin '{symbol}' not found"}

    last_resp: Dict[str, Any] = {"code": 500, "error": "No dense area data"}
    last_points: List[Dict[str, Any]] = []

    candidate_days = [days, max(days * 2, 30), 60, 90]
    seen = set()
    for window in candidate_days:
        if window in seen:
            continue
        seen.add(window)
        resp = get_dense_area(keyword, window) or {}
        last_resp = resp
        if resp.get("code") != 200:
            continue
        points = _extract_dense_points(resp)
        if not points:
            continue
        points_sorted = sorted(points, key=_point_time_ms)
        last_points = points_sorted
        has_timestamp = any(_point_time_ms(point) > 0 for point in points_sorted)
        if not has_timestamp and len(points_sorted) >= 1:
            return {"code": 200, "data": points_sorted}

        filtered = _filter_points_by_days(points_sorted, days)
        if len(filtered) >= 1:
            return {"code": 200, "data": filtered}

        widened = _filter_points_by_days(points_sorted, window)
        if len(widened) >= 1:
            return {"code": 200, "data": widened}

    if len(last_points) >= 1:
        return {"code": 200, "data": last_points[-7:]}
    if isinstance(last_resp, dict):
        return last_resp
    return {"code": 500, "error": "No dense area data"}


def get_hold_cost(keyword: int, days: int = 90) -> Optional[Dict[str, Any]]:
    cached = _hold_cost_cache.get(keyword)
    if cached and _now() - cached["ts"] < _CACHE_TTL_SEC:
        return cached["value"]

    end_ms = int(_now() * 1000)
    begin_ms = end_ms - days * 24 * 60 * 60 * 1000
    data = _post(
        "/api/track/judge/coin/getHoldCost",
        {"keyword": keyword, "begin": begin_ms, "end": end_ms},
    ) or {}
    if data.get("code") != 200:
        return None
    payload = data.get("data")
    if not isinstance(payload, dict):
        return None
    _hold_cost_cache[keyword] = {"value": payload, "ts": _now()}
    return payload


def get_valuescan_key_levels(
    symbol: str,
    current_price: Optional[float] = None,
    days: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    dense_days = days if days is not None else DEFAULT_DENSE_DAYS
    resp = get_main_force(symbol, days=dense_days)
    if resp.get("code") != 200:
        return None
    points = resp.get("data") or []
    if not isinstance(points, list) or not points:
        return None
    type_values = {item.get("type") for item in points if isinstance(item, dict) and item.get("type") is not None}
    if type_values and 2 in type_values:
        filtered_points = [item for item in points if isinstance(item, dict) and item.get("type") == 2]
        if filtered_points:
            points = filtered_points

    points_sorted = sorted(points, key=_point_time_ms)
    recent_points = points_sorted
    levels: List[float] = []
    for item in recent_points:
        price = _dense_point_price(item)
        if price is None:
            continue
        levels.append(price)
    if not levels:
        return None

    levels = _dedupe_levels(levels)

    # 合并相近主力位为密集区（强主力位）
    merged_levels = _merge_close_levels(levels, threshold_pct=0.5)

    # 提取价格列表和强主力位信息
    final_levels = [item["price"] for item in merged_levels]
    strong_levels = [item for item in merged_levels if item.get("is_strong")]

    return {
        "levels": final_levels,
        "merged_levels": merged_levels,  # 包含完整合并信息
        "strong_levels": strong_levels,  # 强主力位（密集区）
        "supports": [],
        "resistances": [],
        "meta": {
            "source": "VS",
            "mode": "window",
            "days": dense_days,
            "count": len(final_levels),
            "strong_count": len(strong_levels),
        },
    }


def list_prices(token_ids: List[int]) -> Dict[str, Any]:
    if not token_ids:
        return {}
    payload = [int(item) for item in token_ids if str(item).strip()]
    data = _post("/api/vs-token/listPrice", payload) or {}
    if data.get("code") != 200:
        return {}
    prices = data.get("data")
    if isinstance(prices, dict):
        return prices
    return {}


def get_exchange_coin_info(keyword: int) -> Optional[Dict[str, Any]]:
    data = _get("/api/track/judge/getExchangeCoinInfo", {"keyword": keyword}) or {}
    if data.get("code") != 200:
        return None
    payload = data.get("data")
    return payload if isinstance(payload, dict) else None


def get_coin_trade_inflow(keyword: int) -> Optional[Dict[str, Any]]:
    data = _get("/api/trade/getCoinTradeInflow", {"keyword": keyword}) or {}
    if data.get("code") != 200:
        return None
    payload = data.get("data")
    return payload if isinstance(payload, dict) else None


def get_ai_coin_summarize(keyword: int) -> Optional[Dict[str, Any]]:
    data = _get("/api/ai/getAiCoinSummarize", {"vsTokenId": keyword}) or {}
    if data.get("code") != 200:
        return None
    payload = data.get("data")
    return payload if isinstance(payload, dict) else None


def get_trade_coin_kline(keyword: int) -> List[Dict[str, Any]]:
    data = _get("/api/track/judge/getTradeCoinKline", {"keyword": keyword}) or {}
    if data.get("code") != 200:
        return []
    payload = data.get("data")
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []


def get_kline_history(
    trade_pairs: str,
    kline_type: str,
    bucket_type: str,
    size: int = 300,
) -> Optional[Dict[str, Any]]:
    if not trade_pairs:
        return None
    payload = {
        "tradePairs": trade_pairs,
        "klineType": kline_type,
        "bucketType": bucket_type,
        "size": size,
    }
    data = _post("/api/kline/history", payload) or {}
    if data.get("code") != 200:
        return None
    return data


def get_kline_miss(
    trade_pairs: str,
    kline_type: str,
    start_ms: int,
) -> Optional[List[List[Any]]]:
    if not trade_pairs:
        return None
    payload = {
        "tradePairs": trade_pairs,
        "klineType": kline_type,
        "start": int(start_ms),
    }
    data = _post("/api/kline/missQuery", payload) or {}
    if data.get("code") != 200:
        return None
    points = data.get("data")
    return points if isinstance(points, list) else None


def get_fund_trade_history_total(
    keyword: int,
    flow: bool,
    trade_type: int = 2,
    time_particle: str = "12h",
    limit_size: int = 100,
) -> Optional[List[Dict[str, Any]]]:
    payload = {
        "timeParticle": time_particle,
        "limitSize": limit_size,
        "flow": bool(flow),
        "keyword": int(keyword),
        "type": int(trade_type),
    }
    data = _post("/api/trade/fundTradeHistoryTotal", payload) or {}
    if data.get("code") != 200:
        return None
    rows = data.get("data")
    if isinstance(rows, list):
        return [item for item in rows if isinstance(item, dict)]
    return None


def _select_trade_pair(entries: List[Dict[str, Any]], preferred: str = "01") -> Optional[Dict[str, str]]:
    for item in entries:
        if str(item.get("klineType", "")).strip() == preferred:
            trade_pairs = str(item.get("tradePairs") or "").strip()
            if trade_pairs:
                return {"tradePairs": trade_pairs, "klineType": preferred}
    for item in entries:
        trade_pairs = str(item.get("tradePairs") or "").strip()
        kline_type = str(item.get("klineType") or "").strip()
        if trade_pairs and kline_type:
            return {"tradePairs": trade_pairs, "klineType": kline_type}
    return None


def _trade_type_label(trade_type: int) -> str:
    return "spot" if int(trade_type) == 1 else "contract"


def get_token_detail(
    symbol: str,
    keyword: Optional[int] = None,
    bucket_type: str = "1h",
    kline_size: int = 300,
    kline_miss_start: Optional[int] = None,
    fund_time_particle: str = "12h",
    fund_limit_size: int = 100,
    fund_trade_type: Optional[int] = None,
) -> Dict[str, Any]:
    resolved = int(keyword) if keyword else resolve_keyword(symbol) or 0
    if resolved <= 0:
        return {"symbol": symbol, "keyword": None, "error": "keyword_not_found"}

    result: Dict[str, Any] = {"symbol": symbol, "keyword": resolved}
    result["coin_info"] = get_exchange_coin_info(resolved)
    result["prices"] = list_prices([resolved])
    result["trade_inflow"] = get_coin_trade_inflow(resolved)
    result["ai_summary"] = get_ai_coin_summarize(resolved)
    result["dense_area"] = get_dense_area(resolved)
    trade_types = [int(fund_trade_type)] if fund_trade_type is not None else [1, 2]
    flow_history: Dict[str, Optional[List[Dict[str, Any]]]] = {}
    volume_history: Dict[str, Optional[List[Dict[str, Any]]]] = {}
    for trade_type in trade_types:
        label = _trade_type_label(trade_type)
        flow_history[label] = get_fund_trade_history_total(
            resolved,
            flow=True,
            trade_type=trade_type,
            time_particle=fund_time_particle,
            limit_size=fund_limit_size,
        )
        volume_history[label] = get_fund_trade_history_total(
            resolved,
            flow=False,
            trade_type=trade_type,
            time_particle=fund_time_particle,
            limit_size=fund_limit_size,
        )
    result["fund_flow_history"] = flow_history
    result["fund_volume_history"] = volume_history

    trade_entries = get_trade_coin_kline(resolved)
    selected = _select_trade_pair(trade_entries)
    result["trade_pairs"] = selected["tradePairs"] if selected else None
    result["kline_type"] = selected["klineType"] if selected else None
    result["kline"] = None
    result["kline_miss"] = None
    if selected:
        result["kline"] = get_kline_history(
            selected["tradePairs"],
            selected["klineType"],
            bucket_type=bucket_type,
            size=kline_size,
        )
        if kline_miss_start is not None:
            result["kline_miss"] = get_kline_miss(
                selected["tradePairs"],
                selected["klineType"],
                kline_miss_start,
            )
    return result


def get_ai_message_page(
    page: int = 1,
    page_size: int = 20,
    message_type: Optional[str] = "",
) -> Optional[Dict[str, Any]]:
    payload: Dict[str, Any] = {"page": page, "pageSize": page_size}
    if message_type is not None:
        payload["messageType"] = message_type
    return _extract_data(_post("/api/account/message/aiMessagePage", payload))


def get_message_history_page(
    page: int = 1,
    page_size: int = 20,
    message_type: str = "",
    order_column: str = "createTime",
    order_asc: bool = False,
    search_count: bool = True,
    vs_token_id: str = "",
    search: str = "",
) -> Optional[Dict[str, Any]]:
    payload = {
        "page": page,
        "pageSize": page_size,
        "order": [{"column": order_column, "asc": bool(order_asc)}],
        "messageType": message_type,
        "searchCount": bool(search_count),
        "vsTokenId": vs_token_id,
        "search": search,
    }
    return _extract_data(_post("/api/account/message/historyPage", payload))


def get_new_fear_greed() -> Optional[Any]:
    return _extract_data(_get("/api/account/message/getNewFearGreed"))


def get_exchange_notice() -> Optional[Any]:
    return _extract_data(_get("/api/account/message/getExchangeNotice"))


def get_heat_map(interval: str = "1h") -> Optional[Any]:
    return _extract_data(_get("/api/account/message/getHeatMap", {"interval": interval}))


def get_warn_message() -> Optional[Any]:
    return _extract_data(_get("/api/account/message/getWarnMessage"))


def get_version_info(payload: Optional[Dict[str, Any]] = None) -> Optional[Any]:
    return _extract_data(_post("/api/account/message/getVersionInfo", payload or {}))


def get_track_signal_page(
    page: int = 1,
    page_size: int = 20,
    signal_type: int = 0,
) -> Optional[Dict[str, Any]]:
    payload = {"page": page, "pageSize": page_size, "type": int(signal_type)}
    return _extract_data(_post("/api/track/signal/page", payload))


def get_track_industry_daily(payload: Optional[Dict[str, Any]] = None) -> Optional[Any]:
    return _extract_data(_post("/api/track/signal/industry/daily", payload or {}))


def get_exchange_assets_list() -> Optional[Any]:
    return _extract_data(_get("/api/analysis/coin/getExchangeAssetsList"))


def get_exchange_all_flow() -> Optional[Any]:
    return _extract_data(_get("/api/analysis/coin/getExchangeAllFlow"))


def get_funds_movement_page(
    page: int = 1,
    page_size: int = 20,
    trade_type: int = 2,
    order_column: str = "endTime",
    order_asc: bool = False,
    filters: Optional[List[Dict[str, Any]]] = None,
) -> Optional[Dict[str, Any]]:
    payload = {
        "page": page,
        "pageSize": page_size,
        "order": [{"column": order_column, "asc": bool(order_asc)}],
        "filters": filters or [],
        "tradeType": int(trade_type),
    }
    return _extract_data(_post("/api/chance/getFundsMovementPage", payload))


def get_funds_movement_update() -> Optional[Any]:
    return _extract_data(_get("/api/chance/getFundsMovementUpdate"))


def get_change_coin_page(
    page: int = 1,
    page_size: int = 20,
    order_column: str = "date",
    order_asc: bool = False,
    volumes: Optional[List[Any]] = None,
    inflows: Optional[List[Any]] = None,
    market_cap: bool = True,
    circulation_rate: bool = True,
) -> Optional[Dict[str, Any]]:
    payload = {
        "page": page,
        "pageSize": page_size,
        "order": {"column": order_column, "asc": bool(order_asc)},
        "volumes": volumes or [],
        "inflows": inflows or [],
        "marketCap": bool(market_cap),
        "circulationRate": bool(circulation_rate),
    }
    return _extract_data(_post("/api/chance/getChangeCoinPage", payload))


def get_change_coin_risk_page(
    page: int = 1,
    page_size: int = 20,
    order_column: str = "date",
    order_asc: bool = False,
    volumes: Optional[List[Any]] = None,
    inflows: Optional[List[Any]] = None,
    market_cap: bool = True,
    circulation_rate: bool = True,
) -> Optional[Dict[str, Any]]:
    payload = {
        "page": page,
        "pageSize": page_size,
        "order": {"column": order_column, "asc": bool(order_asc)},
        "volumes": volumes or [],
        "inflows": inflows or [],
        "marketCap": bool(market_cap),
        "circulationRate": bool(circulation_rate),
    }
    return _extract_data(_post("/api/chance/getChangeCoinRiskPage", payload))


def get_change_coin_update_time(chance_coin_type: Optional[int] = None) -> Optional[Any]:
    params = {"chanceCoinType": int(chance_coin_type)} if chance_coin_type is not None else None
    return _extract_data(_get("/api/chance/getChangeCoinUpdateTime", params))


def get_coin_custom_filter(filter_type: int = 1) -> Optional[Any]:
    return _extract_data(_get("/api/trade/coin/getCoinCustomFilter", {"type": int(filter_type)}))


def get_funds_movement_history_page(
    page: int = 1,
    page_size: int = 20,
    order_column: str = "gains",
    order_asc: bool = False,
) -> Optional[Dict[str, Any]]:
    payload = {
        "page": page,
        "pageSize": page_size,
        "order": [{"column": order_column, "asc": bool(order_asc)}],
    }
    return _extract_data(_post("/api/chance/getFundsMovementHistoryPage", payload))


def get_chance_coin_history_page(
    page: int = 1,
    page_size: int = 20,
    history_type: int = 1,
    order_column: str = "gains",
    order_asc: bool = False,
) -> Optional[Dict[str, Any]]:
    payload = {
        "page": page,
        "pageSize": page_size,
        "order": [{"column": order_column, "asc": bool(order_asc)}],
        "type": int(history_type),
    }
    return _extract_data(_post("/api/chance/chanceCoinHistoryPage", payload))


def get_trade_coin_top(trade_type: int = 1) -> Optional[Any]:
    return _extract_data(_get("/api/chance/getTradeCoinTop", {"type": int(trade_type)}))


def get_coin_rank(
    rank_type: int = 1,
    page: int = 1,
    page_size: int = 20,
    order: Optional[List[Dict[str, Any]]] = None,
) -> Optional[Dict[str, Any]]:
    if order is None:
        if int(rank_type) == 2:
            order = [
                {"column": "percentChange24h", "asc": True},
                {"column": "marketCap", "asc": False},
            ]
        else:
            order = [
                {"column": "percentChange24h", "asc": False},
                {"column": "marketCap", "asc": False},
            ]
    payload = {"page": page, "pageSize": page_size, "order": order, "type": int(rank_type)}
    return _extract_data(_post("/api/analysis/crypto/coin-rank", payload))


def get_quality_rank(
    page: int = 1,
    page_size: int = 20,
    order_column: str = "marketCap",
    order_asc: bool = False,
    filters: Optional[List[Dict[str, Any]]] = None,
) -> Optional[Dict[str, Any]]:
    payload = {
        "page": page,
        "pageSize": page_size,
        "order": [{"column": order_column, "asc": bool(order_asc)}],
        "filters": filters or [],
    }
    return _extract_data(_post("/api/analysis/coin/quality-rank", payload))


def get_coin_exchange_flow_page_time() -> Optional[Any]:
    return _extract_data(_get("/api/analysis/coin/getCoinExchangeFlowPageTime"))


def get_coin_exchange_flow_page(
    time: str = "H12",
    page: int = 1,
    page_size: int = 20,
    order_column: str = "inFlowValue",
    order_asc: bool = False,
    filters: Optional[List[Dict[str, Any]]] = None,
) -> Optional[Dict[str, Any]]:
    payload = {
        "page": page,
        "pageSize": page_size,
        "order": [{"column": order_column, "asc": bool(order_asc)}],
        "filters": filters or [],
        "time": time,
    }
    return _extract_data(_post("/api/analysis/coin/getCoinExchangeFlowPage", payload))


def get_coin_exchange_update_date(time_particle_enum: str = "H12") -> Optional[Any]:
    return _extract_data(
        _get("/api/analysis/coin/getCoinExchangeUpdateDate", {"timeParticleEnum": time_particle_enum})
    )


def get_trade_update_date(trade_type: int = 1) -> Optional[Any]:
    return _extract_data(_get("/api/trade/getTradeUpdateDate", {"type": int(trade_type)}))


def get_trade_page_time() -> Optional[Any]:
    return _extract_data(_get("/api/trade/getTradePageTime"))


def get_time_trade_page(payload: Dict[str, Any]) -> Optional[Any]:
    return _extract_data(_post("/api/trade/getTimeTradePage", payload))


def get_time_particle_trade_tag(trade_type: int = 1, payload: Optional[Dict[str, Any]] = None) -> Optional[Any]:
    path = f"/api/trade/timeParticleTradeTage?type={int(trade_type)}"
    return _extract_data(_post(path, payload or {}))


def get_max_inflow_market_cap(
    page: int = 1,
    page_size: int = 20,
    trade_type: int = 1,
    time_particle: int = 90,
    order_column: str = "percentValue",
    order_asc: bool = False,
) -> Optional[Dict[str, Any]]:
    payload = {
        "page": page,
        "pageSize": page_size,
        "order": [{"column": order_column, "asc": bool(order_asc)}],
        "tradeType": int(trade_type),
        "timeParticle": int(time_particle),
    }
    return _extract_data(_post("/api/trade/getMaxInflowMarketCap", payload))


def get_maintenance_notices() -> Optional[Any]:
    return _extract_data(_get("/api/system/config/status/getMaintenanceNotices"))


def page_system_announcements(payload: Dict[str, Any]) -> Optional[Any]:
    return _extract_data(_post("/api/system/announcements/pageSystemAnnouncements", payload))
