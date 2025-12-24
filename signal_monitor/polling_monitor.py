#!/usr/bin/env python3
"""
主动轮询 ValueScan API 获取信号（轮询版 signal_monitor）。

修复点（对应“发送一下又不发了”）：
- 旧版本在启动时只读取一次 account_token，而 token_refresher 会周期性刷新并写回文件，
  导致轮询继续使用旧 token，随后 API 失败/返回异常，进入失败回退与长等待。
- 本版本每次轮询前都会从 valuescan_localstorage.json 读取最新 token，并对并发写入做容错。
- 代理请求失败自动回退直连，避免本地 SOCKS 不稳定导致整体停摆。
"""

from __future__ import annotations

import json
import logging
import os
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests

from token_refresher import refresh_if_needed


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


POLL_INTERVAL = int(os.getenv("VALUESCAN_POLL_INTERVAL", "10"))
REQUEST_TIMEOUT = int(os.getenv("VALUESCAN_REQUEST_TIMEOUT", "15"))
MAX_CONSECUTIVE_FAILURES = int(os.getenv("VALUESCAN_MAX_CONSECUTIVE_FAILURES", "5"))
FAILURE_COOLDOWN = int(os.getenv("VALUESCAN_FAILURE_COOLDOWN", "60"))
AUTO_RELOGIN = os.getenv("VALUESCAN_AUTO_RELOGIN", "0") == "1"
AUTO_RELOGIN_COOLDOWN = int(os.getenv("VALUESCAN_AUTO_RELOGIN_COOLDOWN", "1800"))
AUTO_RELOGIN_USE_BROWSER = os.getenv("VALUESCAN_AUTO_RELOGIN_USE_BROWSER", "0") == "1"
SKIP_REFRESH_API = os.getenv("VALUESCAN_SKIP_REFRESH_API", "0") in ("1", "true", "True")

WARN_API_URL = os.getenv(
    "VALUESCAN_API_URL", "https://api.valuescan.io/api/account/message/getWarnMessage"
)
AI_API_URL = os.getenv(
    "VALUESCAN_AI_API_URL", "https://api.valuescan.io/api/account/message/aiMessagePage"
).strip()
# (name, url, method, payload)
SIGNAL_ENDPOINTS = [
    ("getWarnMessage", WARN_API_URL, "GET", None),
]
if AI_API_URL:
    # aiMessagePage 需要 POST，否则会返回 500 “Request method 'GET' is not supported”
    SIGNAL_ENDPOINTS.append(
        ("aiMessagePage", AI_API_URL, "POST", {"pageNum": 1, "pageSize": 50})
    )
API_URL = WARN_API_URL  # backward compatibility alias
REFRESH_URL = os.getenv("VALUESCAN_REFRESH_URL", "https://api.valuescan.io/api/account/refreshToken")


def _build_refresh_urls(primary_url: str) -> List[str]:
    env_urls = (os.getenv("VALUESCAN_REFRESH_URLS") or "").strip()
    urls: List[str] = []
    if env_urls:
        urls.extend([u.strip() for u in env_urls.split(",") if u.strip()])

    defaults = [
        primary_url,
        "https://api.valuescan.io/api/account/refresh",
        "https://api.valuescan.io/api/auth/refresh",
        "https://api.valuescan.io/api/token/refresh",
        "https://api.valuescan.io/api/v1/account/refreshToken",
        "https://api.valuescan.io/api/v1/account/refresh",
        "https://api.valuescan.io/api/v1/auth/refresh",
        "https://api.valuescan.io/api/v1/token/refresh",
        "https://www.valuescan.io/api/account/refreshToken",
        "https://www.valuescan.io/api/account/refresh",
    ]
    for url in defaults:
        if url and url not in urls:
            urls.append(url)
    return urls


REFRESH_URLS = _build_refresh_urls(REFRESH_URL)
MOVEMENT_LIST_URL = os.getenv(
    "VALUESCAN_MOVEMENT_LIST_URL", "https://api.valuescan.io/api/getFundsMovementPage"
)
MOVEMENT_LIST_INTERVAL = int(os.getenv("VALUESCAN_MOVEMENT_LIST_INTERVAL", "60"))  # 60秒更新一次

_LAST_RELOGIN_MONO = 0.0


