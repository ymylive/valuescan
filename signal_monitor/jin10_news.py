"""Jin10 news fetcher with caching and fallback."""

from __future__ import annotations

import json
import time
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from signal_monitor.logger import logger
except Exception:
    from logger import logger

FIXTURES_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "jin10_news_50.json"
_cache_lock = threading.Lock()
_CACHE: Dict[str, Any] = {}


def _cache_get(key: str, ttl: int) -> Optional[List[Dict[str, Any]]]:
    with _cache_lock:
        cached = _CACHE.get(key)
        if not cached:
            return None
        if (time.time() - cached["ts"]) > ttl:
            return None
        return cached.get("value")


def _cache_set(key: str, value: List[Dict[str, Any]]) -> None:
    with _cache_lock:
        _CACHE[key] = {"ts": time.time(), "value": value}


def _load_fixtures() -> List[Dict[str, Any]]:
    """Load mock fixtures from file."""
    if not FIXTURES_PATH.exists():
        return []
    try:
        data = json.loads(FIXTURES_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception as exc:
        logger.debug("Failed to load Jin10 fixtures: %s", exc)
        return []


def _fetch_jin10_api(limit: int = 50) -> Optional[List[Dict[str, Any]]]:
    """Fetch from Jin10 API"""
    raise NotImplementedError("Jin10 API integration pending")


def fetch_jin10_news(limit: int = 50, ttl: int = 300) -> List[Dict[str, Any]]:
    """
    Fetch latest Jin10 news with caching and fallback.

    Args:
        limit: Maximum number of news items to return
        ttl: Cache TTL in seconds (default 300)

    Returns:
        List of news items with structure:
        {
            "time": str (ISO 8601),
            "title": str,
            "content": str,
            "tags": [str],
            "importance": "high|medium|low",
            "source": "jin10"
        }
    """
    cache_key = f"jin10_news:{limit}"
    cached = _cache_get(cache_key, ttl)
    if cached is not None:
        logger.debug("Returning cached Jin10 news (%d items)", len(cached))
        return cached

    # Try API first
    news = _fetch_jin10_api(limit)

    # Fallback to fixtures
    if not news:
        logger.debug("Jin10 API unavailable, using fixtures")
        news = _load_fixtures()

    if not news:
        logger.warning("No Jin10 news available (API and fixtures failed)")
        return []

    # Ensure limit
    news = news[:limit]

    # Cache and return
    _cache_set(cache_key, news)
    logger.info("Fetched %d Jin10 news items", len(news))
    return news
