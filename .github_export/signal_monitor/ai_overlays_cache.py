#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
In-memory cache for AI-derived overlay lines (trendlines, channels, wedges, etc.).
"""
import threading
import time
from typing import Any, Dict, List, Optional

_CACHE: Dict[str, Dict[str, Any]] = {}
_LOCK = threading.Lock()


def _normalize_symbol(symbol: str) -> str:
    return symbol.upper().replace("$", "").strip()


def set_overlays(symbol: str, overlays: List[Dict[str, Any]], meta: Optional[Dict[str, Any]] = None) -> None:
    key = _normalize_symbol(symbol)
    with _LOCK:
        _CACHE[key] = {
            "overlays": overlays,
            "meta": meta or {},
            "ts": time.time(),
        }


def get_overlays(symbol: str, max_age_sec: float = 900) -> Optional[Dict[str, Any]]:
    key = _normalize_symbol(symbol)
    now = time.time()
    with _LOCK:
        entry = _CACHE.get(key)
        if not entry:
            return None
        if now - entry.get("ts", 0) > max_age_sec:
            _CACHE.pop(key, None)
            return None
        return entry
