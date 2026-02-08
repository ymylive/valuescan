"""
External data source helpers (public API endpoints).
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict, Optional

import requests

try:
    from signal_monitor.logger import logger
except Exception:
    from logger import logger


NOFX_API_BASE = os.getenv("NOFX_API_BASE", "https://nofxai.com/data").strip().rstrip("/")
NOFX_API_TOKEN = os.getenv("NOFX_API_TOKEN", "").strip()

try:
    NOFX_API_TIMEOUT = float(os.getenv("NOFX_API_TIMEOUT", "10"))
except ValueError:
    NOFX_API_TIMEOUT = 10.0

try:
    NOFX_API_CACHE_TTL = int(os.getenv("NOFX_API_CACHE_TTL", "60"))
except ValueError:
    NOFX_API_CACHE_TTL = 60

_session = requests.Session()
_cache: Dict[str, Dict[str, Any]] = {}


def _cache_get(key: str) -> Optional[Any]:
    entry = _cache.get(key)
    if not entry:
        return None
    if time.time() - entry["ts"] > NOFX_API_CACHE_TTL:
        return None
    return entry["data"]


def _cache_set(key: str, data: Any) -> None:
    _cache[key] = {"ts": time.time(), "data": data}


def _build_headers() -> Dict[str, str]:
    headers = {"Accept": "application/json"}
    if NOFX_API_TOKEN:
        headers["Authorization"] = f"Bearer {NOFX_API_TOKEN}"
    return headers


def _fetch_json(path: str, params: Optional[Dict[str, Any]] = None) -> Optional[Any]:
    if not NOFX_API_BASE:
        return None
    cache_key = path
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    url = f"{NOFX_API_BASE}{path}"
    try:
        resp = _session.get(url, params=params, headers=_build_headers(), timeout=NOFX_API_TIMEOUT)
        if resp.status_code == 200:
            data = resp.json()
            _cache_set(cache_key, data)
            return data
        logger.warning("Data source request failed (%s) for %s", resp.status_code, path)
    except Exception as exc:
        logger.debug("Data source request error: %s", type(exc).__name__)
    return None


def _apply_limit(payload: Dict[str, Any], list_key: str, limit: Optional[int]) -> Dict[str, Any]:
    if not limit:
        return payload
    items = payload.get(list_key)
    if not isinstance(items, list):
        return payload
    sliced = items[: max(0, limit)]
    out = dict(payload)
    out[list_key] = sliced
    if "count" in out:
        out["count"] = len(sliced)
    else:
        out["count"] = len(sliced)
    return out


def fetch_nofx_competition(limit: Optional[int] = None) -> Optional[Dict[str, Any]]:
    payload = _fetch_json("/api/competition")
    if not isinstance(payload, dict):
        return None
    return _apply_limit(payload, "traders", limit)


def fetch_nofx_top_traders(limit: Optional[int] = None) -> Optional[Dict[str, Any]]:
    payload = _fetch_json("/api/top-traders")
    if not isinstance(payload, dict):
        return None
    return _apply_limit(payload, "traders", limit)


def fetch_nofx_public_strategies(limit: Optional[int] = None) -> Optional[Dict[str, Any]]:
    payload = _fetch_json("/api/strategies/public")
    if not isinstance(payload, dict):
        return None
    return _apply_limit(payload, "strategies", limit)