def _resolve_token_file() -> Path:
    env_path = os.getenv("VALUESCAN_TOKEN_FILE")
    if env_path:
        return Path(env_path)

    base_dir = Path(__file__).resolve().parent
    candidates = [
        base_dir / "valuescan_localstorage.json",
        Path("/opt/valuescan/signal_monitor/valuescan_localstorage.json"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


TOKEN_FILE = _resolve_token_file()


def _is_local_proxy_reachable(proxy_url: str) -> bool:
    try:
        parsed = urlparse(proxy_url)
    except Exception:
        return False

    host = parsed.hostname
    port = parsed.port
    if not host or not port:
        return False

    if host not in {"127.0.0.1", "localhost", "::1"}:
        return True

    try:
        with socket.create_connection((host, port), timeout=0.3):
            return True
    except OSError:
        return False


def _load_signal_config_proxies() -> Tuple[Optional[str], Optional[Dict[str, str]]]:
    """
    Returns (proxy_url, proxies_for_requests).
    Prefers signal_monitor/config.py; falls back to local socks5 only if reachable.
    """
    if os.getenv("VALUESCAN_NO_PROXY", "0") == "1":
        return None, None

    cfg_path = Path("/opt/valuescan/signal_monitor/config.py")
    if cfg_path.exists():
        try:
            import importlib.util

            spec = importlib.util.spec_from_file_location("valuescan_signal_config", str(cfg_path))
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)  # type: ignore[attr-defined]
                socks5 = getattr(mod, "SOCKS5_PROXY", "") or ""
                http_proxy = getattr(mod, "HTTP_PROXY", "") or ""
                if isinstance(socks5, str) and socks5.strip():
                    p = socks5.strip()
                    return p, {"http": p, "https": p}
                if isinstance(http_proxy, str) and http_proxy.strip():
                    p = http_proxy.strip()
                    return p, {"http": p, "https": p}
        except Exception:
            pass

    default_proxy = os.getenv("VALUESCAN_DEFAULT_SOCKS5", "socks5://127.0.0.1:1080")
    if default_proxy and _is_local_proxy_reachable(default_proxy):
        return default_proxy, {"http": default_proxy, "https": default_proxy}
    return None, None


def _load_localstorage(retries: int = 3, delay: float = 0.2) -> Dict[str, Any]:
    for attempt in range(retries):
        try:
            content = TOKEN_FILE.read_text(encoding="utf-8")
            return json.loads(content)
        except json.JSONDecodeError as exc:
            if attempt < retries - 1:
                time.sleep(delay)
                continue
            logger.error(f"加载 Token 失败(JSON损坏): {exc}")
            return {}
        except FileNotFoundError:
            logger.error(f"Token 文件不存在: {TOKEN_FILE}")
            return {}
        except Exception as exc:
            logger.error(f"加载 Token 失败: {exc}")
            return {}
    return {}


def _maybe_auto_relogin() -> bool:
    """
    Optional keepalive: when tokens are missing/invalid, try to re-login using env credentials.

    Disabled by default. Enable on VPS via:
      VALUESCAN_AUTO_RELOGIN=1
      VALUESCAN_EMAIL=...
      VALUESCAN_PASSWORD=...

    Optionally enable browser automation fallback (DrissionPage):
      VALUESCAN_AUTO_RELOGIN_USE_BROWSER=1
    """
    global _LAST_RELOGIN_MONO

    if not AUTO_RELOGIN:
        return False

    now = time.monotonic()
    if now - _LAST_RELOGIN_MONO < AUTO_RELOGIN_COOLDOWN:
        return False

    email = (os.getenv("VALUESCAN_EMAIL") or "").strip()
    password = (os.getenv("VALUESCAN_PASSWORD") or "").strip()
    if not email or not password:
        logger.warning("AUTO_RELOGIN 启用但缺少 VALUESCAN_EMAIL/VALUESCAN_PASSWORD")
        return False

    base_dir = Path(__file__).resolve().parent
    python_bin = sys.executable or "python3"

    env = dict(os.environ)
    env.setdefault("VALUESCAN_TOKEN_FILE", str(TOKEN_FILE))

    scripts = [base_dir / "http_api_login.py"]
    if AUTO_RELOGIN_USE_BROWSER:
        scripts.append(base_dir / "http_login.py")

    for script in scripts:
        if not script.exists():
            continue
        logger.warning("尝试自动登录刷新 token: %s", script.name)
        try:
            res = subprocess.run(
                [python_bin, str(script), email, password],
                cwd=str(base_dir),
                env=env,
                capture_output=True,
                text=True,
                timeout=180 if script.name == "http_login.py" else 90,
            )
        except Exception as exc:
            logger.warning("自动登录执行失败: %s", exc)
            continue

        if res.returncode == 0:
            data = _load_localstorage(retries=3)
            if (data.get("account_token") or "").strip():
                _LAST_RELOGIN_MONO = time.monotonic()
                logger.info("自动登录成功，已获取 account_token")
                return True

        stderr = (res.stderr or "").strip()
        stdout = (res.stdout or "").strip()
        msg = stderr or stdout
        if msg:
            logger.warning("自动登录未成功: %s", msg[-300:])

    _LAST_RELOGIN_MONO = time.monotonic()
    return False


def _persist_localstorage(data: Dict[str, Any]) -> bool:
    """
    原子写入，避免 token_refresher/轮询并发导致 JSON 半写入。
    """
    try:
        TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = TOKEN_FILE.with_suffix(TOKEN_FILE.suffix + ".tmp")
        tmp_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp_path, TOKEN_FILE)
        return True
    except Exception as exc:
        logger.error(f"保存 Token 失败: {exc}")
        return False


