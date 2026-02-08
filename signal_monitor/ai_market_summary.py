#!/usr/bin/env python3
"""AI market summary helpers."""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

try:
    from logger import logger
except Exception:
    import logging

    logger = logging.getLogger(__name__)

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
    from .market_data_sources import fetch_market_snapshot, fetch_trending
except Exception:
    from market_data_sources import fetch_market_snapshot, fetch_trending  # type: ignore[import-not-found]

try:
    from .fundamentals_sources import fetch_macro_snapshot
except Exception:
    from fundamentals_sources import fetch_macro_snapshot  # type: ignore[import-not-found]
try:
    from .ai_request_queue import call_ai_with_queue
except Exception:
    from ai_request_queue import call_ai_with_queue  # type: ignore[import-not-found]

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR.parent / "data"
STATE_PATH = DATA_DIR / "market_summary_state.json"
SUMMARY_OUTPUT_PATH = DATA_DIR / "market_summary_latest.json"

AI_SUMMARY_ENABLED = os.getenv("AI_SUMMARY_ENABLED", "1").lower() in ("1", "true", "yes", "on")
AI_SUMMARY_API_KEY = os.getenv("AI_SUMMARY_API_KEY", "").strip()
AI_SUMMARY_API_URL = os.getenv("AI_SUMMARY_API_URL", "").strip()
AI_SUMMARY_MODEL = os.getenv("AI_SUMMARY_MODEL", "").strip()
DEFAULT_MARKET_SYMBOLS = ["BTC", "ETH", "BNB", "SOL"]


