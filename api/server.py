#!/usr/bin/env python3
"""Signal Monitor configuration API."""
from __future__ import annotations

import ast
import base64
import hashlib
import hmac
import json
import logging
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from functools import wraps
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from flask import Flask, jsonify, request, Response, send_from_directory
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from api.clash_store import ClashStore
from api.clash_parser import parse_clash_subscription, parse_base64_subscription
from api.clash_exporter import generate_clash_yaml, generate_proxy_groups_from_nodes
from signal_monitor.market_data_sources import (
    fetch_market_snapshot,
    fetch_binance_ticker,
    fetch_news,
    fetch_trending,
)
from signal_monitor.fundamentals_sources import (
    fetch_fundamentals_snapshot,
    _fetch_fear_greed,
    fetch_macro_snapshot,
    fetch_forexfactory_calendar,
    _parse_macro_time,
    _translate_macro_title,
)
from signal_monitor.ai_api_utils import (
    AI_PROTOCOL_RESPONSES,
    build_payload,
    override_responses_token_key,
    parse_compatible_content,
    parse_responses_body,
    resolve_protocol_and_url,
    resolve_responses_token_key_override,
    should_force_responses_stream,
)
from signal_monitor.btc_forecast import build_btc_forecast
from signal_monitor.forecast_engine import build_market_forecast
from signal_monitor.nofx_data_sources import (
    fetch_nofx_competition,
    fetch_nofx_top_traders,
    fetch_nofx_public_strategies,
)
from signal_monitor.binance_copytrade_api import fetch_trader_data
from signal_monitor.trader_analyzer import analyze_trader
from signal_monitor.macro_data import load_macro_data
from signal_monitor.ccxt_data import fetch_ccxt_ticker, fetch_ccxt_orderbook, fetch_ccxt_snapshot
WEB_DIST = BASE_DIR / "web" / "dist"
SIGNAL_CONFIG_PATH = BASE_DIR / "signal_monitor" / "config.py"
ENV_PATH = BASE_DIR / ".env"
AI_SIGNAL_CONFIG = BASE_DIR / "signal_monitor" / "ai_signal_config.json"
AI_LEVELS_CONFIG = BASE_DIR / "signal_monitor" / "ai_key_levels_config.json"
AI_OVERLAYS_CONFIG = BASE_DIR / "signal_monitor" / "ai_overlays_config.json"
AI_MARKET_CONFIG = BASE_DIR / "signal_monitor" / "ai_market_summary_config.json"
ANOMALY_CONFIG = BASE_DIR / "signal_monitor" / "anomaly_config.json"
MARKET_ALERT_CONFIG = BASE_DIR / "signal_monitor" / "market_alert_config.json"
DEFAULT_FUND_SYMBOLS = ["BTC", "ETH"]
ADMIN_USERNAME = os.getenv("NOFX_ADMIN_USERNAME") or os.getenv("ADMIN_USERNAME", "root")
ADMIN_PASSWORD = os.getenv("NOFX_ADMIN_PASSWORD") or os.getenv("ADMIN_PASSWORD")
if not ADMIN_PASSWORD:
    raise ValueError("ADMIN_PASSWORD environment variable must be set")
ADMIN_TOKEN_TTL = int(os.getenv("NOFX_ADMIN_TOKEN_TTL", "86400") or 86400)
ADMIN_TOKEN_SECRET = (
    os.getenv("NOFX_ADMIN_TOKEN_SECRET")
    or os.getenv("NOFX_JWT_SECRET")
    or os.getenv("JWT_SECRET")
    or "valuescan-admin-secret"
)

app = Flask(__name__, static_folder=str(WEB_DIST), static_url_path="")
CORS(app, origins=["http://localhost:3000", "http://localhost:5000", "https://cornna.abrdns.com"], supports_credentials=True)
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)

clash_store = ClashStore(data_dir=str(BASE_DIR / "data"))

try:
    from mirofish.api import graph_bp, simulation_bp, report_bp, forecast_bp

    app.register_blueprint(graph_bp, url_prefix="/api/mirofish/graph")
    app.register_blueprint(simulation_bp, url_prefix="/api/mirofish/simulation")
    app.register_blueprint(report_bp, url_prefix="/api/mirofish/report")
    app.register_blueprint(forecast_bp, url_prefix="/api/mirofish/forecast")
except Exception as exc:
    logging.getLogger(__name__).warning("MiroFish integration unavailable: %s", exc)


def _is_docker() -> bool:
    if os.getenv("NOFX_DOCKER", "").strip().lower() in ("1", "true", "yes", "on"):
        return True
    return Path("/.dockerenv").exists()