def get_tokens() -> Tuple[str, str]:
    data = _load_localstorage()
    return data.get("account_token", "") or "", data.get("refresh_token", "") or ""


def _make_session() -> requests.Session:
    session = requests.Session()
    session.trust_env = False
    return session


def _request_with_proxy_fallback(
    session: requests.Session,
    method: str,
    url: str,
    headers: Dict[str, str],
    proxies: Optional[Dict[str, str]],
    **kwargs,
) -> requests.Response:
    if proxies:
        try:
            return session.request(
                method, url, headers=headers, proxies=proxies, timeout=REQUEST_TIMEOUT, **kwargs
            )
        except requests.RequestException as exc:
            logger.warning(f"代理请求失败，回退直连: {exc}")
    return session.request(method, url, headers=headers, timeout=REQUEST_TIMEOUT, **kwargs)


def _extract_tokens_from_payload(payload: Any) -> Dict[str, str]:
    if not isinstance(payload, dict):
        return {}

    token_keys = ["account_token", "token", "access_token", "accessToken", "jwt"]
    refresh_keys = ["refresh_token", "refreshToken", "refresh"]

    def _pick(dct: Dict[str, Any], keys: List[str]) -> str:
        for key in keys:
            val = dct.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
        return ""

    def _scan(obj: Any, depth: int) -> Dict[str, str]:
        if depth <= 0:
            return {}
        if isinstance(obj, dict):
            account_token = _pick(obj, token_keys)
            refresh_token = _pick(obj, refresh_keys)
            if account_token or refresh_token:
                return {"account_token": account_token, "refresh_token": refresh_token}
            for value in obj.values():
                found = _scan(value, depth - 1)
                if found:
                    return found
        elif isinstance(obj, list):
            for value in obj:
                found = _scan(value, depth - 1)
                if found:
                    return found
        return {}

    return _scan(payload, depth=4)


def refresh_account_token(
    session: requests.Session,
    refresh_token_value: str,
    proxies: Optional[Dict[str, str]],
) -> bool:
    if SKIP_REFRESH_API:
        logger.warning("刷新 Token API 已禁用，跳过请求。")
        return False
    if not refresh_token_value:
        return False

    base_headers = {"Content-Type": "application/json"}
    request_modes = [
        ("bearer", {"Authorization": f"Bearer {refresh_token_value}"}, {}),
        ("auth", {"Authorization": refresh_token_value}, {}),
        ("body_refresh_token", {}, {"refresh_token": refresh_token_value}),
        ("body_refreshToken", {}, {"refreshToken": refresh_token_value}),
        ("body_token", {}, {"token": refresh_token_value}),
    ]

    last_error = ""
    for url in REFRESH_URLS:
        for label, extra_headers, payload in request_modes:
            headers = dict(base_headers)
            headers.update(extra_headers)
            try:
                resp = _request_with_proxy_fallback(session, "POST", url, headers, proxies, json=payload)
            except requests.RequestException as exc:
                last_error = f"{url} {label} error: {exc}"
                continue

            if resp.status_code in (404, 405):
                last_error = f"{url} status={resp.status_code}"
                break

            if resp.status_code >= 500 and "No static resource" in (resp.text or ""):
                last_error = f"{url} missing endpoint"
                break

            if resp.status_code != 200:
                last_error = f"{url} status={resp.status_code}"
                continue

            try:
                payload_json = resp.json()
            except ValueError:
                last_error = f"{url} non-JSON response"
                continue

            tokens = _extract_tokens_from_payload(payload_json)
            new_account_token = (tokens.get("account_token") or "").strip()
            new_refresh_token = (tokens.get("refresh_token") or refresh_token_value or "").strip()
            if new_account_token:
                ls_data = _load_localstorage()
                ls_data["account_token"] = new_account_token
                ls_data["refresh_token"] = new_refresh_token
                ls_data["last_refresh"] = datetime.now(timezone.utc).isoformat()
                if _persist_localstorage(ls_data):
                    logger.info("Token refreshed successfully via %s (%s).", url, label)
                    return True
                last_error = f"{url} failed to persist token"
                continue

            code = payload_json.get("code") if isinstance(payload_json, dict) else None
            if code in (4000, 401, 403):
                last_error = f"{url} code={code}"
                return False

            last_error = f"{url} invalid payload"

    if last_error:
        logger.warning(f"刷新 Token 失败: {last_error}")
    return False


