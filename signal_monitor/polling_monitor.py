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


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# 尝试从 config.py 读取配置，环境变量优先
try:
    import config as signal_config
    POLL_INTERVAL = int(os.getenv("VALUESCAN_POLL_INTERVAL") or getattr(signal_config, "POLL_INTERVAL", 10))
    REQUEST_TIMEOUT = int(os.getenv("VALUESCAN_REQUEST_TIMEOUT") or getattr(signal_config, "REQUEST_TIMEOUT", 15))
    MAX_CONSECUTIVE_FAILURES = int(os.getenv("VALUESCAN_MAX_CONSECUTIVE_FAILURES") or getattr(signal_config, "MAX_CONSECUTIVE_FAILURES", 5))
    FAILURE_COOLDOWN = int(os.getenv("VALUESCAN_FAILURE_COOLDOWN") or getattr(signal_config, "FAILURE_COOLDOWN", 60))
except ImportError:
    POLL_INTERVAL = int(os.getenv("VALUESCAN_POLL_INTERVAL", "10"))
    REQUEST_TIMEOUT = int(os.getenv("VALUESCAN_REQUEST_TIMEOUT", "15"))
    MAX_CONSECUTIVE_FAILURES = int(os.getenv("VALUESCAN_MAX_CONSECUTIVE_FAILURES", "5"))
    FAILURE_COOLDOWN = int(os.getenv("VALUESCAN_FAILURE_COOLDOWN", "60"))


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


MOVEMENT_LIST_URL = os.getenv(
    "VALUESCAN_MOVEMENT_LIST_URL", "https://api.valuescan.io/api/chance/getFundsMovementPage"
)
MOVEMENT_LIST_INTERVAL = int(os.getenv("VALUESCAN_MOVEMENT_LIST_INTERVAL", "60"))
MOVEMENT_TRADE_TYPE = int(os.getenv("VALUESCAN_MOVEMENT_TRADE_TYPE", "2"))
ENABLE_MOVEMENT_LIST = os.getenv("VALUESCAN_ENABLE_MOVEMENT_LIST", "1") != "0"
PASSIVE_MODE = os.getenv("VALUESCAN_PASSIVE_MODE", "0") == "1"
_enable_signals_env = os.getenv("VALUESCAN_ENABLE_SIGNALS")
ENABLE_SIGNALS = (_enable_signals_env != "0") if _enable_signals_env is not None else (not PASSIVE_MODE)
SEND_TO_TELEGRAM = (not PASSIVE_MODE) and (os.getenv("VALUESCAN_DISABLE_TELEGRAM", "0") != "1")
USER_AGENT = os.getenv(
    "VALUESCAN_USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
)



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