def _setup_api_logging() -> None:
    log_file = os.getenv("NOFX_API_LOG_FILE")
    if not log_file:
        return
    level = (os.getenv("NOFX_API_LOG_LEVEL") or os.getenv("NOFX_LOG_LEVEL") or "INFO").upper()
    max_size = int(os.getenv("NOFX_LOG_MAX_SIZE", "10485760") or 10485760)
    backup_count = int(os.getenv("NOFX_LOG_BACKUP_COUNT", "3") or 3)
    log_format = os.getenv("NOFX_LOG_FORMAT") or "%(asctime)s [%(levelname)s] %(message)s"
    date_format = os.getenv("NOFX_LOG_DATE_FORMAT") or "%Y-%m-%d %H:%M:%S"

    log_path = Path(log_file)
    if not log_path.is_absolute():
        log_path = BASE_DIR / log_path
    log_path.parent.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(getattr(logging, level, logging.INFO))
    for handler in root.handlers:
        if isinstance(handler, RotatingFileHandler) and handler.baseFilename == str(log_path):
            return

    file_handler = RotatingFileHandler(
        str(log_path),
        maxBytes=max_size,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(logging.Formatter(log_format, date_format))
    root.addHandler(file_handler)


_setup_api_logging()


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64url_decode(data: str) -> Optional[bytes]:
    if not data:
        return None
    padding = "=" * (-len(data) % 4)
    try:
        return base64.urlsafe_b64decode(data + padding)
    except Exception:
        return None


def _encode_admin_token(username: str, ttl_seconds: int) -> str:
    exp = int(time.time()) + max(int(ttl_seconds or 0), 60)
    payload = json.dumps({"sub": username, "exp": exp}, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    body = _b64url_encode(payload)
    signature = hmac.new(ADMIN_TOKEN_SECRET.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{body}.{signature}"


def _decode_admin_token(token: str) -> Optional[Dict[str, Any]]:
    if not token or "." not in token:
        return None
    body, signature = token.rsplit(".", 1)
    expected = hmac.new(ADMIN_TOKEN_SECRET.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return None
    raw = _b64url_decode(body)
    if not raw:
        return None
    try:
        payload = json.loads(raw.decode("utf-8"))
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    exp = payload.get("exp")
    if not isinstance(exp, int):
        try:
            exp = int(exp)
        except Exception:
            return None
    if exp < int(time.time()):
        return None
    return payload


def _get_bearer_token() -> Optional[str]:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header:
        return None
    if auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip()
    return None


def require_admin_auth(f):
    """Decorator to require admin authentication for sensitive endpoints"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = _get_bearer_token()
        payload = _decode_admin_token(token or "")
        if not payload:
            return jsonify({"success": False, "error": "unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated_function


def _safe_eval(node: ast.AST) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.List):
        return [_safe_eval(elt) for elt in node.elts]
    if isinstance(node, ast.Tuple):
        return tuple(_safe_eval(elt) for elt in node.elts)
    if isinstance(node, ast.Dict):
        return {str(_safe_eval(k)): _safe_eval(v) for k, v in zip(node.keys, node.values)}
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        value = _safe_eval(node.operand)
        return -value if isinstance(node.op, ast.USub) else value
    if isinstance(node, ast.BinOp):
        left = _safe_eval(node.left)
        right = _safe_eval(node.right)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right
        if isinstance(node.op, ast.FloorDiv):
            return left // right
        if isinstance(node.op, ast.Mod):
            return left % right
    raise ValueError("Unsupported value")


_CONFIG_CACHE: Dict[str, tuple[Dict[str, Any], float, float]] = {}
_CONFIG_CACHE_TTL = 60.0

_FUNDAMENTALS_CACHE: Dict[str, tuple[Dict[str, Any], float]] = {}
_FUNDAMENTALS_CACHE_TTL = float(os.getenv("NOFX_FUNDAMENTALS_CACHE_TTL", "30") or 30)
_FUNDAMENTALS_EXECUTOR = ThreadPoolExecutor(max_workers=5, thread_name_prefix="FundamentalsWorker")


def _parse_config(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}

    cache_key = str(path)
    try:
        mtime = path.stat().st_mtime
    except Exception:
        mtime = 0.0

    now = time.time()
    if cache_key in _CONFIG_CACHE:
        cached_config, cached_mtime, cached_time = _CONFIG_CACHE[cache_key]
        if cached_mtime == mtime and (now - cached_time) < _CONFIG_CACHE_TTL:
            return cached_config

    try:
        content = path.read_text(encoding="utf-8")
    except Exception:
        return {}
    try:
        tree = ast.parse(content)
    except Exception:
        return {}
    config: Dict[str, Any] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name):
                key = target.id
                try:
                    config[key.lower()] = _safe_eval(node.value)
                except Exception:
                    continue

    _CONFIG_CACHE[cache_key] = (config, mtime, now)
    return config


def _config_order(path: Path) -> List[str]:
    if not path.exists():
        return []
    try:
        content = path.read_text(encoding="utf-8")
        tree = ast.parse(content)
    except Exception:
        return []
    order: List[str] = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name):
                order.append(target.id)
    return order


def _serialize_value(value: Any) -> str:
    return repr(value)


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(content, encoding="utf-8")
    os.replace(tmp_path, path)


def _write_config(path: Path, updates: Dict[str, Any]) -> None:
    existing = _parse_config(path)
    existing.update({k: v for k, v in updates.items() if v is not None})
    order = _config_order(path)

    lines: List[str] = []
    used_keys = set()
    for key in order:
        lower = key.lower()
        if lower in existing:
            lines.append(f"{key} = {_serialize_value(existing[lower])}")
            used_keys.add(lower)

    for key in sorted(k for k in existing.keys() if k not in used_keys):
        lines.append(f"{key.upper()} = {_serialize_value(existing[key])}")

    _atomic_write_text(path, "\n".join(lines) + "\n")


def _load_env() -> Dict[str, str]:
    if not ENV_PATH.exists():
        return {}
    data: Dict[str, str] = {}
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        if not line or line.strip().startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        data[key.strip()] = value.strip()
    return data


def _write_env(updates: Dict[str, str]) -> None:
    existing_lines = []
    seen = set()
    if ENV_PATH.exists():
        existing_lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
    output_lines: List[str] = []
    for line in existing_lines:
        if not line or line.strip().startswith("#") or "=" not in line:
            output_lines.append(line)
            continue
        key, _, _ = line.partition("=")
        key = key.strip()
        if key in updates:
            output_lines.append(f"{key}={updates[key]}")
            seen.add(key)
        else:
            output_lines.append(line)
    for key, value in updates.items():
        if key not in seen:
            output_lines.append(f"{key}={value}")
    _atomic_write_text(ENV_PATH, "\n".join(output_lines) + "\n")


def _load_ai_config(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_ai_config(path: Path, payload: Dict[str, Any]) -> Dict[str, Any]:
    config = _load_ai_config(path)
    config.update({k: v for k, v in payload.items() if v is not None})
    _atomic_write_text(path, json.dumps(config, ensure_ascii=False, indent=2))
    return config


def _load_json_config(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_json_config(path: Path, payload: Dict[str, Any]) -> Dict[str, Any]:
    config = _load_json_config(path)
    config.update({k: v for k, v in payload.items() if v is not None})
    _atomic_write_text(path, json.dumps(config, ensure_ascii=False, indent=2))
    return config


def _save_market_alert_config(us_market: Dict[str, Any]) -> Dict[str, Any]:
    config = _load_json_config(MARKET_ALERT_CONFIG)
    if not isinstance(config, dict):
        config = {}
    if us_market:
        existing = config.get("us_market", {})
        if not isinstance(existing, dict):
            existing = {}
        existing.update({k: v for k, v in us_market.items() if v is not None})
        config["us_market"] = existing
    _atomic_write_text(MARKET_ALERT_CONFIG, json.dumps(config, ensure_ascii=False, indent=2))
    return config


def _parse_optional_limit(raw: Optional[str]) -> Optional[int]:
    if raw is None or raw == "":
        return None
    try:
        value = int(raw)
    except ValueError:
        return None
    return value if value > 0 else None


def _ai_summary_config() -> Dict[str, Any]:
    defaults = {
        "api_key": os.getenv("AI_SUMMARY_API_KEY", "").strip(),
        "api_url": os.getenv("AI_SUMMARY_API_URL", "").strip(),
        "model": os.getenv("AI_SUMMARY_MODEL", "").strip(),
        "api_protocol": os.getenv("AI_SUMMARY_API_PROTOCOL", "auto").strip(),
    }
    config_path = BASE_DIR / "signal_monitor" / "ai_summary_config.json"
    overrides = _load_ai_config(config_path)
    defaults.update({k: v for k, v in overrides.items() if v is not None})
    return defaults


def _parse_ai_json(raw: str) -> Optional[Dict[str, Any]]:
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
            match = re.search(r"```(?:json)?\\s*(\\{.*?\\})\\s*```", cleaned, flags=re.S)
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
    return data if isinstance(data, dict) else None


def _call_ai_brief(system_prompt: str, user_prompt: str, config: Dict[str, Any], max_tokens: int) -> Optional[str]:
    api_key = (config.get("api_key") or "").strip()
    api_url = (config.get("api_url") or "").strip()
    model = (config.get("model") or "").strip()
    if not api_key or not api_url or not model:
        return None
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    timeout_sec = int(os.getenv("NOFX_AI_API_TIMEOUT", "90") or 90)
    connect_timeout = float(os.getenv("NOFX_AI_CONNECT_TIMEOUT", "15") or 15)
    protocol, resolved_url = resolve_protocol_and_url(api_url, config.get("api_protocol"))
    stream = False
    payload = build_payload(
        protocol,
        resolved_url,
        model,
        system_prompt,
        user_prompt,
        max_tokens,
        0.3,
        stream,
    )
    try:
        import requests

        session = requests.Session()
        session.trust_env = False
        if protocol == AI_PROTOCOL_RESPONSES:
            headers["Accept"] = "application/json"
        resp = session.post(resolved_url, headers=headers, json=payload, timeout=(connect_timeout, timeout_sec))
        if resp.status_code != 200:
            if protocol == AI_PROTOCOL_RESPONSES and resp.status_code == 400:
                override_key = resolve_responses_token_key_override(resp.text)
                if override_key is not None:
                    payload = override_responses_token_key(payload, override_key, max_tokens)
                    resp = session.post(
                        resolved_url,
                        headers=headers,
                        json=payload,
                        timeout=(connect_timeout, timeout_sec),
                    )
            if resp.status_code != 200:
                logging.getLogger(__name__).warning(
                    "Macro brief AI call failed: %s - %s",
                    resp.status_code,
                    resp.text[:200],
                )
                return None
        if protocol == AI_PROTOCOL_RESPONSES:
            content = parse_responses_body(resp.text)
        else:
            content = parse_compatible_content(resp.json())
        return content.strip() if content else None
    except Exception as exc:
        logging.getLogger(__name__).warning("Macro brief AI error: %s", exc)
        return None


def _ff_item_timestamp(item: Dict[str, Any]) -> float:
    dt = _parse_macro_time(item.get("date") or item.get("time") or item.get("release_time"))
    if dt:
        try:
            return float(dt.timestamp())
        except Exception:
            return 0.0
    return 0.0


def _score_ff_item(item: Dict[str, Any]) -> float:
    impact_raw = str(item.get("impact") or "").lower()
    score = 0.0
    if "high" in impact_raw or "\u9ad8" in impact_raw:
        score += 3.0
    elif "medium" in impact_raw or "\u4e2d" in impact_raw:
        score += 2.0
    elif "low" in impact_raw or "\u4f4e" in impact_raw:
        score += 1.0
    title_raw = str(item.get("title") or "")
    title_cn = _normalize_macro_title_cn(title_raw)
    text = f"{title_raw} {title_cn}".lower()
    keywords = [
        "rate",
        "interest",
        "cpi",
        "inflation",
        "pce",
        "ppi",
        "gdp",
        "payroll",
        "nonfarm",
        "nfp",
        "employment",
        "unemployment",
        "jobless",
        "pmi",
        "retail",
        "fomc",
        "fed",
        "central bank",
        "policy",
        "minutes",
        "press",
        "\u5229\u7387",
        "cpi",
        "\u901a\u80c0",
        "pce",
        "ppi",
        "gdp",
        "\u975e\u519c",
        "\u5c31\u4e1a",
        "\u5931\u4e1a",
        "\u521d\u8bf7",
        "pmi",
        "\u96f6\u552e",
        "\u592e\u884c",
        "\u7f8e\u8054\u50a8",
        "\u653f\u7b56",
        "\u8bb2\u8bdd",
        "\u7eaa\u8981",
        "\u53d1\u5e03\u4f1a",
        "\u8bae\u606f",
    ]
    for key in keywords:
        if key and key in text:
            score += 0.6
    return score


def _normalize_macro_title_cn(title_raw: str) -> str:
    raw = str(title_raw or "")
    title_cn = _translate_macro_title(raw)
    lower = raw.lower()
    suffix = ""
    if "y/y" in lower or "yoy" in lower:
        suffix = "\u540c\u6bd4"
    elif "m/m" in lower or "mom" in lower:
        suffix = "\u73af\u6bd4"
    if "core" in lower and "cpi" in lower and "\u6838\u5fc3" not in title_cn:
        title_cn = f"\u6838\u5fc3CPI{suffix}" if suffix else "\u6838\u5fc3CPI"
    if "core" in lower and "ppi" in lower and "\u6838\u5fc3" not in title_cn:
        title_cn = f"\u6838\u5fc3PPI{suffix}" if suffix else "\u6838\u5fc3PPI"
    return title_cn or raw


def _fallback_macro_highlights(items: List[Dict[str, Any]], top: int) -> Dict[str, Any]:
    ranked = sorted(items, key=_score_ff_item, reverse=True)
    highlights: List[Dict[str, Any]] = []
    seen = set()
    for item in ranked:
        title_cn = _normalize_macro_title_cn(str(item.get("title") or ""))
        impact = str(item.get("impact") or "")
        key = (title_cn, item.get("country"), item.get("date"))
        if key in seen:
            continue
        seen.add(key)
        reason_parts: List[str] = []
        if impact:
            reason_parts.append(f"\u5f71\u54cd\u7b49\u7ea7:{impact}")
        if _score_ff_item(item) >= 3:
            reason_parts.append("\u5173\u952e\u5b8f\u89c2\u6570\u636e/\u653f\u7b56")
        highlights.append(
            {
                "title": title_cn or str(item.get("title") or ""),
                "country": item.get("country") or "",
                "time": item.get("date") or "",
                "impact": impact,
                "reason": "\u3001".join(reason_parts) if reason_parts else "\u91cd\u70b9\u5173\u6ce8",
            }
        )
        if len(highlights) >= max(1, top):
            break
    overview_parts = [
        f"{h.get('title','')}" for h in highlights if isinstance(h, dict) and h.get("title")
    ]
    analysis = "\u91cd\u70b9\u5173\u6ce8: " + ("\uff1b".join(overview_parts) if overview_parts else "\u6682\u65e0")
    return {"highlights": highlights, "analysis": analysis, "ai_used": False}


def _ai_macro_highlights(items: List[Dict[str, Any]], top: int) -> Optional[Dict[str, Any]]:
    config = _ai_summary_config()
    system_prompt = (
        "\u4f60\u662f\u5b8f\u89c2\u65b0\u95fb/\u7ecf\u6d4e\u6570\u636e\u5206\u6790\u5e08\u3002"
        "\u8bf7\u53ea\u4f9d\u636e\u8f93\u5165\u6570\u636e\uff0c\u7528\u4e2d\u6587\u8f93\u51fa\u4e25\u683cJSON\u3002"
    )
    payload_items: List[Dict[str, Any]] = []
    for item in items:
        title_raw = str(item.get("title") or "")
        payload_items.append(
            {
                "title": _normalize_macro_title_cn(title_raw),
                "country": item.get("country") or "",
                "time": item.get("date") or "",
                "impact": item.get("impact") or "",
                "actual": item.get("actual") or "",
                "forecast": item.get("forecast") or "",
                "previous": item.get("previous") or "",
            }
        )
    prompt_lines = [
        f"\u8fd9\u662f\u6700\u8fd1{len(items)}\u6761\u7ecf\u6d4e\u65e5\u5386\u4e8b\u4ef6(JSON):",
        json.dumps(payload_items, ensure_ascii=True, separators=(",", ":")),
        f"\u8bf7\u6311\u9009\u6700\u91cd\u8981\u7684{max(1, top)}\u6761\uff0c\u8f93\u51faJSON:",
        '{"highlights":[{"title":"","country":"","time":"","impact":"","reason":""}],"analysis":""}',
        "\u8981\u6c42:",
        "1) \u4e0d\u8981\u7f16\u9020\uff0c\u4e0d\u786c\u8bf4\u3002",
        "2) \u201canalysis\u201d\u7528\u4e00\u5230\u4e24\u53e5\u6982\u62ec\u6574\u4f53\u5f71\u54cd\u3002",
        "3) \u8bed\u8a00\u5fc5\u987b\u4e3a\u4e2d\u6587\u3002",
    ]
    raw = _call_ai_brief(system_prompt, "\n".join(prompt_lines), config, max_tokens=1200)
    if not raw:
        return None
    parsed = _parse_ai_json(raw)
    if parsed:
        parsed["ai_used"] = True
        return parsed
    return None


def _call_ai_test(api_url: str, api_key: str, model: str, api_protocol: Optional[str] = None) -> Dict[str, Any]:
    import requests
    from signal_monitor.ai_api_utils import (
        AI_PROTOCOL_RESPONSES,
        build_payload,
        override_responses_token_key,
        resolve_protocol_and_url,
        resolve_responses_token_key_override,
        should_force_responses_stream,
    )

    protocol, resolved_url = resolve_protocol_and_url(api_url, api_protocol)
    stream = should_force_responses_stream(resolved_url, protocol)
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    if protocol == AI_PROTOCOL_RESPONSES:
        headers["Accept"] = "text/event-stream" if stream else "application/json"
    payload = build_payload(
        protocol,
        resolved_url,
        model,
        "",
        "test",
        50,
        0.2,
        stream,
    )
    resp = requests.post(resolved_url, headers=headers, json=payload, timeout=30)
    if resp.status_code != 200:
        if protocol == AI_PROTOCOL_RESPONSES and resp.status_code == 400:
            override_key = resolve_responses_token_key_override(resp.text)
            if override_key is not None:
                payload = override_responses_token_key(payload, override_key, 50)
                resp = requests.post(resolved_url, headers=headers, json=payload, timeout=30)
        if resp.status_code != 200:
            return {"success": False, "message": resp.text[:200]}
    return {"success": True}


def _systemctl_available() -> bool:
    return shutil.which("systemctl") is not None


def _systemctl(action: str, service: str) -> bool:
    if platform.system().lower().startswith("win"):
        return False
    if not _systemctl_available():
        return False
    try:
        subprocess.run(["systemctl", action, service], check=True, capture_output=True, text=True)
        return True
    except Exception:
        return False


def _systemctl_status(service: str) -> str:
    if platform.system().lower().startswith("win"):
        return "stopped"
    if not _systemctl_available():
        return "stopped"
    try:
        result = subprocess.run(
            ["systemctl", "is-active", service],
            check=False,
            capture_output=True,
            text=True,
        )
        status = result.stdout.strip()
        return "running" if status == "active" else "stopped"
    except Exception:
        return "stopped"


def _journal_logs(unit: str, lines: int) -> List[Dict[str, Any]]:
    if platform.system().lower().startswith("win"):
        return []
    if not shutil.which("journalctl"):
        return []
    try:
        result = subprocess.run(
            ["journalctl", "-u", unit, "-n", str(lines), "--no-pager", "-o", "json"],
            check=False,
            capture_output=True,
            text=True,
        )
        logs: List[Dict[str, Any]] = []
        for line in result.stdout.splitlines():
            try:
                entry = json.loads(line)
            except Exception:
                continue
            ts_raw = entry.get("__REALTIME_TIMESTAMP")
            ts = int(int(ts_raw) / 1_000_000) if ts_raw else int(time.time())
            logs.append(
                {
                    "timestamp": ts,
                    "level": entry.get("PRIORITY", "6"),
                    "component": unit,
                    "message": entry.get("MESSAGE", ""),
                }
            )
        return logs
    except Exception:
        return []


def _resolve_log_file(unit: str) -> Optional[Path]:
    if unit == "signal-monitor":
        log_file = os.getenv("NOFX_LOG_FILE") or os.getenv("LOG_FILE")
        if not log_file:
            log_file = str(BASE_DIR / "data" / "signal_monitor.log")
    else:
        log_file = os.getenv("NOFX_API_LOG_FILE") or os.getenv("API_LOG_FILE")
        if not log_file:
            return None
    path = Path(log_file)
    if not path.is_absolute():
        path = BASE_DIR / path
    return path


def _docker_monitor_status() -> str:
    log_path = _resolve_log_file("signal-monitor")
    if not log_path or not log_path.exists():
        return "running"
    threshold = int(os.getenv("NOFX_MONITOR_HEARTBEAT_SEC", "900") or 900)
    age = time.time() - log_path.stat().st_mtime
    return "running" if age <= threshold else "stopped"


def _parse_log_line(line: str, unit: str) -> Optional[Dict[str, Any]]:
    line = line.strip()
    if not line:
        return None
    ts = int(time.time())
    level = "6"
    message = line
    match = re.match(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \[([^\]]+)\] (.*)$", line)
    if match:
        dt_raw, level_raw, message = match.groups()
        try:
            dt = datetime.strptime(dt_raw, "%Y-%m-%d %H:%M:%S")
            ts = int(dt.replace(tzinfo=timezone.utc).timestamp())
        except Exception:
            ts = int(time.time())
        level_name = level_raw.strip().upper()
        level_map = {
            "DEBUG": "7",
            "INFO": "6",
            "WARNING": "4",
            "WARN": "4",
            "ERROR": "3",
            "CRITICAL": "2",
        }
        level = level_map.get(level_name, "6")
    return {
        "timestamp": ts,
        "level": level,
        "component": unit,
        "message": message,
    }


def _file_logs(unit: str, lines: int) -> List[Dict[str, Any]]:
    path = _resolve_log_file(unit)
    if not path or not path.exists():
        return []
    try:
        raw = path.read_bytes()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("gb18030", errors="replace")
        raw_lines = text.splitlines()
    except Exception:
        return []
    logs: List[Dict[str, Any]] = []
    for line in raw_lines[-lines:]:
        entry = _parse_log_line(line, unit)
        if entry:
            logs.append(entry)
    return logs


@app.route("/api/health", methods=["GET"])
def healthcheck() -> Response:
    return jsonify({"status": "ok", "timestamp": int(time.time())})


@app.route("/api/v1/admin/login", methods=["POST"])
def api_v1_admin_login() -> Response:
    payload = request.get_json(silent=True) or {}
    username = str(payload.get("username") or "").strip()
    password = str(payload.get("password") or "").strip()
    if not username or not password:
        return jsonify({"success": False, "error": "username and password required"}), 400
    if username != ADMIN_USERNAME or password != ADMIN_PASSWORD:
        return jsonify({"success": False, "error": "invalid credentials"}), 401
    token = _encode_admin_token(username, ADMIN_TOKEN_TTL)
    expires_at = datetime.fromtimestamp(int(time.time()) + ADMIN_TOKEN_TTL, timezone.utc).isoformat()
    return jsonify({"success": True, "token": token, "user": username, "expires_at": expires_at})


@app.route("/api/v1/admin/check", methods=["GET"])
def api_v1_admin_check() -> Response:
    token = _get_bearer_token()
    payload = _decode_admin_token(token or "")
    if not payload:
        return jsonify({"success": False, "error": "unauthorized"}), 401
    exp = payload.get("exp")
    expires_at = None
    if isinstance(exp, int):
        expires_at = datetime.fromtimestamp(exp, timezone.utc).isoformat()
    return jsonify({"success": True, "user": payload.get("sub"), "expires_at": expires_at})


@app.route("/api/config", methods=["GET"])
def get_config() -> Response:
    signal_cfg = _parse_config(SIGNAL_CONFIG_PATH)
    anomaly_cfg = _load_json_config(ANOMALY_CONFIG)
    market_alert_cfg = _load_json_config(MARKET_ALERT_CONFIG)
    us_market_cfg = market_alert_cfg.get("us_market", {}) if isinstance(market_alert_cfg, dict) else {}
    signal_cfg["realtime_market_enabled"] = _realtime_market_enabled()
    logging_cfg = {
        "log_level": signal_cfg.get("log_level", "INFO"),
        "log_to_file": signal_cfg.get("log_to_file", True),
        "log_file": signal_cfg.get("log_file", "signal_monitor.log"),
        "log_max_size": signal_cfg.get("log_max_size", 10 * 1024 * 1024),
        "log_backup_count": signal_cfg.get("log_backup_count", 5),
        "log_format": signal_cfg.get("log_format", "%(asctime)s [%(levelname)s] %(message)s"),
        "log_date_format": signal_cfg.get("log_date_format", "%Y-%m-%d %H:%M:%S"),
    }
    env = _load_env()
    environment_cfg = {}
    system_cfg = {
        "nofx_backend_port": 8080,
        "nofx_frontend_port": 3000,
        "nofx_timezone": "Asia/Shanghai",
        "jwt_secret": "",
        "data_encryption_key": "",
        "rsa_private_key": "",
        "transport_encryption": False,
    }
    return jsonify({
        "signal": signal_cfg,
        "logging": logging_cfg,
        "environment": environment_cfg,
        "system": system_cfg,
        "anomaly": anomaly_cfg,
        "us_market": us_market_cfg,
    })


@app.route("/api/config", methods=["POST"])
@require_admin_auth
@limiter.limit("10 per minute")
def save_config() -> Response:
    payload = request.get_json(silent=True) or {}
    signal_cfg = payload.get("signal") or {}
    logging_cfg = payload.get("logging") or {}
    anomaly_cfg = payload.get("anomaly") or {}
    us_market_cfg = payload.get("us_market") or {}

    merged = dict(signal_cfg)
    merged.update(
        {
            "log_level": logging_cfg.get("log_level"),
            "log_to_file": logging_cfg.get("log_to_file"),
            "log_file": logging_cfg.get("log_file"),
            "log_max_size": logging_cfg.get("log_max_size"),
            "log_backup_count": logging_cfg.get("log_backup_count"),
            "log_format": logging_cfg.get("log_format"),
            "log_date_format": logging_cfg.get("log_date_format"),
        }
    )

    _write_config(SIGNAL_CONFIG_PATH, merged)

    env_cfg = payload.get("environment") or {}
    if env_cfg:
        _write_env({})
    if anomaly_cfg:
        _save_json_config(ANOMALY_CONFIG, anomaly_cfg)
    if us_market_cfg:
        _save_market_alert_config(us_market_cfg)

    return jsonify({"success": True})


@app.route("/api/ai/signal/config", methods=["GET"])
def get_ai_signal_config() -> Response:
    return jsonify(_load_ai_config(AI_SIGNAL_CONFIG))


@app.route("/api/ai/signal/config", methods=["POST"])
@require_admin_auth
@limiter.limit("10 per minute")
def set_ai_signal_config() -> Response:
    payload = request.get_json(silent=True) or {}
    return jsonify(_save_ai_config(AI_SIGNAL_CONFIG, payload))


@app.route("/api/ai/signal/test", methods=["POST"])
def test_ai_signal() -> Response:
    cfg = _load_ai_config(AI_SIGNAL_CONFIG)
    if not cfg.get("api_key"):
        return jsonify({"success": False, "message": "API Key ???"})
    return jsonify(_call_ai_test(cfg.get("api_url"), cfg.get("api_key"), cfg.get("model"), cfg.get("api_protocol")))


@app.route("/api/ai/levels/config", methods=["GET"])
def get_ai_levels_config() -> Response:
    return jsonify(_load_ai_config(AI_LEVELS_CONFIG))


@app.route("/api/ai/levels/config", methods=["POST"])
@require_admin_auth
@limiter.limit("10 per minute")
def set_ai_levels_config() -> Response:
    payload = request.get_json(silent=True) or {}
    return jsonify(_save_ai_config(AI_LEVELS_CONFIG, payload))


@app.route("/api/ai/levels/test", methods=["POST"])
def test_ai_levels() -> Response:
    cfg = _load_ai_config(AI_LEVELS_CONFIG)
    if not cfg.get("api_key"):
        return jsonify({"success": False, "message": "API Key ???"})
    return jsonify(_call_ai_test(cfg.get("api_url"), cfg.get("api_key"), cfg.get("model"), cfg.get("api_protocol")))


@app.route("/api/ai/overlays/config", methods=["GET"])
def get_ai_overlays_config() -> Response:
    return jsonify(_load_ai_config(AI_OVERLAYS_CONFIG))


@app.route("/api/ai/overlays/config", methods=["POST"])
@require_admin_auth
@limiter.limit("10 per minute")
def set_ai_overlays_config() -> Response:
    payload = request.get_json(silent=True) or {}
    return jsonify(_save_ai_config(AI_OVERLAYS_CONFIG, payload))


@app.route("/api/ai/overlays/test", methods=["POST"])
def test_ai_overlays() -> Response:
    cfg = _load_ai_config(AI_OVERLAYS_CONFIG)
    if not cfg.get("api_key"):
        return jsonify({"success": False, "message": "API Key ???"})
    return jsonify(_call_ai_test(cfg.get("api_url"), cfg.get("api_key"), cfg.get("model"), cfg.get("api_protocol")))


@app.route("/api/ai/market/config", methods=["GET"])
def get_ai_market_config() -> Response:
    return jsonify(_load_ai_config(AI_MARKET_CONFIG))


@app.route("/api/ai/market/config", methods=["POST"])
@require_admin_auth
@limiter.limit("10 per minute")
def set_ai_market_config() -> Response:
    payload = request.get_json(silent=True) or {}
    return jsonify(_save_ai_config(AI_MARKET_CONFIG, payload))


@app.route("/api/ai/market/test", methods=["POST"])
def test_ai_market() -> Response:
    cfg = _load_ai_config(AI_MARKET_CONFIG)
    if not cfg.get("api_key"):
        return jsonify({"success": False, "message": "API Key ???"})
    return jsonify(_call_ai_test(cfg.get("api_url"), cfg.get("api_key"), cfg.get("model"), cfg.get("api_protocol")))


@app.route("/api/services/status", methods=["GET"])
def services_status() -> Response:
    if _is_docker():
        services = {
            "signal-monitor": _docker_monitor_status(),
            "signal-api": "running",
        }
        return jsonify(services)
    services = {
        "signal-monitor": _systemctl_status("signal-monitor"),
        "signal-api": _systemctl_status("signal-api"),
    }
    return jsonify(services)


@app.route("/api/services/<action>", methods=["POST"])
@require_admin_auth
@limiter.limit("10 per minute")
def services_action(action: str) -> Response:
    payload = request.get_json(silent=True) or {}
    service = payload.get("service")
    if action not in {"start", "stop", "restart"}:
        return jsonify({"success": False, "message": "Invalid action"}), 400
    if _is_docker():
        return jsonify({"success": False, "message": "Service management is handled by Docker"}), 400
    allowed = {"signal-monitor", "signal-api"}
    if service not in allowed:
        return jsonify({"success": False, "message": "Service not allowed"}), 400
    ok = _systemctl(action, service)
    return jsonify({"success": ok})


@app.route("/api/logs/<service>", methods=["GET"])
def get_logs(service: str) -> Response:
    mapping = {
        "signal": "signal-monitor",
        "api": "signal-api",
    }
    unit = mapping.get(service)
    if not unit:
        return jsonify({"logs": []})
    lines = int(request.args.get("lines", 2000))
    logs = _journal_logs(unit, lines)
    if not logs:
        logs = _file_logs(unit, lines)
    return jsonify({"logs": logs})


@app.route("/api/db/status", methods=["GET"])
def get_db_status() -> Response:
    try:
        from signal_monitor.database import MessageDatabase

        db = MessageDatabase()
        stats = db.get_statistics()
        return jsonify({"available": True, "stats": stats})
    except Exception as exc:
        return jsonify({"available": False, "error": str(exc)}), 500


def _fetch_messages_by_types(types: List[int], limit: int) -> List[Dict[str, Any]]:
    from signal_monitor.database import MessageDatabase

    db = MessageDatabase()
    if not types:
        return []
    placeholders = ",".join(["?"] * len(types))
    query = (
        "SELECT message_id, message_type, symbol, title, created_time "
        "FROM processed_messages "
        f"WHERE message_type IN ({placeholders}) "
        "ORDER BY created_time DESC "
        "LIMIT ?"
    )
    rows = []
    try:
        rows = db.cursor.execute(query, [*types, limit]).fetchall()
    except Exception:
        return []
    results = []
    for row in rows:
        results.append(
            {
                "id": row[0],
                "type": str(row[1]),
                "symbol": row[2] or "",
                "title": row[3] or "",
                "timestamp": row[4] or 0,
            }
        )
    return results


def _normalize_symbols(raw: Optional[str]) -> List[str]:
    if not raw:
        return DEFAULT_FUND_SYMBOLS[:]
    symbols: List[str] = []
    for part in raw.replace(";", ",").split(","):
        sym = part.strip().upper().replace("$", "")
        if sym:
            symbols.append(sym)
    return symbols or DEFAULT_FUND_SYMBOLS[:]


def _realtime_market_enabled() -> bool:
    env_raw = os.getenv("NOFX_REALTIME_MARKET_ENABLED")
    if env_raw is not None and env_raw != "":
        return str(env_raw).strip().lower() in ("1", "true", "yes", "on")
    signal_cfg = _parse_config(SIGNAL_CONFIG_PATH)
    raw = signal_cfg.get("realtime_market_enabled")
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        return raw.strip().lower() in ("1", "true", "yes", "on")
    return True


@app.route("/api/signals", methods=["GET"])
def get_signals() -> Response:
    limit = int(request.args.get("limit", 5))
    signals = _fetch_messages_by_types([110, 113], limit)
    return jsonify({"signals": signals})


@app.route("/api/alerts", methods=["GET"])
def get_alerts() -> Response:
    return jsonify({"alerts": [], "disabled": True})


@app.route("/api/fundamentals", methods=["GET"])
def get_fundamentals() -> Response:
    symbols = _normalize_symbols(request.args.get("symbols"))
    include_macro = request.args.get("include_macro", "1").lower() in ("1", "true", "yes", "on")
    if not _realtime_market_enabled():
        payload = [{"symbol": symbol, "available": False, "fundamentals": None} for symbol in symbols]
        return jsonify({"timestamp": int(time.time()), "symbols": symbols, "data": payload})

    # Check cache first
    now = time.time()
    cache_key = f"{','.join(sorted(symbols))}:{int(include_macro)}"
    if cache_key in _FUNDAMENTALS_CACHE:
        cached_data, cached_time = _FUNDAMENTALS_CACHE[cache_key]
        if (now - cached_time) < _FUNDAMENTALS_CACHE_TTL:
            return jsonify(cached_data)

    # Fetch data concurrently
    def fetch_symbol_data(symbol: str) -> Dict[str, Any]:
        snapshot = fetch_market_snapshot(symbol) or {}
        fundamentals = fetch_fundamentals_snapshot(symbol, include_macro=include_macro)
        if snapshot:
            item = dict(snapshot)
            item["symbol"] = symbol
            item["available"] = True
            if fundamentals:
                item["fundamentals"] = fundamentals
        else:
            item = {"symbol": symbol, "available": False, "fundamentals": fundamentals}
        return item

    payload = []
    future_to_symbol = {_FUNDAMENTALS_EXECUTOR.submit(fetch_symbol_data, symbol): symbol for symbol in symbols}
    for future in as_completed(future_to_symbol, timeout=15):
        try:
            result = future.result(timeout=5)
            payload.append(result)
        except Exception as e:
            symbol = future_to_symbol[future]
            payload.append({"symbol": symbol, "available": False, "fundamentals": None, "error": str(e)})

    response_data = {"timestamp": int(time.time()), "symbols": symbols, "data": payload}
    _FUNDAMENTALS_CACHE[cache_key] = (response_data, now)
    return jsonify(response_data)


@app.route("/api/clash/config", methods=["GET"])
def get_clash_config() -> Response:
    return jsonify(clash_store.get_config())


@app.route("/api/clash/config", methods=["POST"])
@require_admin_auth
@limiter.limit("10 per minute")
def save_clash_config() -> Response:
    payload = request.get_json(silent=True) or {}
    clash_store.save_config(payload)
    return jsonify({"success": True})


@app.route("/api/clash/nodes", methods=["GET"])
def get_clash_nodes() -> Response:
    return jsonify(clash_store.get_nodes())


@app.route("/api/clash/nodes", methods=["POST"])
@require_admin_auth
@limiter.limit("10 per minute")
def save_clash_nodes() -> Response:
    payload = request.get_json(silent=True) or []
    if not isinstance(payload, list):
        return jsonify({"success": False, "message": "nodes must be a list"}), 400
    clash_store.save_nodes(payload)
    return jsonify({"success": True})


@app.route("/api/clash/groups", methods=["GET"])
def get_clash_groups() -> Response:
    return jsonify(clash_store.get_proxy_groups())


@app.route("/api/clash/groups", methods=["POST"])
@require_admin_auth
@limiter.limit("10 per minute")
def save_clash_groups() -> Response:
    payload = request.get_json(silent=True) or {}
    groups = payload.get("groups")
    if not isinstance(groups, list):
        return jsonify({"success": False, "message": "groups must be a list"}), 400
    clash_store.save_proxy_groups(groups)
    return jsonify({"success": True})


@app.route("/api/clash/groups/generate", methods=["POST"])
def generate_clash_groups() -> Response:
    nodes = clash_store.get_nodes()
    groups = generate_proxy_groups_from_nodes(nodes)
    clash_store.save_proxy_groups(groups)
    return jsonify({"groups": groups})


@app.route("/api/clash/subscription/update", methods=["POST"])
@require_admin_auth
@limiter.limit("5 per minute")
def update_clash_subscription() -> Response:
    payload = request.get_json(silent=True) or {}
    url = payload.get("url")
    sub_type = payload.get("type", "clash")
    if not url:
        return jsonify({"success": False, "message": "url required"}), 400
    import requests

    resp = requests.get(url, timeout=30)
    if resp.status_code != 200:
        return jsonify({"success": False, "message": "fetch failed"}), 400
    content = resp.text
    nodes: List[Dict[str, Any]] = []
    groups: List[Dict[str, Any]] = []
    if sub_type == "clash":
        nodes, groups, rules, proxy_providers, rule_providers = parse_clash_subscription(content)
        if proxy_providers is not None:
            config = clash_store.get_config()
            config["proxyProviders"] = proxy_providers
            clash_store.save_config(config)
        if rule_providers is not None:
            config = clash_store.get_config()
            config["ruleProviders"] = rule_providers
            clash_store.save_config(config)
        if rules is not None:
            config = clash_store.get_config()
            config["rules"] = rules
            clash_store.save_config(config)
    else:
        nodes = parse_base64_subscription(content)
    return jsonify({"nodes": nodes, "groups": groups})


@app.route("/api/clash/test-node", methods=["POST"])
def test_clash_node() -> Response:
    payload = request.get_json(silent=True) or {}
    node_id = payload.get("nodeId") or ""
    return jsonify({"nodeId": node_id, "delay": -1, "success": False, "error": "?????"})


@app.route("/api/clash/stats", methods=["GET"])
def clash_stats() -> Response:
    return jsonify({"uploadTotal": 0, "downloadTotal": 0, "connections": 0, "uploadSpeed": 0, "downloadSpeed": 0})


@app.route("/api/clash/service/status", methods=["GET"])
def clash_service_status() -> Response:
    service_name = os.getenv("NOFX_CLASH_SERVICE", "clash")
    return jsonify({"status": _systemctl_status(service_name)})


@app.route("/api/clash/service/<action>", methods=["POST"])
def clash_service_action(action: str) -> Response:
    service_name = os.getenv("NOFX_CLASH_SERVICE", "clash")
    if action not in {"start", "stop", "restart"}:
        return jsonify({"success": False, "message": "Invalid action"}), 400
    ok = _systemctl(action, service_name)
    return jsonify({"success": ok})


@app.route("/api/clash/export", methods=["GET"])
def export_clash_config() -> Response:
    config = clash_store.get_config()
    nodes = clash_store.get_nodes()
    yaml_text = generate_clash_yaml(config, nodes)
    return Response(yaml_text, mimetype="text/yaml")


# ==================== Trader Evaluation API ====================

@app.route("/api/trader/evaluate/<portfolio_id>", methods=["GET"])
def evaluate_trader(portfolio_id: str) -> Response:
    """获取交易员评测数据（JSON格式）"""
    try:
        trader_data = fetch_trader_data(portfolio_id)
        if not trader_data:
            return jsonify({"success": False, "error": "无法获取交易员数据"}), 404

        result = analyze_trader(trader_data)
        m = result.metrics

        # 构建完整的JSON响应
        response = {
            "success": True,
            "timestamp": int(time.time()),
            "portfolio_id": portfolio_id,
            "basic_info": {
                "nickname": m.nickname,
                "follower_count": m.follower_count,
                "aum": m.aum,
            },
            "performance": {
                "roi_7d": round(m.roi_7d, 2),
                "roi_30d": round(m.roi_30d, 2),
                "roi_90d": round(m.roi_90d, 2),
                "total_roi": round(m.total_roi, 2),
                "win_rate": round(m.win_rate, 4),
                "max_drawdown": round(m.max_drawdown, 2),
                "sharpe_ratio": round(m.sharpe_ratio, 2),
                "profit_factor": round(m.profit_factor, 2),
            },
            "trading_style": {
                "style": m.trading_style,
                "holding_style": m.holding_style,
                "trade_count": m.trade_count,
                "trade_frequency": round(m.trade_frequency, 2),
                "avg_holding_hours": round(m.avg_holding_hours, 2),
                "avg_leverage": round(m.avg_leverage, 2),
                "max_leverage": round(m.max_leverage, 2),
                "long_ratio": round(m.long_ratio, 4),
            },
            "coin_distribution": [
                {"asset": c.get("asset", ""), "volume": round(c.get("volume", 0), 2)}
                for c in m.coin_distribution[:10]
            ],
            "preferred_pairs": m.preferred_pairs[:10],
            "risk_assessment": {
                "level": m.risk_level,
                "score": m.risk_score,
                "margin_behavior": m.margin_behavior,
                "margin_concern_level": m.margin_concern_level,
                "margin_addition_count": m.margin_addition_count,
                "margin_addition_ratio": round(m.margin_addition_ratio, 4),
                "stop_loss_usage_rate": round(m.stop_loss_usage_rate, 4),
            },
            "analysis": {
                "strengths": result.strengths,
                "weaknesses": result.weaknesses,
                "risk_factors": result.risk_factors,
                "summary": result.summary,
            },
        }
        return jsonify(response)

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/trader/raw/<portfolio_id>", methods=["GET"])
def get_trader_raw_data(portfolio_id: str) -> Response:
    """获取交易员原始数据"""
    try:
        trader_data = fetch_trader_data(portfolio_id)
        if not trader_data:
            return jsonify({"success": False, "error": "无法获取交易员数据"}), 404

        return jsonify({
            "success": True,
            "timestamp": int(time.time()),
            "portfolio_id": portfolio_id,
            "raw_data": trader_data.raw_data,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ==================== API v1 - 数据源开放接口 ====================

@app.route("/api/v1/help", methods=["GET"])
def api_v1_help() -> Response:
    """API使用帮助"""
    return jsonify({
        "version": "1.0",
        "base_url": "https://cornna.abrdns.com/api/v1",
        "endpoints": {
            "market": {
                "ticker": {"path": "/market/ticker/<symbol>", "method": "GET", "desc": "Binance实时行情", "params": {"symbol": "币种如BTC/ETH"}},
                "snapshot": {"path": "/market/snapshot/<symbol>", "method": "GET", "desc": "聚合行情快照(多数据源)", "params": {"symbol": "币种"}},
                "news": {"path": "/market/news", "method": "GET", "desc": "加密货币新闻", "params": {"limit": "数量(默认10)"}},
                "trending": {"path": "/market/trending", "method": "GET", "desc": "热门币种", "params": {"limit": "数量(默认10)"}},
                "btc_forecast": {
                    "path": "/market/btc-forecast",
                    "method": "GET",
                    "desc": "BTC forecast",
                    "params": {"use_llm": "optional 1/0 to enable AI forecast"},
                },
                "forecast": {
                    "path": "/market/forecast/<symbol>",
                    "method": "GET",
                    "desc": "Symbol forecast (crypto/stocks/futures)",
                    "params": {"symbol": "asset symbol", "use_llm": "optional 1/0 to enable AI forecast"},
                },
            },
            "fundamentals": {
                "symbol": {"path": "/fundamentals/<symbol>", "method": "GET", "desc": "币种基本面数据", "params": {"symbol": "币种", "include_macro": "是否包含宏观数据(默认true)"}},
                "sentiment": {"path": "/fundamentals/sentiment", "method": "GET", "desc": "恐惧贪婪指数"},
            },
            "macro": {
                "data": {"path": "/macro/data", "method": "GET", "desc": "宏观数据(经济日历+数据发布)"},
            },
            "exchange": {
                "ticker": {"path": "/exchange/ticker/<symbol>", "method": "GET", "desc": "CCXT交易所行情", "params": {"symbol": "币种"}},
                "orderbook": {"path": "/exchange/orderbook/<symbol>", "method": "GET", "desc": "订单簿", "params": {"symbol": "币种", "limit": "深度(默认20)"}},
                "snapshot": {"path": "/exchange/snapshot/<symbol>", "method": "GET", "desc": "完整快照(含流动性)", "params": {"symbol": "币种"}},
            },
            "trader": {
                "evaluate": {"path": "/trader/evaluate/<portfolio_id>", "method": "GET", "desc": "交易员评测", "params": {"portfolio_id": "交易员ID"}},
                "raw": {"path": "/trader/raw/<portfolio_id>", "method": "GET", "desc": "交易员原始数据", "params": {"portfolio_id": "交易员ID"}},
            },
            "external": {
                "competition": {"path": "/external/competition", "method": "GET", "desc": "Competition leaderboard", "params": {"limit": "optional max items"}},
                "top_traders": {"path": "/external/top-traders", "method": "GET", "desc": "Top traders", "params": {"limit": "optional max items"}},
                "strategies_public": {"path": "/external/strategies/public", "method": "GET", "desc": "Public strategies", "params": {"limit": "optional max items"}},
            },
        },
        "examples": {
            "external_competition": "/api/v1/external/competition?limit=5",
            "external_top_traders": "/api/v1/external/top-traders",
            "external_strategies": "/api/v1/external/strategies/public?limit=10",
            "market_ticker": "/api/v1/market/ticker/BTC",
            "market_btc_forecast": "/api/v1/market/btc-forecast",
            "market_forecast": "/api/v1/market/forecast/BTC",
            "market_forecast_gold": "/api/v1/market/forecast/GC=F",
            "fundamentals": "/api/v1/fundamentals/ETH",
            "trader_evaluate": "/api/v1/trader/evaluate/4826460952808447745",
        },
    })


@app.route("/api/v1/market/ticker/<symbol>", methods=["GET"])
def api_v1_market_ticker(symbol: str) -> Response:
    """Binance实时行情"""
    data = fetch_binance_ticker(symbol)
    if not data:
        return jsonify({"success": False, "error": "获取行情失败"}), 404
    return jsonify({"success": True, "timestamp": int(time.time()), "symbol": symbol.upper(), "data": data})


@app.route("/api/v1/market/snapshot/<symbol>", methods=["GET"])
def api_v1_market_snapshot(symbol: str) -> Response:
    """聚合行情快照"""
    data = fetch_market_snapshot(symbol)
    if not data:
        return jsonify({"success": False, "error": "获取行情失败"}), 404
    return jsonify({"success": True, "timestamp": int(time.time()), "symbol": symbol.upper(), "data": data})


@app.route("/api/v1/market/news", methods=["GET"])
def api_v1_market_news() -> Response:
    """加密货币新闻"""
    limit = int(request.args.get("limit", 10))
    data = fetch_news(limit)
    return jsonify({"success": True, "timestamp": int(time.time()), "count": len(data), "data": data})


@app.route("/api/v1/market/trending", methods=["GET"])
def api_v1_market_trending() -> Response:
    """热门币种"""
    limit = int(request.args.get("limit", 10))
    data = fetch_trending(limit)
    return jsonify({"success": True, "timestamp": int(time.time()), "count": len(data), "data": data})


@app.route("/api/v1/market/btc-forecast", methods=["GET"])
def api_v1_market_btc_forecast() -> Response:
    """BTC forecast"""
    use_llm_raw = request.args.get("use_llm")
    use_llm = None
    if use_llm_raw is not None:
        use_llm = use_llm_raw.strip().lower() in ("1", "true", "yes", "on")
    data = build_btc_forecast("BTC", use_llm=use_llm)
    if not data:
        return jsonify({"success": False, "error": "Failed to build BTC forecast"}), 502
    return jsonify({"success": True, "timestamp": int(time.time()), "data": data})


@app.route("/api/v1/macro/calendar", methods=["GET"])
def api_v1_macro_calendar() -> Response:
    """Macro calendar items (merged)."""
    limit = _parse_optional_limit(request.args.get("limit")) or 50
    snapshot = fetch_macro_snapshot()
    macro = snapshot.get("macro") if isinstance(snapshot, dict) else {}
    calendar = macro.get("calendar") if isinstance(macro, dict) else {}
    items = calendar.get("items") if isinstance(calendar, dict) else []
    if not isinstance(items, list):
        items = []
    if limit:
        items = items[:limit]
    return jsonify({"success": True, "timestamp": int(time.time()), "count": len(items), "data": items})


@app.route("/api/v1/macro/forexfactory", methods=["GET"])
def api_v1_macro_forexfactory() -> Response:
    """ForexFactory calendar (free source)."""
    limit = _parse_optional_limit(request.args.get("limit")) or 50
    top = _parse_optional_limit(request.args.get("top")) or 5
    use_ai = request.args.get("ai", "0").strip().lower() in ("1", "true", "yes", "on")
    payload = fetch_forexfactory_calendar()
    items: List[Dict[str, Any]] = []
    if isinstance(payload, dict):
        calendar = payload.get("calendar") if isinstance(payload.get("calendar"), dict) else {}
        items = calendar.get("items") if isinstance(calendar, dict) else []
    if not isinstance(items, list):
        items = []
    items = sorted(items, key=_ff_item_timestamp, reverse=True)
    if limit:
        items = items[:limit]
    summary: Optional[Dict[str, Any]] = None
    if use_ai:
        summary = _ai_macro_highlights(items, top) or _fallback_macro_highlights(items, top)
    return jsonify(
        {
            "success": True,
            "timestamp": int(time.time()),
            "source": "forexfactory",
            "count": len(items),
            "data": items,
            "summary": summary,
        }
    )


@app.route("/api/v1/market/forecast/<symbol>", methods=["GET"])
def api_v1_market_forecast(symbol: str) -> Response:
    """Symbol forecast"""
    use_llm_raw = request.args.get("use_llm")
    use_llm = None
    if use_llm_raw is not None:
        use_llm = use_llm_raw.strip().lower() in ("1", "true", "yes", "on")
    data = build_market_forecast(symbol, use_llm=use_llm)
    if not data:
        return jsonify({"success": False, "error": "Failed to build forecast"}), 502
    return jsonify({"success": True, "timestamp": int(time.time()), "symbol": symbol.upper(), "data": data})


@app.route("/api/v1/fundamentals/<symbol>", methods=["GET"])
def api_v1_fundamentals(symbol: str) -> Response:
    """币种基本面数据"""
    include_macro = request.args.get("include_macro", "1").lower() in ("1", "true", "yes")
    data = fetch_fundamentals_snapshot(symbol, include_macro=include_macro)
    if not data:
        return jsonify({"success": False, "error": "获取基本面数据失败"}), 404
    return jsonify({"success": True, "timestamp": int(time.time()), "symbol": symbol.upper(), "data": data})


@app.route("/api/v1/fundamentals/sentiment", methods=["GET"])
def api_v1_fundamentals_sentiment() -> Response:
    """恐惧贪婪指数"""
    data = _fetch_fear_greed()
    if not data:
        return jsonify({"success": False, "error": "获取情绪指数失败"}), 404
    return jsonify({"success": True, "timestamp": int(time.time()), "data": data})


@app.route("/api/v1/macro/data", methods=["GET"])
def api_v1_macro_data() -> Response:
    """宏观数据"""
    data = load_macro_data()
    return jsonify({"success": True, "timestamp": int(time.time()), "data": data})


@app.route("/api/v1/exchange/ticker/<symbol>", methods=["GET"])
def api_v1_exchange_ticker(symbol: str) -> Response:
    """CCXT交易所行情"""
    data = fetch_ccxt_ticker(symbol)
    if not data:
        return jsonify({"success": False, "error": "获取行情失败"}), 404
    return jsonify({"success": True, "timestamp": int(time.time()), "symbol": symbol.upper(), "data": data})


@app.route("/api/v1/exchange/orderbook/<symbol>", methods=["GET"])
def api_v1_exchange_orderbook(symbol: str) -> Response:
    """订单簿"""
    limit = int(request.args.get("limit", 20))
    data = fetch_ccxt_orderbook(symbol, limit)
    if not data:
        return jsonify({"success": False, "error": "获取订单簿失败"}), 404
    return jsonify({"success": True, "timestamp": int(time.time()), "symbol": symbol.upper(), "data": data})


@app.route("/api/v1/exchange/snapshot/<symbol>", methods=["GET"])
def api_v1_exchange_snapshot(symbol: str) -> Response:
    """完整快照(含流动性)"""
    data = fetch_ccxt_snapshot(symbol)
    if not data:
        return jsonify({"success": False, "error": "获取快照失败"}), 404
    return jsonify({"success": True, "timestamp": int(time.time()), "symbol": symbol.upper(), "data": data})


@app.route("/api/v1/trader/evaluate/<portfolio_id>", methods=["GET"])
def api_v1_trader_evaluate(portfolio_id: str) -> Response:
    """交易员评测(v1)"""
    return evaluate_trader(portfolio_id)


@app.route("/api/v1/trader/raw/<portfolio_id>", methods=["GET"])
def api_v1_trader_raw(portfolio_id: str) -> Response:
    """交易员原始数据(v1)"""
    return get_trader_raw_data(portfolio_id)



@app.route("/api/v1/nofx/competition", methods=["GET"])
@app.route("/api/v1/external/competition", methods=["GET"])
def api_v1_nofx_competition() -> Response:
    limit = _parse_optional_limit(request.args.get("limit"))
    data = fetch_nofx_competition(limit=limit)
    if not data:
        return jsonify({"success": False, "error": "Failed to fetch NOFX competition data"}), 502
    return jsonify({"success": True, "timestamp": int(time.time()), "source": "external", "data": data})

@app.route("/api/v1/nofx/top-traders", methods=["GET"])
@app.route("/api/v1/external/top-traders", methods=["GET"])
def api_v1_nofx_top_traders() -> Response:
    limit = _parse_optional_limit(request.args.get("limit"))
    data = fetch_nofx_top_traders(limit=limit)
    if not data:
        return jsonify({"success": False, "error": "Failed to fetch NOFX top traders data"}), 502
    return jsonify({"success": True, "timestamp": int(time.time()), "source": "external", "data": data})

@app.route("/api/v1/nofx/strategies/public", methods=["GET"])
@app.route("/api/v1/external/strategies/public", methods=["GET"])
def api_v1_nofx_public_strategies() -> Response:
    limit = _parse_optional_limit(request.args.get("limit"))
    data = fetch_nofx_public_strategies(limit=limit)
    if not data:
        return jsonify({"success": False, "error": "Failed to fetch NOFX public strategies"}), 502
    return jsonify({"success": True, "timestamp": int(time.time()), "source": "external", "data": data})

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path: str) -> Response:
    if WEB_DIST.exists() and (WEB_DIST / path).is_file():
        return send_from_directory(WEB_DIST, path)
    if WEB_DIST.exists():
        return send_from_directory(WEB_DIST, "index.html")
    return jsonify({"message": "web/dist not built"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
