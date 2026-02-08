#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
In-memory cache for AI-derived key levels (supports/resistances).
"""
import threading
import time
from typing import Any, Dict, List, Optional

_CACHE: Dict[str, Dict[str, Any]] = {}
_LOCK = threading.Lock()


def _normalize_symbol(symbol: str) -> str:
    return symbol.upper().replace("$", "").strip()


def set_levels(symbol: str, supports: List[float], resistances: List[float], meta: Optional[Dict[str, Any]] = None) -> None:
    key = _normalize_symbol(symbol)
    with _LOCK:
        _CACHE[key] = {
            "supports": supports,
            "resistances": resistances,
            "meta": meta or {},
            "ts": time.time(),
        }


def get_levels(symbol: str, max_age_sec: float = 86400) -> Optional[Dict[str, Any]]:
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


def wait_for_levels(symbol: str, timeout_sec: float = 8, poll_sec: float = 0.3) -> Optional[Dict[str, Any]]:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        entry = get_levels(symbol)
        if entry:
            return entry
        time.sleep(poll_sec)
    return None