def _load_config(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _merge_defaults(overrides: Dict[str, Any], defaults: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(defaults)
    merged.update({k: v for k, v in overrides.items() if v is not None})
    return merged


def get_ai_summary_config() -> Dict[str, Any]:
    """Return AI summary config without legacy dependencies."""
    defaults = {
        "enabled": AI_SUMMARY_ENABLED,
        "api_key": AI_SUMMARY_API_KEY,
        "api_url": AI_SUMMARY_API_URL,
        "model": AI_SUMMARY_MODEL,
        "api_protocol": os.getenv("AI_SUMMARY_API_PROTOCOL", "auto").strip(),
    }
    config_path = BASE_DIR / "ai_summary_config.json"
    return _merge_defaults(_load_config(config_path), defaults)


def get_ai_market_config() -> Dict[str, Any]:
    """Return AI market config without legacy dependencies."""
    defaults = {
        "enabled": True,
        "api_key": AI_SUMMARY_API_KEY,
        "api_url": AI_SUMMARY_API_URL,
        "model": AI_SUMMARY_MODEL,
        "api_protocol": os.getenv("AI_MARKET_API_PROTOCOL", "auto").strip(),
        "summary_mode": "market",
        "market_label": "TOTAL_MKT",
        "market_symbols": ",".join(DEFAULT_MARKET_SYMBOLS),
        "market_symbol_limit": 12,
    }
    config_path = BASE_DIR / "ai_market_summary_config.json"
    return _merge_defaults(_load_config(config_path), defaults)


def get_ai_overlays_config() -> Dict[str, Any]:
    """Return AI overlays config without legacy dependencies."""
    defaults = {
        "enabled": True,
        "api_key": AI_SUMMARY_API_KEY,
        "api_url": AI_SUMMARY_API_URL,
        "model": AI_SUMMARY_MODEL,
        "api_protocol": os.getenv("AI_OVERLAYS_API_PROTOCOL", "auto").strip(),
    }
    config_path = BASE_DIR / "ai_overlays_config.json"
    return _merge_defaults(_load_config(config_path), defaults)


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


def _load_state(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_state(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=True, separators=(",", ":")), encoding="utf-8")
    os.replace(tmp_path, path)


def _normalize_symbols(raw: Optional[object]) -> List[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        tokens = [t.strip().upper() for t in raw.replace(";", ",").split(",")]
        return [t for t in tokens if t]
    if isinstance(raw, (list, tuple, set)):
        out = []
        for item in raw:
            if not item:
                continue
            out.append(str(item).strip().upper())
        return [t for t in out if t]
    return []


def _summary_due(state: Dict[str, Any], interval_hours: float) -> bool:
    try:
        last_ts = float(state.get("last_ts", 0) or 0)
    except Exception:
        last_ts = 0.0
    if interval_hours <= 0:
        return True
    return (time.time() - last_ts) >= (interval_hours * 3600)


def _format_levels(items: Any, max_items: int = 5) -> str:
    if not isinstance(items, list):
        return "?"
    out: List[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        price = item.get("price")
        if not isinstance(price, (int, float)):
            continue
        strength = item.get("strength")
        if isinstance(strength, (int, float)):
            out.append(f"{_format_market_value(price)} ({int(strength)})")
        else:
            out.append(_format_market_value(price))
        if len(out) >= max_items:
            break
    return ", ".join(out) if out else "?"


def _format_market_value(value: Any, digits: int = 4) -> str:
    if not isinstance(value, (int, float)):
        return "?"
    v = float(value)
    abs_v = abs(v)
    if abs_v >= 1e12:
        return f"{v / 1e12:.2f}T"
    if abs_v >= 1e9:
        return f"{v / 1e9:.2f}B"
    if abs_v >= 1e6:
        return f"{v / 1e6:.2f}M"
    if abs_v >= 1e3:
        return f"{v / 1e3:.2f}K"
    return f"{v:.{digits}f}"


def _format_number(value: Any, digits: int = 4) -> str:
    return _format_market_value(value, digits=digits)


def _format_list(items: Any, digits: int = 4) -> str:
    if not isinstance(items, list):
        return "?"
    out: List[str] = []
    for item in items:
        if isinstance(item, (int, float)):
            out.append(_format_number(item, digits=digits))
        elif isinstance(item, str):
            out.append(item)
    return ", ".join(out) if out else "?"


def _format_pct(value: Any, digits: int = 2) -> str:
    if not isinstance(value, (int, float)):
        return "?"
    return f"{value:+.{digits}f}%"


def _format_ratio(value: Any, digits: int = 2) -> str:
    if not isinstance(value, (int, float)):
        return "?"
    return f"{value * 100:.{digits}f}%"


def _format_as_of(value: Any) -> str:
    if not value:
        return ""
    dt = None
    if isinstance(value, (int, float)):
        try:
            dt = datetime.fromtimestamp(float(value), tz=timezone.utc)
        except Exception:
            dt = None
    elif isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            return value.strip()
    if not dt:
        return str(value)
    return dt.astimezone(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M UTC+8")


def _format_movers(items: Any, max_items: int = 3) -> str:
    if not isinstance(items, list):
        return "暂无"
    out: List[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        symbol = item.get("symbol")
        change = item.get("change")
        if symbol and isinstance(change, (int, float)):
            out.append(f"{symbol} {_format_pct(change)}")
        if len(out) >= max_items:
            break
    return "、".join(out) if out else "暂无"


def _get_basket_change(snapshot: Dict[str, Any], symbol: str) -> Optional[float]:
    basket = snapshot.get("basket")
    if not isinstance(basket, list):
        return None
    for item in basket:
        if not isinstance(item, dict):
            continue
        if str(item.get("symbol") or "").upper() == symbol.upper():
            change = item.get("price_change_percent")
            if isinstance(change, (int, float)):
                return float(change)
    return None


def _coerce_items(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("items", "data", "events", "calendar", "releases"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def _pick_item_title(item: Dict[str, Any]) -> Optional[str]:
    for key in ("title", "event", "name", "release", "indicator", "description", "subject"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    if item.get("series_id") and item.get("date"):
        return f"{item.get('series_id')} {item.get('date')}"
    if item.get("release_id") and item.get("date"):
        return f"{item.get('release_id')} {item.get('date')}"
    return None


def _limit_titles(items: List[Dict[str, Any]], max_items: int = 3) -> List[str]:
    titles: List[str] = []
    for item in items:
        title = _pick_item_title(item)
        if title:
            titles.append(title)
        if len(titles) >= max_items:
            break
    return titles


def _build_macro_event_note(snapshot: Dict[str, Any]) -> str:
    macro_snapshot = snapshot.get("macro_snapshot") if isinstance(snapshot, dict) else {}
    if not isinstance(macro_snapshot, dict):
        macro_snapshot = {}

    economic_data = macro_snapshot.get("economic_data") if isinstance(macro_snapshot.get("economic_data"), dict) else {}
    major_events_payload = macro_snapshot.get("major_events") if isinstance(macro_snapshot.get("major_events"), dict) else {}
    major_policies_payload = macro_snapshot.get("major_policies") if isinstance(macro_snapshot.get("major_policies"), dict) else {}

    if economic_data or major_events_payload or major_policies_payload:
        econ_brief = economic_data.get("brief") if isinstance(economic_data.get("brief"), list) else []
        event_brief = major_events_payload.get("brief") if isinstance(major_events_payload.get("brief"), list) else []
        policy_brief = major_policies_payload.get("brief") if isinstance(major_policies_payload.get("brief"), list) else []

        def _fmt(items: List[str]) -> str:
            cleaned = [item for item in items if item]
            return "、".join(cleaned) if cleaned else "暂无"

        return (
            f"重大事件: {_fmt(event_brief)}; "
            f"即将发布数据: {_fmt(econ_brief[:2])}; "
            f"已发布数据: {_fmt(econ_brief[2:]) or '暂无'}。"
        )

    major_events: List[str] = []
    upcoming_data: List[str] = []
    released_data: List[str] = []

    macro = macro_snapshot.get("macro") if isinstance(macro_snapshot.get("macro"), dict) else {}
    calendar_items = _coerce_items(macro.get("calendar"))
    recent_items = _coerce_items(macro.get("recent_releases"))
    if calendar_items:
        upcoming_data.extend(_limit_titles(calendar_items, max_items=3))
    if recent_items:
        released_data.extend(_limit_titles(recent_items, max_items=3))

    macro_fred = macro_snapshot.get("macro_fred") if isinstance(macro_snapshot.get("macro_fred"), dict) else {}
    fred_upcoming = macro_fred.get("upcoming") if isinstance(macro_fred.get("upcoming"), list) else []
    fred_series = macro_fred.get("series") if isinstance(macro_fred.get("series"), list) else []
    if fred_upcoming:
        upcoming_data.extend(_limit_titles([item for item in fred_upcoming if isinstance(item, dict)], max_items=3))
    if fred_series:
        released_data.extend(_limit_titles([item for item in fred_series if isinstance(item, dict)], max_items=3))

    macro_gdelt = macro_snapshot.get("macro_gdelt") if isinstance(macro_snapshot.get("macro_gdelt"), dict) else {}
    articles = macro_gdelt.get("articles") if isinstance(macro_gdelt.get("articles"), list) else []
    if articles:
        major_events.extend(_limit_titles([item for item in articles if isinstance(item, dict)], max_items=3))

    def _fmt(items: List[str]) -> str:
        cleaned = [item for item in items if item]
        return "、".join(cleaned) if cleaned else "暂无"

    return f"重大事件: {_fmt(major_events)}; 即将发布数据: {_fmt(upcoming_data)}; 已发布数据: {_fmt(released_data)}。"


def _translate_trend_direction(value: Any) -> str:
    mapping = {
        "bullish": "偏多",
        "bearish": "偏空",
        "sideways": "震荡",
    }
    if not value:
        return "未知"
    return mapping.get(str(value).strip().lower(), "未知")


def _translate_risk_level(value: Any) -> str:
    mapping = {
        "low": "低",
        "medium": "中",
        "high": "高",
    }
    if not value:
        return "未知"
    return mapping.get(str(value).strip().lower(), "未知")


def _translate_action(value: Any) -> str:
    mapping = {
        "buy": "买入",
        "sell": "卖出",
        "hold": "持有",
        "wait": "等待",
    }
    if not value:
        return "未知"
    return mapping.get(str(value).strip().lower(), "未知")


def _format_summary_message(
    symbol: str,
    analysis: Dict[str, Any],
    fundamental_note: Optional[str] = None,
) -> str:
    label_map = {
        "TOTAL_MKT": "大盘",
        "TOTAL_MARKET_CAP": "大盘",
        "TOTAL_MKT_CAP": "大盘",
        "GLOBAL": "大盘",
        "MARKET": "大盘",
    }
    display_symbol = label_map.get(str(symbol).strip().upper(), symbol)
    summary = (analysis.get("summary") or "").strip()
    fundamental_view = analysis.get("fundamental_view") if isinstance(analysis.get("fundamental_view"), str) else ""
    technical_view = analysis.get("technical_view") if isinstance(analysis.get("technical_view"), str) else ""
    macro_view = analysis.get("macro_view") if isinstance(analysis.get("macro_view"), str) else ""
    liquidity_view = analysis.get("liquidity_view") if isinstance(analysis.get("liquidity_view"), str) else ""
    data_conflicts = analysis.get("data_conflicts") if isinstance(analysis.get("data_conflicts"), str) else ""
    btc_eth_view = analysis.get("btc_eth_view") if isinstance(analysis.get("btc_eth_view"), str) else ""
    btc_eth_suggestion = analysis.get("btc_eth_trade_suggestion") if isinstance(analysis.get("btc_eth_trade_suggestion"), dict) else {}

    if not fundamental_view:
        fundamental_view = "无"
    if not technical_view:
        technical_view = "无"
    if not macro_view:
        macro_view = "无"
    if not liquidity_view:
        liquidity_view = "无"
    if not data_conflicts or data_conflicts in ("?", "??", "????", "N/A"):
        data_conflicts = "无"
    if not btc_eth_view:
        btc_eth_view = "无"
    if not summary:
        summary = "无"


    trend = analysis.get("trend") if isinstance(analysis.get("trend"), dict) else {}
    direction = _translate_trend_direction(trend.get("direction"))
    strength = trend.get("strength")
    trend_line = f"{direction}"
    if isinstance(strength, (int, float)):
        trend_line = f"{trend_line} ({int(strength)}/100)"
    trend_desc = trend.get("description") or ""
    if trend_desc:
        trend_line = f"{trend_line} - {trend_desc}"

    key_levels = analysis.get("key_levels") if isinstance(analysis.get("key_levels"), dict) else {}
    supports = _format_levels(key_levels.get("supports"))
    resistances = _format_levels(key_levels.get("resistances"))

    patterns = analysis.get("patterns") if isinstance(analysis.get("patterns"), dict) else {}
    primary_pattern = patterns.get("primary")
    pattern_desc = patterns.get("description") or ""
    detected = patterns.get("detected")
    pattern_line = None
    if primary_pattern:
        pattern_line = f"{primary_pattern}"
        if pattern_desc:
            pattern_line = f"{pattern_line} - {pattern_desc}"
    elif isinstance(detected, list) and detected:
        pattern_line = ", ".join(str(p) for p in detected if p)

    sentiment = analysis.get("sentiment") if isinstance(analysis.get("sentiment"), dict) else {}
    momentum = analysis.get("momentum") if isinstance(analysis.get("momentum"), dict) else {}
    sentiment_line = None
    if sentiment:
        score = sentiment.get("score")
        desc = sentiment.get("description") or ""
        sentiment_line = f"{score if isinstance(score, (int, float)) else '?'}"
        if desc:
            sentiment_line = f"{sentiment_line} - {desc}"
    momentum_line = None
    if momentum:
        score = momentum.get("score")
        desc = momentum.get("description") or ""
        momentum_line = f"{score if isinstance(score, (int, float)) else '?'}"
        if desc:
            momentum_line = f"{momentum_line} - {desc}"

    risk = analysis.get("risk_assessment") if isinstance(analysis.get("risk_assessment"), dict) else {}
    risk_line = None
    if risk:
        level = _translate_risk_level(risk.get("level"))
        factors = risk.get("factors")
        if isinstance(factors, list) and factors:
            risk_line = f"{level} - {', '.join(str(f) for f in factors if f)}"
        else:
            risk_line = f"{level}"

    suggestion = analysis.get("trading_suggestion") if isinstance(analysis.get("trading_suggestion"), dict) else {}
    suggestion_lines: List[str] = []
    if suggestion:
        raw_action = str(suggestion.get("action") or "").strip().lower()
        action = _translate_action(suggestion.get("action"))
        entry_zone = suggestion.get("entry_zone")
        stop_loss = suggestion.get("stop_loss")
        take_profit = suggestion.get("take_profit")
        reasoning = suggestion.get("reasoning") or ""
        suggestion_lines.append(f"• 动作: {action}")
        if isinstance(entry_zone, list) and len(entry_zone) >= 2:
            suggestion_lines.append(
                f"• 入场区间: {_format_number(entry_zone[0])} - {_format_number(entry_zone[1])}"
            )
        elif entry_zone is not None:
            suggestion_lines.append(f"• 入场区间: {_format_number(entry_zone)}")
        if raw_action not in ("wait", "hold", "等待", "观望", "持有"):
            if stop_loss is not None:
                suggestion_lines.append(f"• 止损: {_format_number(stop_loss)}")
            if take_profit is not None:
                suggestion_lines.append(f"• 止盈: {_format_list(take_profit)}")
        if reasoning:
            suggestion_lines.append(f"• 理由: {reasoning}")

    btc_eth_lines: List[str] = []
    if btc_eth_suggestion:
        asset = str(btc_eth_suggestion.get("asset") or "").strip().upper() or "BTC/ETH"
        raw_action = str(btc_eth_suggestion.get("action") or "").strip().lower()
        action = _translate_action(btc_eth_suggestion.get("action"))
        entry_zone = btc_eth_suggestion.get("entry_zone")
        stop_loss = btc_eth_suggestion.get("stop_loss")
        take_profit = btc_eth_suggestion.get("take_profit")
        reasoning = btc_eth_suggestion.get("reasoning") or ""
        btc_eth_lines.append(f"• 标的: {asset}")
        btc_eth_lines.append(f"• 动作: {action}")
        if isinstance(entry_zone, list) and len(entry_zone) >= 2:
            btc_eth_lines.append(
                f"• 入场区间: {_format_number(entry_zone[0])} - {_format_number(entry_zone[1])}"
            )
        elif entry_zone is not None:
            btc_eth_lines.append(f"• 入场区间: {_format_number(entry_zone)}")
        if raw_action not in ("wait", "hold", "等待", "观望", "持有"):
            if stop_loss is not None:
                btc_eth_lines.append(f"• 止损: {_format_number(stop_loss)}")
            if take_profit is not None:
                btc_eth_lines.append(f"• 止盈: {_format_list(take_profit)}")
        if reasoning:
            btc_eth_lines.append(f"• 理由: {reasoning}")

    as_of_text = _format_as_of(analysis.get("_as_of") or analysis.get("as_of"))
    section_sep = "━━━━━━━━━━━━━━━━"

    macro_note_line = ""
    if fundamental_note:
        note = fundamental_note.strip()
        if note.endswith("。"):
            note = note[:-1]
        macro_note_line = note.replace(";", "；")

    lines = [f"📊【市场宏观】{display_symbol}"]
    if as_of_text:
        lines.append(f"🕒 更新时间：{as_of_text}")
    lines.append(f"🧭 总览：{summary}")
    lines.append(section_sep)

    lines.append("🧩 核心观点")
    lines.append(f"• 基本面：{fundamental_view}")
    if macro_note_line:
        lines.append(f"• 宏观事件：{macro_note_line}")
    lines.append(f"• 技术面：{technical_view}")
    lines.append(f"• 宏观：{macro_view}")
    lines.append(f"• 流动性：{liquidity_view}")
    lines.append(f"• 数据冲突：{data_conflicts}")
    lines.append(f"• BTC/ETH 类别：{btc_eth_view}")
    lines.append(section_sep)

    lines.append("📌 结构")
    lines.append(f"• 趋势：{trend_line}")
    lines.append(f"• 支撑：{supports}")
    lines.append(f"• 阻力：{resistances}")
    if pattern_line:
        lines.append(f"• 形态：{pattern_line}")
    lines.append(section_sep)

    lines.append("🌡️ 情绪与风险")
    if sentiment_line:
        lines.append(f"• 情绪：{sentiment_line}")
    if momentum_line:
        lines.append(f"• 动能：{momentum_line}")
    if risk_line:
        lines.append(f"• 风险：{risk_line}")

    if suggestion_lines:
        lines.append(section_sep)
        lines.append("🎯 大盘交易建议")
        lines.extend(suggestion_lines)

    if btc_eth_lines:
        lines.append(section_sep)
        lines.append("🪙 BTC/ETH 入场")
        lines.extend(btc_eth_lines)

    return "\n".join(lines).strip()


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def _fetch_global_market_data() -> Dict[str, Any]:
    url = "https://api.coingecko.com/api/v3/global"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return {}
        payload = resp.json()
    except Exception:
        return {}

    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        return {}

    total_market_cap = _safe_float((data.get("total_market_cap") or {}).get("usd"))
    total_volume = _safe_float((data.get("total_volume") or {}).get("usd"))
    market_cap_change = _safe_float(data.get("market_cap_change_percentage_24h_usd"))
    dominance = data.get("market_cap_percentage") if isinstance(data.get("market_cap_percentage"), dict) else {}
    return {
        "total_market_cap": total_market_cap,
        "total_volume_24h": total_volume,
        "market_cap_change_24h": market_cap_change,
        "dominance": {
            "btc": _safe_float(dominance.get("btc")),
            "eth": _safe_float(dominance.get("eth")),
        },
    }


def _build_market_snapshot(config: Dict[str, Any]) -> Dict[str, Any]:
    symbols = _normalize_symbols(config.get("market_symbols") or config.get("symbols")) or DEFAULT_MARKET_SYMBOLS[:]
    try:
        limit = int(config.get("market_symbol_limit", 12) or 12)
    except Exception:
        limit = 12
    if limit > 0:
        symbols = symbols[:limit]

    basket: List[Dict[str, Any]] = []
    for symbol in symbols:
        snapshot = fetch_market_snapshot(symbol)
        if not isinstance(snapshot, dict):
            continue
        basket.append(
            {
                "symbol": symbol,
                "price": _safe_float(snapshot.get("price")),
                "price_change_percent": _safe_float(snapshot.get("price_change_percent")),
                "volume_24h": _safe_float(snapshot.get("volume_24h")),
                "market_cap": _safe_float(snapshot.get("market_cap")),
            }
        )

    changes = [item.get("price_change_percent") for item in basket if isinstance(item.get("price_change_percent"), (int, float))]
    volumes = [item.get("volume_24h") for item in basket if isinstance(item.get("volume_24h"), (int, float))]
    market_caps = [item.get("market_cap") for item in basket if isinstance(item.get("market_cap"), (int, float))]

    weight_sum = sum(market_caps) if market_caps else 0.0
    weighted_change = None
    if weight_sum > 0:
        weighted_change = sum(
            item.get("price_change_percent", 0) * item.get("market_cap", 0)
            for item in basket
            if isinstance(item.get("price_change_percent"), (int, float)) and isinstance(item.get("market_cap"), (int, float))
        ) / weight_sum
    elif changes:
        weighted_change = sum(changes) / len(changes)

    breadth_up = sum(1 for item in basket if isinstance(item.get("price_change_percent"), (int, float)) and item.get("price_change_percent") > 0)
    breadth_down = sum(1 for item in basket if isinstance(item.get("price_change_percent"), (int, float)) and item.get("price_change_percent") < 0)
    breadth_flat = max(len(basket) - breadth_up - breadth_down, 0)

    volatility = None
    if changes:
        mean_val = sum(changes) / len(changes)
        variance = sum((val - mean_val) ** 2 for val in changes) / len(changes)
        volatility = variance ** 0.5

    top_movers = sorted(
        basket,
        key=lambda item: item.get("price_change_percent") if isinstance(item.get("price_change_percent"), (int, float)) else -1e9,
        reverse=True,
    )[:3]
    bottom_movers = sorted(
        basket,
        key=lambda item: item.get("price_change_percent") if isinstance(item.get("price_change_percent"), (int, float)) else 1e9,
    )[:3]

    global_data = _fetch_global_market_data()
    total_market_cap = global_data.get("total_market_cap") or (sum(market_caps) if market_caps else None)
    total_volume = global_data.get("total_volume_24h") or (sum(volumes) if volumes else None)
    market_index_value = total_market_cap

    liquidity_ratio = None
    if total_market_cap and total_volume:
        liquidity_ratio = total_volume / total_market_cap

    macro_snapshot = fetch_macro_snapshot() or {}
    trending = fetch_trending(limit=8)

    return {
        "as_of": datetime.now(timezone.utc).isoformat(),
        "market_index": {
            "name": "TOTAL_MARKET_CAP",
            "value": market_index_value,
            "change_24h": global_data.get("market_cap_change_24h"),
            "unit": "USD",
        },
        "aggregate": {
            "weighted_change_24h": weighted_change,
            "volatility_24h": volatility,
            "total_market_cap": total_market_cap,
            "total_volume_24h": total_volume,
            "liquidity_ratio": liquidity_ratio,
            "market_cap_change_24h": global_data.get("market_cap_change_24h"),
            "dominance": global_data.get("dominance"),
        },
        "breadth": {
            "total": len(basket),
            "up": breadth_up,
            "down": breadth_down,
            "flat": breadth_flat,
        },
        "top_movers": [
            {"symbol": item.get("symbol"), "change": item.get("price_change_percent")}
            for item in top_movers
            if item.get("symbol")
        ],
        "bottom_movers": [
            {"symbol": item.get("symbol"), "change": item.get("price_change_percent")}
            for item in bottom_movers
            if item.get("symbol")
        ],
        "basket": basket,
        "macro_snapshot": macro_snapshot,
        "trending": trending,
    }




def _build_market_prompt(snapshot: Dict[str, Any]) -> str:
    payload_json = json.dumps(_compact_snapshot_for_prompt(snapshot), ensure_ascii=False)
    lines = [
        "你是专业的市场宏观分析师，只返回严格 JSON，所有描述性文本必须使用中文。",
        "严禁输出英文或拼音；若无法中文表达，必须用中文说明“数据不足”。",
        "需要 8-12 行要点，总结趋势/结构/动能/流动性/宏观/风险/冲突。",
        "说明: key_levels/entry_zone/stop_loss/take_profit 主要给 BTC/ETH，其他币可留空。",
        "btc_eth_trade_suggestion 必须给出 asset=BTC/ETH/BOTH。",
        "action 只能是 buy/sell/hold/wait；stop_loss 和 take_profit 若不适用可为 null。",
        "JSON schema (keys must match; enum values not translated):",
        '{"trend":{"direction":"bullish/bearish/sideways","strength":0-100,"description":"..."},"key_levels":{"supports":[{"price":0,"strength":0-100,"reason":"..."}],"resistances":[{"price":0,"strength":0-100,"reason":"..."}]},"patterns":{"detected":[],"primary":null,"description":"..."},"sentiment":{"score":-100,"description":"..."},"momentum":{"score":-100,"description":"..."},"risk_assessment":{"level":"low/medium/high","factors":["..."]},"trading_suggestion":{"action":"buy/sell/hold/wait","entry_zone":[0,0],"stop_loss":0,"take_profit":[0,0],"reasoning":"..."},"btc_eth_trade_suggestion":{"asset":"BTC/ETH/BOTH","action":"buy/sell/hold/wait","entry_zone":[0,0],"stop_loss":0,"take_profit":[0,0],"reasoning":"..."},"summary":"...","fundamental_view":"...","technical_view":"...","macro_view":"...","liquidity_view":"...","data_conflicts":"...","btc_eth_view":"..."}',
        "输入数据:",
        payload_json,
    ]
    return "\n".join(lines)


def _compact_snapshot_for_prompt(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(snapshot, dict):
        return {}
    compact = dict(snapshot)
    compact["macro_snapshot"] = _compact_macro_snapshot(snapshot.get("macro_snapshot"))
    return compact


def _compact_macro_snapshot(macro_snapshot: Any) -> Dict[str, Any]:
    if not isinstance(macro_snapshot, dict):
        return {}

    out: Dict[str, Any] = {}

    economic_data = macro_snapshot.get("economic_data")
    if isinstance(economic_data, dict) and economic_data:
        out["economic_data"] = economic_data

    major_events = macro_snapshot.get("major_events")
    if isinstance(major_events, dict) and major_events:
        out["major_events"] = major_events

    major_policies = macro_snapshot.get("major_policies")
    if isinstance(major_policies, dict) and major_policies:
        out["major_policies"] = major_policies

    return out
def _call_ai_summary_api(prompt: str, config: Dict[str, Any]) -> Optional[str]:
    api_key = (config.get("api_key") or "").strip()
    api_url = (config.get("api_url") or "").strip()
    model = (config.get("model") or "").strip()
    if not api_key or not api_url or not model:
        return None

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    max_retries = int(os.getenv("NOFX_AI_API_RETRY", "1") or 1)
    timeout_sec = int(os.getenv("NOFX_AI_API_TIMEOUT", "90") or 90)
    connect_timeout = float(os.getenv("NOFX_AI_CONNECT_TIMEOUT", "15") or 15)
    max_tokens = int(os.getenv("NOFX_AI_MARKET_MAX_TOKENS", "8000") or 8000)

    protocol, resolved_url = resolve_protocol_and_url(api_url, config.get("api_protocol"))
    stream = should_force_responses_stream(resolved_url, protocol)
    payload = build_payload(
        protocol,
        resolved_url,
        model,
        "你是专业的市场宏观分析师，仅返回严格 JSON，所有描述性文本必须使用中文，禁止出现英文或拼音。",
        prompt,
        max_tokens,
        0.3,
        stream,
    )

    proxies = _get_ai_proxies()
    use_env_proxy = os.getenv("NOFX_AI_TRUST_ENV", "0").lower() in ("1", "true", "yes", "on")
    retry_statuses = {429, 500, 502, 503, 504}

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
        except Exception as exc:
            if attempt < max_retries:
                logger.warning(
                    "Market summary AI call error (attempt %s/%s): %s",
                    attempt + 1,
                    max_retries + 1,
                    exc,
                )
                time.sleep(2 + attempt * 2)
                continue
            logger.warning("Market summary AI call error: %s", exc)
            return None

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
                logger.warning("Market summary AI call failed: %s - %s", resp.status_code, resp.text[:200])
                if attempt < max_retries and resp.status_code in retry_statuses:
                    time.sleep(2 + attempt * 2)
                    continue
                return None

        try:
            if protocol == AI_PROTOCOL_RESPONSES:
                content = parse_responses_body(resp.text)
            else:
                try:
                    payload_json = resp.json()
                except Exception:
                    payload_json = None
                content = parse_compatible_content(payload_json) if isinstance(payload_json, dict) else ""
                if not content:
                    content = (resp.text or "").strip()
        except Exception as exc:
            if attempt < max_retries:
                logger.warning(
                    "Market summary AI parse error (attempt %s/%s): %s",
                    attempt + 1,
                    max_retries + 1,
                    exc,
                )
                time.sleep(2 + attempt * 2)
                continue
            logger.warning("Market summary AI parse error: %s", exc)
            return None

        if content:
            return content.strip()
        if attempt < max_retries:
            time.sleep(2 + attempt * 2)
            continue
        return None


def _parse_ai_summary(raw: str) -> Optional[Dict[str, Any]]:
    if not raw:
        return None
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

            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, flags=re.S)
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
                data = json.loads(cleaned[start : end + 1])
            except Exception:
                data = None
    if isinstance(data, dict):
        return data
    return None


def _build_market_summary(config: Dict[str, Any]) -> Optional[Tuple[Dict[str, Any], Dict[str, Any]]]:
    snapshot = _build_market_snapshot(config)
    prompt = _build_market_prompt(snapshot)
    raw = call_ai_with_queue(lambda: _call_ai_summary_api(prompt, config))
    if not raw:
        logger.warning("Market summary AI returned empty response.")
        return None
    analysis = _parse_ai_summary(raw)
    if not analysis:
        logger.warning("Market summary AI parse failed.")
        return None
    return analysis, snapshot


def _build_fallback_market_analysis(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    aggregate = snapshot.get("aggregate") if isinstance(snapshot.get("aggregate"), dict) else {}
    market_index = snapshot.get("market_index") if isinstance(snapshot.get("market_index"), dict) else {}
    breadth = snapshot.get("breadth") if isinstance(snapshot.get("breadth"), dict) else {}

    total_market_cap = aggregate.get("total_market_cap") or market_index.get("value")
    total_volume = aggregate.get("total_volume_24h")
    market_cap_change = aggregate.get("market_cap_change_24h") or market_index.get("change_24h")
    weighted_change = aggregate.get("weighted_change_24h")
    volatility = aggregate.get("volatility_24h")
    liquidity_ratio = aggregate.get("liquidity_ratio")

    summary_parts: List[str] = []
    if total_market_cap is not None:
        summary_parts.append(f"总市值{_format_market_value(total_market_cap)}")
    if market_cap_change is not None:
        summary_parts.append(f"24H {_format_pct(market_cap_change)}")
    breadth_total = breadth.get("total")
    breadth_up = breadth.get("up")
    breadth_down = breadth.get("down")
    breadth_flat = breadth.get("flat")
    if isinstance(breadth_total, int) and breadth_total > 0:
        up = int(breadth_up or 0)
        down = int(breadth_down or 0)
        flat = int(breadth_flat or 0)
        summary_parts.append(f"上涨{up}/{breadth_total} 下跌{down}/{breadth_total} 平盘{flat}")
    if total_volume is not None:
        summary_parts.append(f"24H成交{_format_market_value(total_volume)}")

    dominance = aggregate.get("dominance") if isinstance(aggregate.get("dominance"), dict) else {}
    btc_dom = dominance.get("btc") if isinstance(dominance.get("btc"), (int, float)) else None
    eth_dom = dominance.get("eth") if isinstance(dominance.get("eth"), (int, float)) else None
    dom_parts = []
    if btc_dom is not None:
        dom_parts.append(f"BTC {btc_dom:.2f}%")
    if eth_dom is not None:
        dom_parts.append(f"ETH {eth_dom:.2f}%")
    if dom_parts:
        summary_parts.append("主导率 " + " / ".join(dom_parts))

    summary = "；".join(summary_parts) if summary_parts else "市场快照数据不足，暂无法给出完整结论。"

    technical_bits: List[str] = []
    if weighted_change is not None:
        technical_bits.append(f"加权涨跌{_format_pct(weighted_change)}")
    if volatility is not None:
        technical_bits.append(f"波动{_format_pct(volatility)}")
    top_movers = _format_movers(snapshot.get("top_movers"))
    bottom_movers = _format_movers(snapshot.get("bottom_movers"))
    if top_movers != "暂无":
        technical_bits.append(f"领涨：{top_movers}")
    if bottom_movers != "暂无":
        technical_bits.append(f"领跌：{bottom_movers}")
    technical_view = "；".join(technical_bits) if technical_bits else "数据不足"

    if total_volume is not None and total_market_cap is not None and liquidity_ratio is not None:
        liquidity_view = f"24H成交{_format_market_value(total_volume)}，换手比{_format_ratio(liquidity_ratio)}"
    elif total_volume is not None:
        liquidity_view = f"24H成交{_format_market_value(total_volume)}"
    else:
        liquidity_view = "数据不足"

    btc_change = _get_basket_change(snapshot, "BTC")
    eth_change = _get_basket_change(snapshot, "ETH")
    btc_eth_parts: List[str] = []
    if btc_change is not None:
        btc_eth_parts.append(f"BTC 24H {_format_pct(btc_change)}")
    if eth_change is not None:
        btc_eth_parts.append(f"ETH 24H {_format_pct(eth_change)}")
    btc_eth_view = "，".join(btc_eth_parts) if btc_eth_parts else "暂无"

    direction = "sideways"
    strength = 20
    if isinstance(weighted_change, (int, float)):
        if weighted_change >= 0.6:
            direction = "bullish"
        elif weighted_change <= -0.6:
            direction = "bearish"
        strength = int(max(20, min(90, abs(weighted_change) * 12)))

    trend_desc_parts = []
    if weighted_change is not None:
        trend_desc_parts.append(f"加权{_format_pct(weighted_change)}")
    if isinstance(breadth_total, int) and breadth_total > 0:
        trend_desc_parts.append(f"广度{int(breadth_up or 0)}/{breadth_total}")
    trend_desc = "，".join(trend_desc_parts)

    sentiment = {}
    if isinstance(breadth_total, int) and breadth_total > 0:
        breadth_score = int(((int(breadth_up or 0) - int(breadth_down or 0)) / breadth_total) * 100)
        sentiment = {"score": max(-100, min(100, breadth_score)), "description": f"上涨{breadth_up} 下跌{breadth_down}"}

    momentum = {}
    if isinstance(weighted_change, (int, float)):
        momentum_score = int(max(-100, min(100, weighted_change * 10)))
        momentum = {"score": momentum_score, "description": f"24H加权涨跌{_format_pct(weighted_change)}"}

    risk_level = "medium"
    risk_factors: List[str] = []
    if isinstance(volatility, (int, float)):
        if volatility >= 5:
            risk_level = "high"
            risk_factors.append("波动放大")
        elif volatility <= 1.5:
            risk_level = "low"
            risk_factors.append("波动温和")
    if isinstance(liquidity_ratio, (int, float)):
        if liquidity_ratio < 0.02:
            risk_factors.append("流动性偏低")
        elif liquidity_ratio > 0.08:
            risk_factors.append("流动性偏高")
    if not risk_factors:
        risk_factors = ["AI暂不可用，风险需自行评估"]

    return {
        "_as_of": snapshot.get("as_of"),
        "summary": summary,
        "fundamental_view": "AI暂不可用，以下为基于市场快照的简述。",
        "technical_view": technical_view,
        "macro_view": "宏观影响需结合事件数据进一步判读。",
        "liquidity_view": liquidity_view,
        "data_conflicts": "AI不可用，冲突待确认",
        "btc_eth_view": btc_eth_view,
        "trend": {
            "direction": direction,
            "strength": strength,
            "description": trend_desc,
        },
        "key_levels": {"supports": [], "resistances": []},
        "patterns": {"detected": [], "primary": None, "description": ""},
        "sentiment": sentiment,
        "momentum": momentum,
        "risk_assessment": {"level": risk_level, "factors": risk_factors},
        "trading_suggestion": {
            "action": "wait",
            "entry_zone": None,
            "stop_loss": None,
            "take_profit": None,
            "reasoning": "AI暂不可用，先观望，等待更清晰信号。",
        },
        "btc_eth_trade_suggestion": {
            "asset": "BTC/ETH",
            "action": "wait",
            "entry_zone": None,
            "stop_loss": None,
            "take_profit": None,
            "reasoning": "AI暂不可用，先观望，等待更清晰信号。",
        },
    }


def _build_symbol_summary(symbol: str, config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    try:
        from chart_pro_v10 import get_klines, get_orderbook
        from market_data_sources import fetch_market_snapshot as _fetch_market_snapshot
        from ai_market_analysis import get_ai_market_analysis
    except Exception as exc:
        logger.warning("Market summary imports failed: %s", exc)
        return None

    df = get_klines(symbol, timeframe="1h", limit=200)
    if df is None or getattr(df, "empty", True):
        logger.warning("Market summary skipped %s: missing klines", symbol)
        return None

    try:
        current_price = float(df["close"].iloc[-1])
    except Exception:
        logger.warning("Market summary skipped %s: invalid price", symbol)
        return None

    orderbook = get_orderbook(symbol, limit=80)
    market_data = _fetch_market_snapshot(symbol) or {}
    analysis = get_ai_market_analysis(
        symbol,
        df,
        current_price,
        orderbook=orderbook,
        market_data=market_data,
        config=config,
        language="zh",
    )
    if not analysis:
        logger.warning("Market summary skipped %s: no analysis", symbol)
        return None
    return analysis


def generate_market_summary(force: bool = False) -> Optional[Dict[str, Any]]:
    """Generate scheduled market summary payload."""
    config = get_ai_market_config()
    if not config.get("enabled"):
        return None

    interval_hours = float(config.get("interval_hours", 1) or 1)
    state = _load_state(STATE_PATH)
    if not force and not _summary_due(state, interval_hours):
        return None

    mode = str(config.get("summary_mode") or config.get("mode") or "market").strip().lower()
    market_label = str(config.get("market_label") or "TOTAL_MKT")

    pin_message = mode in ("market", "macro", "global", "index")
    if mode in ("market", "macro", "global", "index"):
        result = _build_market_summary(config)
        if result:
            analysis, snapshot = result
            analysis = dict(analysis)
            analysis["_as_of"] = snapshot.get("as_of")
        else:
            logger.warning("Market summary AI unavailable; using snapshot fallback.")
            snapshot = _build_market_snapshot(config)
            analysis = _build_fallback_market_analysis(snapshot)
        items = [{"symbol": market_label, "analysis": analysis}]
        message = _format_summary_message(
            market_label,
            analysis,
            fundamental_note=_build_macro_event_note(snapshot),
        )
    else:
        symbols = _normalize_symbols(config.get("symbols")) or DEFAULT_MARKET_SYMBOLS[:1]
        items: List[Dict[str, Any]] = []
        for symbol in symbols:
            analysis = _build_symbol_summary(symbol, config)
            if analysis:
                items.append({"symbol": symbol, "analysis": analysis})
        if not items:
            return None
        messages = [_format_summary_message(item["symbol"], item["analysis"]) for item in items]
        message = "\n\n".join(msg for msg in messages if msg)

    return {
        "ts": time.time(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": message,
        "items": items,
        "pin_message": pin_message,
    }


def check_and_generate_summary() -> None:
    """Best-effort summary generation hook (no-op when disabled)."""
    try:
        payload = generate_market_summary()
    except Exception as exc:
        logger.warning("Market summary generation failed: %s", exc)
        return

    if not payload or not payload.get("message"):
        return

    try:
        from telegram import send_telegram_message
    except Exception as exc:
        logger.warning("Market summary send unavailable: %s", exc)
        return

    try:
        send_telegram_message(payload["message"], parse_mode=None, pin_message=bool(payload.get("pin_message")))
    except Exception as exc:
        logger.warning("Market summary send failed: %s", exc)
        return

    state = {"last_ts": payload.get("ts", time.time())}
    try:
        _save_state(STATE_PATH, state)
        _save_state(SUMMARY_OUTPUT_PATH, payload)
    except Exception as exc:
        logger.warning("Market summary state save failed: %s", exc)