def get_tokens() -> str:
    data = _load_localstorage()
    return data.get("account_token", "") or ""


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
            logger.warning(f"Proxy request failed, fallback to direct: {exc}")
    return session.request(method, url, headers=headers, timeout=REQUEST_TIMEOUT, **kwargs)


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
    headers = {
        "Authorization": f"Bearer {account_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
    }

    for attempt in range(3):
        try:
            logger.debug(
                "[%s] 正在请求 API... (尝试 %s/3, method=%s)",
                source_name,
                attempt + 1,
                method,
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
        # 4000: Token已过期, 4002: 用户已下线 (也表示token失效)
        if code in (4000, 4002):
            logger.info(f"[{source_name}] Token expired signal (code {code}).")
            return None, "expired"

        if code != 200:
            logger.warning(f"[{source_name}] API 返回错误: {payload}")
            return None, "retry"

        items = _extract_items_from_payload(payload)
        logger.debug(f"[{source_name}] API 返回 {len(items)} 条消息")
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
    logger.info("=" * 60)
    logger.info("开始获取信号数据")
    logger.info(f"配置的信号源数量: {len(SIGNAL_ENDPOINTS)}")
    logger.info(f"使用代理: {proxies is not None}")

    combined_messages = []
    seen_keys = set()
    source_counts: Dict[str, int] = {}
    duplicate_count = 0
    statuses = []

    for idx, entry in enumerate(SIGNAL_ENDPOINTS, 1):
        source_name, url = entry[0], entry[1]
        method = entry[2] if len(entry) >= 3 else "GET"
        json_payload = entry[3] if len(entry) >= 4 else None

        logger.info(f"[{idx}/{len(SIGNAL_ENDPOINTS)}] 正在从 [{source_name}] 获取数据...")
        logger.info(f"  URL: {url}")
        logger.info(f"  方法: {method}")

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
            logger.error(f"[{source_name}] Token已过期，需要重新登录")
            return None, "expired"
        if status != "ok" or not payload:
            logger.warning(f"[{source_name}] 未获取到有效数据，状态: {status}")
            continue

        items = _extract_items_from_payload(payload)
        source_counts[source_name] = len(items)
        logger.info(f"[{source_name}] 成功获取 {len(items)} 条信号")

        for item in items:
            key = _make_dedupe_key(item)
            if key in seen_keys:
                duplicate_count += 1
                continue
            seen_keys.add(key)
            combined_messages.append(item)

    if not any(status == "ok" for status in statuses):
        logger.error("所有信号源均获取失败")
        return None, "retry"

    combined_messages.sort(key=_message_sort_key)
    if duplicate_count:
        logger.info(f"合并过程中跳过 {duplicate_count} 条重复信号")

    logger.info("=" * 60)
    logger.info(f"✓ 信号数据获取完成")
    logger.info(f"  总计: {len(combined_messages)} 条消息")
    logger.info(f"  来源分布: {source_counts}")
    logger.info(f"  去重数量: {duplicate_count}")
    logger.info("=" * 60)

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
    trade_type: Optional[int] = None,
) -> Optional[dict]:
    """
    获取异动榜单数据
    """
    headers = {
        "Authorization": f"Bearer {account_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
    }
    trade_type = MOVEMENT_TRADE_TYPE if trade_type is None else trade_type
    payload = {
        "page": 1,
        "pageSize": 50,
        "tradeType": trade_type,
        "order": [{"column": "endTime", "asc": False}],
        "filters": [],
    }
    
    try:
        resp = _request_with_proxy_fallback(
            session,
            "POST",
            MOVEMENT_LIST_URL,
            headers,
            proxies,
            json=payload,
        )
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
    logger.info(f"Passive mode: {PASSIVE_MODE}")
    logger.info(f"Enable signals: {ENABLE_SIGNALS}")
    logger.info(f"Send to Telegram: {SEND_TO_TELEGRAM}")
    logger.info(f"Enable movement list: {ENABLE_MOVEMENT_LIST}")
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

    # 显示AI服务配置状态
    logger.info("=" * 50)
    logger.info("AI 服务配置状态:")
    try:
        from config import (
            ENABLE_AI_KEY_LEVELS,
            ENABLE_AI_OVERLAYS,
            ENABLE_AI_SIGNAL_ANALYSIS,
            ENABLE_AI_MARKET_ANALYSIS,
        )
        logger.info(f"  🤖 AI主力位分析: {'✅ 已启用' if ENABLE_AI_KEY_LEVELS else '❌ 未启用'}")
        logger.info(f"  🎨 AI辅助线绘制: {'✅ 已启用' if ENABLE_AI_OVERLAYS else '❌ 未启用'}")
        logger.info(f"  💬 AI单币简评: {'✅ 已启用' if ENABLE_AI_SIGNAL_ANALYSIS else '❌ 未启用'}")
        logger.info(f"  📊 AI市场分析: {'✅ 已启用' if ENABLE_AI_MARKET_ANALYSIS else '❌ 未启用'}")
    except ImportError:
        logger.warning("  ⚠️  无法加载AI服务配置（config.py可能不存在）")
    logger.info("=" * 50)

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

            account_token = get_tokens()
            
            # 注意: 异动榜单 API 目前不可用，已禁用自动更新
            # 做多策略已修改为：当缓存过期时假设币种在榜单上，允许开单
            # 如果需要启用异动榜单检查，需要找到正确的 API 路径
            if not account_token:
                logger.warning("account_token missing. Please update the token manually.")
                consecutive_failures += 1
                time.sleep(10)
                continue

            if ENABLE_MOVEMENT_LIST and movement_cache and (time.time() - last_movement_update) >= MOVEMENT_LIST_INTERVAL:
                movement_payload = fetch_movement_list(session, account_token, proxies)
                if movement_payload:
                    data = movement_payload.get("data")
                    if isinstance(data, dict) and isinstance(data.get("list"), list):
                        movement_payload = {**movement_payload, "data": data.get("list")}
                    movement_cache.update_from_api_response(movement_payload)
                    last_movement_update = time.time()

            if ENABLE_SIGNALS:
                payload, status = fetch_signals(session, account_token, proxies)

                if status == "ok" and payload and process_response_data:
                    consecutive_failures = 0
                    messages = payload.get("data", [])
                    if messages:
                        new_count = process_response_data(
                            payload,
                            send_to_telegram=SEND_TO_TELEGRAM,
                            seen_ids=None,
                            signal_callback=forward_signal if (ENABLE_IPC_FORWARDING and not PASSIVE_MODE) else None,
                        )
                        if isinstance(new_count, int) and new_count > 0:
                            logger.info(f"处理了 {new_count} 条新消息")
                    else:
                        logger.debug("本次无消息")
                elif status == "expired":
                    logger.warning("Token expired. Please refresh the token manually.")
                    consecutive_failures += 1
                    time.sleep(30)

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
