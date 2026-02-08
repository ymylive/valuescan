#!/usr/bin/env python3
"""主动轮询 ValueScan API 获取信号（稳定 token / 自动代理回退）"""
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

POLL_INTERVAL = int(os.getenv("VALUESCAN_POLL_INTERVAL", "10"))
REQUEST_TIMEOUT = int(os.getenv("VALUESCAN_REQUEST_TIMEOUT", "15"))
TOKEN_FILE = os.getenv(
    "VALUESCAN_TOKEN_FILE",
    "/opt/valuescan/signal_monitor/valuescan_localstorage.json",
)
REFRESH_URL = "https://api.valuescan.io/api/account/refreshToken"
API_URL = "https://api.valuescan.io/api/account/message/getWarnMessage"
REFRESH_THROTTLE = 60  # 最短两次刷新间隔（秒），避免频繁请求

_last_refresh_attempt = 0.0


def load_localstorage() -> Dict[str, Any]:
    """读取本地存储的 token 信息"""
    try:
        with open(TOKEN_FILE, "r") as f:
            return json.load(f)
    except Exception as exc:
        logger.error(f"加载 Token 失败: {exc}")
        return {}


def persist_localstorage(data: Dict[str, Any]) -> bool:
    """将最新 token 写回本地存储"""
    try:
        with open(TOKEN_FILE, "w") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as exc:
        logger.error(f"保存 Token 失败: {exc}")
        return False


def get_tokens() -> Tuple[str, str]:
    """返回 account_token 与 refresh_token"""
    data = load_localstorage()
    return data.get("account_token", ""), data.get("refresh_token", "")


def resolve_proxies() -> Optional[Dict[str, str]]:
    """
    优先读取 /opt/valuescan/signal_monitor/config.py 的 SOCKS5_PROXY/HTTP_PROXY。
    若无配置则默认使用本地 socks5://127.0.0.1:1080（兼容旧行为）。
    可用 VALUESCAN_NO_PROXY=1 关闭。
    """
    if os.getenv("VALUESCAN_NO_PROXY", "0") == "1":
        return None

    try:
        import importlib.util
        from pathlib import Path

        cfg_path = Path("/opt/valuescan/signal_monitor/config.py")
        if cfg_path.exists():
            spec = importlib.util.spec_from_file_location("valuescan_signal_config", str(cfg_path))
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)  # type: ignore[attr-defined]
                socks5 = getattr(mod, "SOCKS5_PROXY", "") or ""
                http_proxy = getattr(mod, "HTTP_PROXY", "") or ""
                if isinstance(socks5, str) and socks5.strip():
                    p = socks5.strip()
                    return {"http": p, "https": p}
                if isinstance(http_proxy, str) and http_proxy.strip():
                    p = http_proxy.strip()
                    return {"http": p, "https": p}
    except Exception:
        pass

    default_proxy = os.getenv("VALUESCAN_DEFAULT_SOCKS5", "socks5://127.0.0.1:1080")
    return {"http": default_proxy, "https": default_proxy}


def _request_with_proxy_fallback(
    method: str,
    url: str,
    headers: Dict[str, str],
    proxies: Optional[Dict[str, str]],
    **kwargs,
):
    if proxies:
        try:
            return requests.request(
                method, url, headers=headers, proxies=proxies, timeout=REQUEST_TIMEOUT, **kwargs
            )
        except requests.exceptions.RequestException as exc:
            logger.warning(f"代理请求失败，回退直连: {exc}")
    return requests.request(
        method, url, headers=headers, timeout=REQUEST_TIMEOUT, **kwargs
    )


def refresh_account_token(current_refresh_token: str, proxies: Optional[Dict[str, str]]) -> bool:
    """使用 refresh_token 刷新 account_token"""
    global _last_refresh_attempt
    now = time.time()

    if now - _last_refresh_attempt < REFRESH_THROTTLE:
        logger.warning("跳过刷新：刷新请求过于频繁")
        return False
    _last_refresh_attempt = now

    if not current_refresh_token:
        logger.error("无法刷新 Token：缺少 refresh_token")
        return False

    headers = {
        "Authorization": f"Bearer {current_refresh_token}",
        "Content-Type": "application/json",
    }

    try:
        resp = _request_with_proxy_fallback("POST", REFRESH_URL, headers, proxies)
    except requests.exceptions.RequestException as exc:
        logger.error(f"刷新 Token 请求异常: {exc}")
        return False

    if resp.status_code != 200:
        logger.error(f"刷新 Token 失败，状态码 {resp.status_code}")
        return False

    try:
        payload = resp.json()
    except ValueError:
        logger.error("刷新 Token 响应无法解析 JSON")
        return False

    if payload.get("code") != 200:
        logger.error(f"刷新 Token 返回错误: {payload}")
        return False

    data = payload.get("data") or {}
    new_account_token = data.get("account_token") or data.get("token")
    new_refresh_token = data.get("refresh_token") or current_refresh_token

    if not new_account_token:
        logger.error("刷新 Token 响应缺少 account_token")
        return False

    ls_data = load_localstorage()
    ls_data["account_token"] = new_account_token
    ls_data["refresh_token"] = new_refresh_token
    ls_data["last_refresh"] = datetime.now(timezone.utc).isoformat()

    if persist_localstorage(ls_data):
        logger.info("Token 已刷新并写回本地存储")
        return True
    return False