def _extract_items_from_payload(payload: dict) -> list:
    def _walk(obj, depth: int = 3) -> list:
        if depth <= 0:
            return []
        if isinstance(obj, list):
            return obj
        if not isinstance(obj, dict):
            return []
        # Common list containers
        for key in ("list", "records", "rows", "items", "messages", "data"):
            v = obj.get(key)
            if isinstance(v, list):
                return v
        # Recurse a bit for nested "data"
        for key in ("data", "result", "payload"):
            v = obj.get(key)
            if isinstance(v, dict):
                found = _walk(v, depth - 1)
                if found:
                    return found
        return []

    data = payload.get("data")
    found = _walk(data, depth=4)
    if found:
        return found
    # Some responses may return the list at top-level directly
    return _walk(payload, depth=2)


def _message_sort_key(item: dict) -> int:
    for key in ("createTime", "createdTime", "create_time", "timestamp"):
        ts = item.get(key)
        if ts is None:
            continue
        try:
            return int(ts)
        except (TypeError, ValueError):
            try:
                return int(float(ts))
            except Exception:
                continue
    return 0


def _make_dedupe_key(item: dict) -> str:
    msg_id = None
    for key in ("id", "msgId", "messageId", "message_id", "msg_id"):
        v = item.get(key)
        if v is None:
            continue
        if isinstance(v, (int, float)):
            try:
                msg_id = str(int(v))
                break
            except Exception:
                continue
        if isinstance(v, str) and v.strip():
            msg_id = v.strip()
            break
    if msg_id is not None:
        return f"id:{msg_id}"
    title = item.get("title") or ""
    keyword = item.get("keyword") or ""
    symbol = item.get("symbol") or ""
    msg_type = item.get("type") or item.get("messageType") or ""
    create_time = item.get("createTime") or item.get("createdTime") or item.get("create_time") or ""
    return f"fallback:{title}-{keyword or symbol}-{msg_type}-{create_time}"


def _fetch_from_endpoint(
    session: requests.Session,
    account_token: str,
    proxies: Optional[Dict[str, str]],
    url: str,
    source_name: str,
    method: str = "GET",
    json_payload: Optional[dict] = None,
) -> Tuple[Optional[dict], str]:
    headers = {"Authorization": f"Bearer {account_token}", "Content-Type": "application/json"}

    for attempt in range(3):
        try:
            logger.info(
                f"[{source_name}] 正在请求 API... (尝试 {attempt + 1}/3, method={method})"
            )
            if method.upper() == "POST":
                resp = _request_with_proxy_fallback(
                    session,
                    "POST",
                    url,
                    headers,
                    proxies,
                    json=json_payload or {},
                )
            else:
                resp = _request_with_proxy_fallback(session, "GET", url, headers, proxies)
        except requests.exceptions.Timeout:
            logger.warning(f"[{source_name}] 请求超时 (尝试 {attempt + 1}/3)")
            if attempt < 2:
                time.sleep(2)
            continue
        except requests.exceptions.RequestException as exc:
            logger.warning(f"[{source_name}] 请求异常: {exc}")
            return None, "retry"

        if resp.status_code == 401:
            logger.error(f"[{source_name}] Token 未通过认证 (401)")
            return None, "expired"

        if resp.status_code != 200:
            logger.warning(f"[{source_name}] API 返回状态码: {resp.status_code}")
            if attempt < 2:
                time.sleep(2)
                continue
            return None, "retry"

        try:
            payload = resp.json()
        except ValueError:
            logger.warning(f"[{source_name}] API 响应 JSON 解析失败")
            return None, "retry"

        code = payload.get("code")
        if code == 4000:
            logger.error(f"[{source_name}] Token 已过期 (code 4000)")
            return None, "expired"

        if code != 200:
            logger.warning(f"[{source_name}] API 返回错误: {payload}")
            return None, "retry"

        items = _extract_items_from_payload(payload)
        logger.info(f"[{source_name}] API 返回 {len(items)} 条消息")
        return payload, "ok"

    return None, "retry"


