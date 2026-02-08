#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI主力位内存缓存模块 - 支持强弱分级
"""
import threading
import time
from typing import Any, Dict, List, Optional
from dataclasses import asdict

_CACHE: Dict[str, Dict[str, Any]] = {}
_LOCK = threading.Lock()


def _normalize_symbol(symbol: str) -> str:
    return symbol.upper().replace("$", "").strip()


def set_levels(
    symbol: str,
    supports: List[float],
    resistances: List[float],
    meta: Optional[Dict[str, Any]] = None,
    strong_supports: Optional[List[float]] = None,
    strong_resistances: Optional[List[float]] = None,
    weak_supports: Optional[List[float]] = None,
    weak_resistances: Optional[List[float]] = None,
    support_strengths: Optional[List[float]] = None,
    resistance_strengths: Optional[List[float]] = None
) -> None:
    """
    设置AI主力位缓存

    Args:
        symbol: 币种符号
        supports: 支撑位列表
        resistances: 阻力位列表
        meta: 元数据
        strong_supports: 强支撑位
        strong_resistances: 强阻力位
        weak_supports: 弱支撑位
        weak_resistances: 弱阻力位
        support_strengths: 支撑位强度列表 (0-1)
        resistance_strengths: 阻力位强度列表 (0-1)
    """
    key = _normalize_symbol(symbol)
    with _LOCK:
        _CACHE[key] = {
            "supports": supports,
            "resistances": resistances,
            "strong_supports": strong_supports or [],
            "strong_resistances": strong_resistances or [],
            "weak_supports": weak_supports or [],
            "weak_resistances": weak_resistances or [],
            "support_strengths": support_strengths or [],
            "resistance_strengths": resistance_strengths or [],
            "meta": meta or {},
            "ts": time.time(),
        }


def get_levels(symbol: str, max_age_sec: float = 86400) -> Optional[Dict[str, Any]]:
    """获取AI主力位缓存"""
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


def get_strong_levels(symbol: str, max_age_sec: float = 86400) -> Optional[Dict[str, List[float]]]:
    """仅获取强主力位"""
    entry = get_levels(symbol, max_age_sec)
    if not entry:
        return None
    return {
        "supports": entry.get("strong_supports", []),
        "resistances": entry.get("strong_resistances", [])
    }


def get_weak_levels(symbol: str, max_age_sec: float = 86400) -> Optional[Dict[str, List[float]]]:
    """仅获取弱主力位"""
    entry = get_levels(symbol, max_age_sec)
    if not entry:
        return None
    return {
        "supports": entry.get("weak_supports", []),
        "resistances": entry.get("weak_resistances", [])
    }


def wait_for_levels(symbol: str, timeout_sec: float = 8, poll_sec: float = 0.3) -> Optional[Dict[str, Any]]:
    """等待缓存可用"""
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        entry = get_levels(symbol)
        if entry:
            return entry
        time.sleep(poll_sec)
    return None


def set_levels_from_result(symbol: str, result: Dict[str, Any]) -> None:
    """
    从find_ai_key_levels结果设置缓存

    Args:
        symbol: 币种符号
        result: find_ai_key_levels返回的结果字典
    """
    supports = [l.price if hasattr(l, 'price') else l for l in result.get('supports', [])]
    resistances = [l.price if hasattr(l, 'price') else l for l in result.get('resistances', [])]

    strong_supports = [l.price if hasattr(l, 'price') else l for l in result.get('strong_supports', [])]
    strong_resistances = [l.price if hasattr(l, 'price') else l for l in result.get('strong_resistances', [])]

    weak_supports = [l.price if hasattr(l, 'price') else l for l in result.get('weak_supports', [])]
    weak_resistances = [l.price if hasattr(l, 'price') else l for l in result.get('weak_resistances', [])]

    support_strengths = [l.strength if hasattr(l, 'strength') else 0.5 for l in result.get('supports', [])]
    resistance_strengths = [l.strength if hasattr(l, 'strength') else 0.5 for l in result.get('resistances', [])]

    set_levels(
        symbol=symbol,
        supports=supports,
        resistances=resistances,
        meta=result.get('metadata', {}),
        strong_supports=strong_supports,
        strong_resistances=strong_resistances,
        weak_supports=weak_supports,
        weak_resistances=weak_resistances,
        support_strengths=support_strengths,
        resistance_strengths=resistance_strengths
    )


def clear_cache(symbol: Optional[str] = None) -> None:
    """清除缓存"""
    with _LOCK:
        if symbol:
            key = _normalize_symbol(symbol)
            _CACHE.pop(key, None)
        else:
            _CACHE.clear()

