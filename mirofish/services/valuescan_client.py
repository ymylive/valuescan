from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional

from ..config import Config
from ..utils.logger import get_logger

logger = get_logger("mirofish.valuescan")


def _build_url(path: str, params: Optional[Dict[str, Any]] = None) -> str:
    base = (Config.VALUESCAN_BASE_URL or "").rstrip("/")
    path = path.lstrip("/")
    url = f"{base}/{path}"
    if params:
        query = urllib.parse.urlencode(params)
        url = f"{url}?{query}"
    return url


def _fetch_json(path: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    url = _build_url(path, params)
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=Config.VALUESCAN_TIMEOUT) as resp:
            if resp.status != 200:
                logger.warning("ValueScan request failed: %s - %s", resp.status, url)
                return None
            body = resp.read().decode("utf-8")
            data = json.loads(body)
            return data if isinstance(data, dict) else None
    except Exception as exc:
        logger.warning("ValueScan request error: %s (%s)", url, exc)
        return None


def _extract_data(payload: Optional[Dict[str, Any]]) -> Optional[Any]:
    if not isinstance(payload, dict):
        return None
    if payload.get("success") is False:
        return None
    return payload.get("data")


def fetch_valuescan_bundle(symbol: str = "BTC") -> Dict[str, Any]:
    symbol = symbol.upper().replace("$", "").replace("USDT", "").strip()
    bundle: Dict[str, Any] = {"symbol": symbol}

    bundle["market_snapshot"] = _extract_data(_fetch_json(f"market/snapshot/{symbol}"))
    bundle["fundamentals"] = _extract_data(_fetch_json(f"fundamentals/{symbol}", {"include_macro": 1}))
    bundle["news"] = _extract_data(_fetch_json("market/news", {"limit": 12}))
    bundle["trending"] = _extract_data(_fetch_json("market/trending", {"limit": 8}))
    bundle["btc_forecast"] = _extract_data(_fetch_json("market/btc-forecast"))

    return bundle