def fetch_signals(
    session: requests.Session,
    account_token: str,
    proxies: Optional[Dict[str, str]],
) -> Tuple[Optional[dict], str]:
    """
    Fetch signals from all configured endpoints and merge duplicates.

    Returns (payload, status) where status is one of: ok/expired/retry.
    """
    combined_messages = []
    seen_keys = set()
    source_counts: Dict[str, int] = {}
    duplicate_count = 0
    statuses = []

    for entry in SIGNAL_ENDPOINTS:
        source_name, url = entry[0], entry[1]
        method = entry[2] if len(entry) >= 3 else "GET"
        json_payload = entry[3] if len(entry) >= 4 else None

        payload, status = _fetch_from_endpoint(
            session,
            account_token,
            proxies,
            url,
            source_name,
            method=method,
            json_payload=json_payload,
        )
        statuses.append(status)

        if status == "expired":
            return None, "expired"
        if status != "ok" or not payload:
            logger.warning(f"[{source_name}] 未获取到有效数据，状态: {status}")
            continue

        items = _extract_items_from_payload(payload)
        source_counts[source_name] = len(items)
        for item in items:
            key = _make_dedupe_key(item)
            if key in seen_keys:
                duplicate_count += 1
                continue
            seen_keys.add(key)
            combined_messages.append(item)

    if not any(status == "ok" for status in statuses):
        return None, "retry"

    combined_messages.sort(key=_message_sort_key)
    if duplicate_count:
        logger.info(f"合并过程中跳过 {duplicate_count} 条重复信号")
    logger.info(f"合并后返回 {len(combined_messages)} 条消息，来源计数: {source_counts}")

    aggregated_payload = {
        "code": 200,
        "msg": "success",
        "data": combined_messages,
        "source_counts": source_counts,
    }
    return aggregated_payload, "ok"


def fetch_movement_list(
    session: requests.Session,
    account_token: str,
    proxies: Optional[Dict[str, str]],
) -> Optional[dict]:
    """
    获取异动榜单数据
    """
    headers = {"Authorization": f"Bearer {account_token}", "Content-Type": "application/json"}
    
    try:
        resp = _request_with_proxy_fallback(session, "GET", MOVEMENT_LIST_URL, headers, proxies)
    except requests.RequestException as exc:
        logger.warning(f"获取异动榜单失败: {exc}")
        return None
    
    if resp.status_code != 200:
        logger.warning(f"异动榜单 API 返回状态码: {resp.status_code}")
        return None
    
    try:
        payload = resp.json()
    except ValueError:
        logger.warning("异动榜单响应 JSON 解析失败")
        return None
    
    if payload.get("code") != 200:
        logger.warning(f"异动榜单 API 返回错误: {payload}")
        return None
    
    return payload


