import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def _normalize_payload(data: Any) -> Dict[str, Any]:
    if isinstance(data, dict):
        return data
    if isinstance(data, list):
        return {"items": data}
    return {}


def _load_json_from_env(env_name: str) -> Dict[str, Any]:
    raw = (os.getenv(env_name) or "").strip()
    if not raw:
        return {}
    try:
        return _normalize_payload(json.loads(raw))
    except Exception:
        return {"note": "invalid_env_json"}


def _load_json_from_file(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return _normalize_payload(json.loads(path.read_text(encoding="utf-8")))
    except Exception:
        return {"note": "invalid_file_json"}


def _parse_timestamp(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        ts = float(value)
        if ts > 1e12:
            ts /= 1000.0
        elif ts > 1e10:
            ts /= 1000.0
        if ts <= 0:
            return None
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        if s.isdigit():
            return _parse_timestamp(float(s))
        s = s.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(s)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            pass
        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y/%m/%d %H:%M:%S",
            "%Y/%m/%d %H:%M",
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%m/%d/%Y %H:%M",
            "%m/%d/%Y",
        ):
            try:
                dt = datetime.strptime(s, fmt)
                return dt.replace(tzinfo=timezone.utc)
            except Exception:
                continue
    return None


def _extract_items(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("items", "data", "events", "calendar", "releases"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def _extract_item_time(item: Dict[str, Any]) -> Optional[datetime]:
    keys = (
        "time",
        "timestamp",
        "ts",
        "date",
        "datetime",
        "release_time",
        "releaseTime",
        "published_at",
        "publishedAt",
        "event_time",
        "eventTime",
        "when",
    )
    for key in keys:
        if key in item:
            ts = _parse_timestamp(item.get(key))
            if ts:
                return ts
    return None


def _filter_items(
    items: List[Dict[str, Any]],
    now: datetime,
    max_age_days: Optional[int] = None,
    max_future_days: Optional[int] = None,
) -> List[Dict[str, Any]]:
    filtered = []
    for item in items:
        ts = _extract_item_time(item)
        if not ts:
            continue
        delta_sec = (ts - now).total_seconds()
        if max_age_days is not None and delta_sec < -(max_age_days * 86400):
            continue
        if max_future_days is not None and delta_sec > (max_future_days * 86400):
            continue
        filtered.append(item)
    return filtered


def _macro_meta(now: datetime) -> Dict[str, Any]:
    return {
        "calendar_window_days": 7,
        "release_max_age_days": 3,
        "generated_at": now.isoformat(),
    }


def _filter_combined(payload: Dict[str, Any], now: datetime) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    calendar_payload = payload.get("calendar")
    releases_payload = payload.get("recent_releases") or payload.get("releases")
    if calendar_payload is None and releases_payload is None and _extract_items(payload):
        calendar_payload = payload

    calendar_items = _extract_items(calendar_payload)
    release_items = _extract_items(releases_payload)

    filtered_calendar = _filter_items(calendar_items, now, max_age_days=3, max_future_days=7)
    filtered_releases = _filter_items(release_items, now, max_age_days=3, max_future_days=1)

    if filtered_calendar:
        result["calendar"] = {"items": filtered_calendar}
    if filtered_releases:
        result["recent_releases"] = {"items": filtered_releases}
    if result:
        result["meta"] = _macro_meta(now)
    return result


def load_macro_data() -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    combined = _load_json_from_env("NOFX_MACRO_DATA_JSON")
    if not combined:
        combined = _load_json_from_file(Path(__file__).parent / "macro_data.json")
    if combined:
        return _filter_combined(combined, now)

    calendar = _load_json_from_env("NOFX_MACRO_CALENDAR_JSON")
    if not calendar:
        calendar = _load_json_from_file(Path(__file__).parent / "macro_calendar.json")

    releases = _load_json_from_env("NOFX_MACRO_RELEASES_JSON")
    if not releases:
        releases = _load_json_from_file(Path(__file__).parent / "macro_releases.json")

    macro_data: Dict[str, Any] = {}
    calendar_items = _filter_items(_extract_items(calendar), now, max_age_days=3, max_future_days=7)
    release_items = _filter_items(_extract_items(releases), now, max_age_days=3, max_future_days=1)

    if calendar_items:
        macro_data["calendar"] = {"items": calendar_items}
    if release_items:
        macro_data["recent_releases"] = {"items": release_items}
    if macro_data:
        macro_data["meta"] = _macro_meta(now)
    return macro_data