def fetch_signals(account_token: str, proxies: Optional[Dict[str, str]]) -> Tuple[Optional[dict], str]:
    """
    获取信号，带重试机制
    返回 (数据, 状态)；状态可为 ok/expired/retry
    """
    headers = {"Authorization": f"Bearer {account_token}", "Content-Type": "application/json"}
    url = API_URL

    for attempt in range(3):
        try:
            logger.info(f"正在请求 API... (尝试 {attempt + 1}/3)")
            resp = _request_with_proxy_fallback("GET", url, headers, proxies)
        except requests.exceptions.Timeout:
            logger.warning(f"请求超时 (尝试 {attempt + 1}/3)")
            if attempt < 2:
                time.sleep(2)
            continue
        except requests.exceptions.RequestException as exc:
            logger.error(f"请求异常: {exc}")
            return None, "retry"

        if resp.status_code == 401:
            logger.error("Token 未通过认证 (401)")
            return None, "expired"

        if resp.status_code != 200:
            logger.warning(f"API 返回状态码: {resp.status_code}")
            if attempt < 2:
                time.sleep(2)
                continue
            return None, "retry"

        try:
            data = resp.json()
        except ValueError:
            logger.error("API 响应 JSON 解析失败")
            return None, "retry"

        if data.get("code") == 4000:
            logger.error("Token 已过期 (code 4000)")
            return None, "expired"

        logger.info(f"API 返回 {len(data.get('data', []))} 条消息")
        return data, "ok"

    return None, "retry"


def main():
    logger.info("=" * 50)
    logger.info("启动主动轮询监控...")
    logger.info(f"轮询间隔: {POLL_INTERVAL} 秒")
    logger.info(f"请求超时: {REQUEST_TIMEOUT} 秒")
    logger.info("=" * 50)

    consecutive_failures = 0
    max_consecutive_failures = 5

    proxies = resolve_proxies()

    try:
        sys.path.insert(0, "/opt/valuescan/signal_monitor")
        from message_handler import process_response_data
        from config import ENABLE_IPC_FORWARDING
        from ipc_client import forward_signal
        logger.info("导入模块成功")
    except Exception as e:
        logger.error(f"导入模块失败: {e}")
        forward_signal = None
        ENABLE_IPC_FORWARDING = False
        process_response_data = None  # type: ignore

    while True:
        try:
            account_token, refresh_token_value = get_tokens()
            if not account_token:
                consecutive_failures += 1
                logger.error("未读取到 account_token，30 秒后重试")
                time.sleep(30)
                continue

            data, status = fetch_signals(account_token, proxies)

            if status == "expired":
                refreshed = refresh_account_token(refresh_token_value, proxies)
                if refreshed:
                    # 刷新成功，立即重试获取信号
                    time.sleep(1)
                    continue
                consecutive_failures += 1

            elif status == "ok" and data and data.get("code") == 200 and process_response_data:
                consecutive_failures = 0
                messages = data.get("data", [])

                if messages:
                    logger.info("  状态码: 200")
                    logger.info("  消息: success")
                    new_count = process_response_data(
                        data,
                        send_to_telegram=True,
                        seen_ids=None,
                        signal_callback=forward_signal if ENABLE_IPC_FORWARDING else None,
                    )
                    if new_count > 0:
                        logger.info(f"处理了 {new_count} 条新消息")
                else:
                    logger.info("本次无消息")

            else:
                consecutive_failures += 1
                logger.warning(
                    f"API 请求失败 (连续失败: {consecutive_failures}/{max_consecutive_failures})"
                )

            if consecutive_failures >= max_consecutive_failures:
                logger.error(
                    f"连续失败 {consecutive_failures} 次，等待 60 秒后重试"
                )
                time.sleep(60)
                consecutive_failures = 0
            else:
                time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            logger.info("停止监控")
            break
        except SystemExit as e:
            # 防止下游模块意外 sys.exit 导致服务退出
            logger.error(f"捕获到 SystemExit: {e}，继续运行")
            time.sleep(POLL_INTERVAL)
        except BaseException as e:
            # 兜底所有异常（含非 Exception），避免服务退出
            logger.exception(f"循环致命错误: {e}")
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