def main():
    logger.info("=" * 50)
    logger.info("启动主动轮询监控...")
    logger.info(f"轮询间隔: {POLL_INTERVAL} 秒")
    logger.info(f"请求超时: {REQUEST_TIMEOUT} 秒")
    logger.info(f"信号源: {[entry[0] for entry in SIGNAL_ENDPOINTS]}")
    for entry in SIGNAL_ENDPOINTS:
        name, url = entry[0], entry[1]
        method = entry[2] if len(entry) >= 3 else "GET"
        logger.info(f"  - {name}: {url} (method={method})")
    logger.info(f"Token 文件: {TOKEN_FILE}")
    logger.info(f"异动榜单更新间隔: {MOVEMENT_LIST_INTERVAL} 秒")
    logger.info("=" * 50)

    try:
        from message_handler import process_response_data
        from config import ENABLE_IPC_FORWARDING
        from ipc_client import forward_signal
        logger.info("导入模块成功")
    except Exception as exc:
        logger.error(f"导入模块失败: {exc}")
        process_response_data = None  # type: ignore[assignment]
        forward_signal = None  # type: ignore[assignment]
        ENABLE_IPC_FORWARDING = False  # type: ignore[assignment]

    # 导入异动榜单缓存
    movement_cache = None
    try:
        from movement_list_cache import get_movement_list_cache
        movement_cache = get_movement_list_cache()
        logger.info("✅ 异动榜单缓存已初始化")
    except Exception as exc:
        logger.warning(f"导入异动榜单缓存失败: {exc}")

    # 导入 AI 市场总结模块
    ai_summary_check = None
    try:
        from ai_market_summary import check_and_generate_summary
        ai_summary_check = check_and_generate_summary
        logger.info("✅ AI 市场总结模块已加载")
    except Exception as exc:
        logger.warning(f"导入 AI 市场总结模块失败: {exc}")

    proxy_url, proxies = _load_signal_config_proxies()
    if proxy_url:
        logger.info(f"🌐 使用代理: {proxy_url}")

    session = _make_session()
    consecutive_failures = 0
    last_movement_update = 0.0  # 上次更新异动榜单的时间
    last_ai_summary_check = 0.0  # 上次检查 AI 总结的时间

    while True:
        try:
            # 定期检查 AI 市场总结（每5分钟检查一次是否需要生成）
            if ai_summary_check and (time.time() - last_ai_summary_check) >= 300:
                try:
                    ai_summary_check()
                    last_ai_summary_check = time.time()
                except Exception as exc:
                    logger.warning(f"AI 市场总结检查失败: {exc}")

            # Proactively refresh token when it is close to expiring (browser-based).
            refresh_if_needed(headless=True)
            account_token, refresh_token_value = get_tokens()
            
            # 注意: 异动榜单 API 目前不可用，已禁用自动更新
            # 做多策略已修改为：当缓存过期时假设币种在榜单上，允许开单
            # 如果需要启用异动榜单检查，需要找到正确的 API 路径
            
            if not account_token:
                # If refresh_token exists, try to refresh proactively (avoid requiring a full re-login).
                if refresh_token_value:
                    refreshed = refresh_account_token(session, refresh_token_value, proxies)
                    if refreshed:
                        logger.info("account_token 缺失，已用 refresh_token 刷新并写回本地")
                        consecutive_failures = 0
                        time.sleep(1)
                        continue

                # If tokens are missing, try a Chromium re-login (uses saved credentials or env).
                if refresh_if_needed(headless=True, force=True):
                    consecutive_failures = 0
                    time.sleep(1)
                    continue

                # Fallback to legacy subprocess-based relogin (env only).
                _maybe_auto_relogin()

                consecutive_failures += 1
                logger.error("未读取到 account_token，10 秒后重试")
                time.sleep(10)
                continue

            payload, status = fetch_signals(session, account_token, proxies)

            if status == "ok" and payload and process_response_data:
                consecutive_failures = 0
                messages = payload.get("data", [])
                if messages:
                    new_count = process_response_data(
                        payload,
                        send_to_telegram=True,
                        seen_ids=None,
                        signal_callback=forward_signal if ENABLE_IPC_FORWARDING else None,
                    )
                    if isinstance(new_count, int) and new_count > 0:
                        logger.info(f"处理了 {new_count} 条新消息")
                else:
                    logger.info("本次无消息")

            elif status == "expired":
                refreshed = refresh_account_token(session, refresh_token_value, proxies)
                if refreshed:
                    logger.info("Token 已刷新并写回本地存储")
                    consecutive_failures = 0
                    time.sleep(1)
                    continue
                if refresh_if_needed(headless=True, force=True):
                    logger.info("Token re-login succeeded via Chromium; continuing.")
                    consecutive_failures = 0
                    time.sleep(1)
                    continue
                # Optional re-login when refresh fails (e.g. refresh_token invalid/user logged out).
                _maybe_auto_relogin()
                consecutive_failures += 1
                logger.error("Token 过期且无法刷新，等待 token_refresher/Selenium 刷新")

            else:
                consecutive_failures += 1
                logger.warning(
                    f"API 请求失败 (连续失败: {consecutive_failures}/{MAX_CONSECUTIVE_FAILURES})"
                )

            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                logger.error(f"连续失败 {consecutive_failures} 次，等待 {FAILURE_COOLDOWN} 秒后重试")
                time.sleep(FAILURE_COOLDOWN)
                consecutive_failures = 0
            else:
                time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            logger.info("停止监控")
            break
        except SystemExit as exc:
            logger.error(f"捕获到 SystemExit: {exc}，继续运行")
            time.sleep(POLL_INTERVAL)
        except BaseException as exc:
            logger.exception(f"循环错误: {exc}")
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
