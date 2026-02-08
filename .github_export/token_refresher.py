#!/usr/bin/env python3
"""
ValueScan token refresher.

Keeps `valuescan_localstorage.json` fresh by periodically exchanging refresh_token
for a new account_token.

This module is also used by tests in `tests/test_token_refresher_utils.py`.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

REFRESH_URL = os.getenv("VALUESCAN_REFRESH_URL", "https://api.valuescan.io/api/account/refreshToken")
TOKEN_FILE = Path(os.getenv("VALUESCAN_TOKEN_FILE") or Path(__file__).resolve().parent / "signal_monitor" / "valuescan_localstorage.json")
CREDENTIALS_FILE = Path(
    os.getenv("VALUESCAN_CREDENTIALS_FILE")
    or Path(__file__).resolve().parent / "signal_monitor" / "valuescan_credentials.json"
)

CHECK_INTERVAL_S = int(os.getenv("VALUESCAN_TOKEN_REFRESH_INTERVAL", "30"))
REFRESH_SAFETY_S = int(os.getenv("VALUESCAN_TOKEN_REFRESH_SAFETY", "120"))
REQUEST_TIMEOUT_S = int(os.getenv("VALUESCAN_TOKEN_REFRESH_TIMEOUT", "15"))
TOKEN_STATUS_URL = os.getenv(
    "VALUESCAN_TOKEN_STATUS_URL",
    "https://api.valuescan.io/api/account/message/getWarnMessage",
)
TOKEN_STATUS_TIMEOUT_S = int(os.getenv("VALUESCAN_TOKEN_STATUS_TIMEOUT", "12"))
AUTO_RELOGIN = os.getenv("VALUESCAN_AUTO_RELOGIN", "0").strip().lower() in ("1", "true", "yes")
AUTO_RELOGIN_COOLDOWN_S = int(os.getenv("VALUESCAN_AUTO_RELOGIN_COOLDOWN", "900"))
AUTO_RELOGIN_USE_BROWSER = os.getenv("VALUESCAN_AUTO_RELOGIN_USE_BROWSER", "1").strip().lower() in ("1", "true", "yes")
LOGIN_METHOD = (os.getenv("VALUESCAN_LOGIN_METHOD") or "auto").strip().lower()
LOGIN_NO_HEADLESS = os.getenv("VALUESCAN_LOGIN_NO_HEADLESS", "0").strip().lower() in ("1", "true", "yes")
SKIP_REFRESH_API = os.getenv("VALUESCAN_SKIP_REFRESH_API", "0").strip().lower() in ("1", "true", "yes")

REFRESH_WINDOW_START_HOUR = int(os.getenv("VALUESCAN_REFRESH_WINDOW_START", "0"))
REFRESH_WINDOW_END_HOUR = int(os.getenv("VALUESCAN_REFRESH_WINDOW_END", "6"))
REFRESH_URGENT_THRESHOLD_S = int(os.getenv("VALUESCAN_REFRESH_URGENT_THRESHOLD", "1800"))
ACCESS_TICKET_KEY = b"BxlAG1lX9daAAHgj"
ACCESS_TICKET_EMPTY = "LNe1VTyHk0bij3cyWB2gxg=="


def _is_refresh_window() -> bool:
    """Check if current time is within the preferred refresh window (default: 0:00-6:00)."""
    now = datetime.now()
    hour = now.hour
    if REFRESH_WINDOW_START_HOUR <= REFRESH_WINDOW_END_HOUR:
        return REFRESH_WINDOW_START_HOUR <= hour < REFRESH_WINDOW_END_HOUR
    else:
        return hour >= REFRESH_WINDOW_START_HOUR or hour < REFRESH_WINDOW_END_HOUR


def _build_refresh_urls(primary_url: str) -> List[str]:
    env_urls = (os.getenv("VALUESCAN_REFRESH_URLS") or "").strip()
    urls: List[str] = []
    if env_urls:
        urls.extend([u.strip() for u in env_urls.split(",") if u.strip()])

    defaults = [
        primary_url,
        "https://api.valuescan.io/api/authority/refresh/{refresh_token}",
        "https://www.valuescan.io/api/authority/refresh/{refresh_token}",
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


def _build_status_urls(primary_url: str) -> List[str]:
    env_urls = (os.getenv("VALUESCAN_TOKEN_STATUS_URLS") or "").strip()
    urls: List[str] = []
    if env_urls:
        urls.extend([u.strip() for u in env_urls.split(",") if u.strip()])

    defaults = [primary_url]
    if "api.valuescan.io" in primary_url:
        defaults.append(primary_url.replace("api.valuescan.io", "www.valuescan.io"))
    elif "www.valuescan.io" in primary_url:
        defaults.append(primary_url.replace("www.valuescan.io", "api.valuescan.io"))

    for url in defaults:
        if url and url not in urls:
            urls.append(url)
    return urls


TOKEN_STATUS_URLS = _build_status_urls(TOKEN_STATUS_URL)


def _load_credentials() -> Dict[str, str]:
    creds = {"email": "", "password": ""}
    try:
        if CREDENTIALS_FILE.exists():
            payload = json.loads(CREDENTIALS_FILE.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                creds["email"] = str(payload.get("email") or "").strip()
                creds["password"] = str(payload.get("password") or "").strip()
    except Exception:
        pass
    env_email = (os.getenv("VALUESCAN_EMAIL") or "").strip()
    env_password = (os.getenv("VALUESCAN_PASSWORD") or "").strip()
    if env_email and env_password:
        creds = {"email": env_email, "password": env_password}
    return creds


def _parse_iso(ts: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(ts)
    except Exception:
        return None


def _relogin_on_cooldown(ls: Dict[str, Any], force: bool = False) -> bool:
    if force:
        return False
    last = ls.get("last_relogin")
    if not isinstance(last, str) or not last.strip():
        return False
    last_dt = _parse_iso(last)
    if not last_dt:
        return False
    return (datetime.now(timezone.utc) - last_dt).total_seconds() < AUTO_RELOGIN_COOLDOWN_S


def _persist_relogin_meta(ls: Dict[str, Any], method: str, success: bool, note: str = "") -> None:
    ls["last_relogin"] = datetime.now(timezone.utc).isoformat()
    ls["last_relogin_method"] = method
    ls["last_relogin_success"] = bool(success)
    if note:
        ls["last_relogin_note"] = note[:500]
    _persist_localstorage(ls)


def _run_login_script(
    script_path: Path,
    env: Dict[str, str],
    args: Optional[list] = None,
    timeout_s: int = 180,
) -> bool:
    if not script_path.exists():
        logger.error("Login helper not found: %s", script_path)
        return False
    try:
        cmd = [sys.executable, str(script_path)]
        if args:
            cmd.extend(args)
        proc = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
    except Exception as exc:
        logger.error("Login helper failed to start: %s", exc)
        return False
    if proc.returncode != 0:
        logger.warning("Login helper exited with code %s", proc.returncode)
        if proc.stderr:
            logger.warning("Login stderr: %s", proc.stderr.strip()[-400:])
        return False
    return True


def _run_browser_login(email: str, password: str) -> bool:
    env = os.environ.copy()
    env["VALUESCAN_EMAIL"] = email
    env["VALUESCAN_PASSWORD"] = password
    env["VALUESCAN_TOKEN_FILE"] = str(TOKEN_FILE)
    base_dir = Path(__file__).resolve().parent / "signal_monitor"
    cdp_script = base_dir / "cdp_token_refresher.py"
    if cdp_script.exists():
        logger.info("Using CDP token refresher for browser login.")
        if _run_login_script(cdp_script, env, args=["--once"], timeout_s=180):
            return True
        logger.warning("CDP token refresher failed; falling back to Chromium login.")
    script = base_dir / "token_refresher.py"
    args = ["--once"]
    if LOGIN_NO_HEADLESS:
        args.append("--no-headless")
    return _run_login_script(script, env, args=args, timeout_s=240)


def _run_http_login(email: str, password: str) -> bool:
    env = os.environ.copy()
    env["VALUESCAN_EMAIL"] = email
    env["VALUESCAN_PASSWORD"] = password
    env["VALUESCAN_TOKEN_FILE"] = str(TOKEN_FILE)
    script = Path(__file__).resolve().parent / "signal_monitor" / "http_api_login.py"
    return _run_login_script(script, env, timeout_s=90)


def _attempt_relogin(ls: Dict[str, Any], reason: str, force: bool = False) -> bool:
    if not AUTO_RELOGIN:
        return False
    backup = dict(ls)
    if _relogin_on_cooldown(ls, force=force):
        logger.info("Relogin skipped (cooldown).")
        return False

    creds = _load_credentials()
    if not creds["email"] or not creds["password"]:
        logger.error("No credentials available for relogin.")
        _persist_relogin_meta(ls, "none", False, "missing_credentials")
        return False

    method = "browser" if AUTO_RELOGIN_USE_BROWSER else "http"
    if LOGIN_METHOD in ("browser", "chromium"):
        method = "browser"
    elif LOGIN_METHOD in ("http", "api"):
        method = "http"

    logger.warning("Relogin triggered (%s). Method=%s", reason, method)
    ok = False
    if method == "browser":
        ok = _run_browser_login(creds["email"], creds["password"])
        if not ok and LOGIN_METHOD in ("auto", "browser"):
            logger.warning("Browser relogin failed; trying HTTP login fallback.")
            ok = _run_http_login(creds["email"], creds["password"])
    else:
        ok = _run_http_login(creds["email"], creds["password"])
        if not ok and LOGIN_METHOD in ("auto", "http"):
            logger.warning("HTTP relogin failed; trying browser login fallback.")
            ok = _run_browser_login(creds["email"], creds["password"])

    ls_after = _load_localstorage()
    token_ok = bool((ls_after.get("account_token") or "").strip())
    _persist_relogin_meta(ls_after if ls_after else ls, method, ok and token_ok, reason)
    if ok and token_ok:
        logger.info("Relogin succeeded.")
        return True
    logger.error("Relogin failed.")
    if backup.get("refresh_token"):
        logger.warning("Restoring previous tokens after relogin failure.")
        _persist_localstorage(backup)
    return False


def _b64url_decode(segment: str) -> bytes:
    seg = (segment or "").strip()
    if not seg:
        return b""
    pad = "=" * (-len(seg) % 4)
    return base64.urlsafe_b64decode((seg + pad).encode("ascii", errors="ignore"))


def _pkcs7_pad(data: bytes, block_size: int = 16) -> bytes:
    pad_len = block_size - (len(data) % block_size)
    return data + bytes([pad_len]) * pad_len


def _compute_access_ticket(ticket: str) -> str:
    raw = (ticket or "").encode("utf-8")
    try:
        from Crypto.Cipher import AES  # type: ignore

        cipher = AES.new(ACCESS_TICKET_KEY, AES.MODE_ECB)
        encrypted = cipher.encrypt(_pkcs7_pad(raw))
        return base64.b64encode(encrypted).decode("ascii")
    except Exception:
        if not raw:
            return ACCESS_TICKET_EMPTY
        try:
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes  # type: ignore
            from cryptography.hazmat.backends import default_backend  # type: ignore

            encryptor = Cipher(
                algorithms.AES(ACCESS_TICKET_KEY),
                modes.ECB(),
                backend=default_backend(),
            ).encryptor()
            encrypted = encryptor.update(_pkcs7_pad(raw)) + encryptor.finalize()
            return base64.b64encode(encrypted).decode("ascii")
        except Exception:
            return ACCESS_TICKET_EMPTY


def _jwt_expiry_seconds(token: str) -> Optional[int]:
    parts = (token or "").split(".")
    if len(parts) < 2:
        return None
    try:
        payload_raw = _b64url_decode(parts[1])
        payload = json.loads(payload_raw.decode("utf-8", errors="ignore") or "null")
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    exp = payload.get("exp")
    if isinstance(exp, int):
        return exp
    if isinstance(exp, str) and exp.strip().isdigit():
        try:
            return int(exp.strip())
        except Exception:
            return None
    return None


def _seconds_until_expiry(token: str) -> Optional[int]:
    exp = _jwt_expiry_seconds(token)
    if not exp:
        return None
    now = int(time.time())
    return max(0, exp - now)


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


def _load_localstorage(retries: int = 3, delay: float = 0.2) -> Dict[str, Any]:
    for attempt in range(max(1, retries)):
        try:
            content = TOKEN_FILE.read_text(encoding="utf-8")
            data = json.loads(content or "null")
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            if attempt < retries - 1:
                time.sleep(delay)
                continue
            return {}
        except FileNotFoundError:
            return {}
        except Exception:
            return {}
    return {}


def _persist_localstorage(data: Dict[str, Any]) -> bool:
    try:
        TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = TOKEN_FILE.with_suffix(TOKEN_FILE.suffix + ".tmp")
        tmp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp_path.replace(TOKEN_FILE)
        return True
    except Exception:
        try:
            tmp_path = TOKEN_FILE.with_suffix(TOKEN_FILE.suffix + ".tmp")
            if tmp_path.exists():
                tmp_path.unlink()
        except Exception:
            pass
        return False


def _refresh(
    session: requests.Session,
    refresh_token_value: str,
    account_token_value: Optional[str] = None,
    ticket_value: Optional[str] = None,
    proxies: Optional[Dict[str, str]] = None,
) -> Optional[Dict[str, str]]:
    if not refresh_token_value:
        return None

    access_ticket = (os.getenv("VALUESCAN_ACCESS_TICKET") or "").strip()
    if not access_ticket:
        access_ticket = _compute_access_ticket(ticket_value or "")
    base_headers = {
        "Content-Type": "application/json",
        "Origin": "https://www.valuescan.io",
        "Referer": "https://www.valuescan.io/",
    }
    if access_ticket:
        base_headers["Access-Ticket"] = access_ticket

    request_modes = [
        ("bearer", {"Authorization": f"Bearer {refresh_token_value}"}, {}),
        ("auth", {"Authorization": refresh_token_value}, {}),
        ("body_refresh_token", {}, {"refresh_token": refresh_token_value}),
        ("body_refreshToken", {}, {"refreshToken": refresh_token_value}),
        ("body_token", {}, {"token": refresh_token_value}),
    ]
    if account_token_value:
        request_modes.insert(0, ("account_bearer", {"Authorization": f"Bearer {account_token_value}"}, {}))

    last_error = ""
    for url in REFRESH_URLS:
        url_has_token = "{refresh_token}" in url
        if url_has_token:
            if not refresh_token_value:
                continue
            url = url.replace("{refresh_token}", refresh_token_value)
            modes = [("path_only", {}, None)] + request_modes
        else:
            modes = request_modes

        for label, extra_headers, payload in modes:
            headers = dict(base_headers)
            headers.update(extra_headers)
            try:
                if payload is None:
                    resp = session.post(
                        url,
                        headers=headers,
                        proxies=proxies,
                        timeout=REQUEST_TIMEOUT_S,
                    )
                else:
                    resp = session.post(
                        url,
                        headers=headers,
                        json=payload,
                        proxies=proxies,
                        timeout=REQUEST_TIMEOUT_S,
                    )
            except requests.RequestException:
                last_error = f"{url} {label} network error"
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
            account_token = (tokens.get("account_token") or "").strip()
            if account_token:
                refresh_token_new = (tokens.get("refresh_token") or refresh_token_value or "").strip()
                return {"account_token": account_token, "refresh_token": refresh_token_new}

            code = payload_json.get("code") if isinstance(payload_json, dict) else None
            if code in (4000, 401, 403):
                last_error = f"{url} code={code}"
                continue

            last_error = f"{url} invalid payload"

    if last_error:
        logger.warning("Refresh request failed: %s", last_error)
    else:
        logger.warning("Refresh request failed: no endpoints available")
    return None


def _check_api_token_status(
    session: requests.Session,
    account_token: str,
    proxies: Optional[Dict[str, str]] = None,
) -> tuple[str, str]:
    if not account_token:
        return ("missing", "missing_account_token")
    headers = {
        "Authorization": f"Bearer {account_token}",
        "Content-Type": "application/json",
    }
    last_reason = "no_response"
    for url in TOKEN_STATUS_URLS:
        try:
            resp = session.get(
                url,
                headers=headers,
                proxies=proxies,
                timeout=TOKEN_STATUS_TIMEOUT_S,
            )
        except requests.RequestException as exc:
            logger.warning("Token status check failed (%s): %s", url, exc)
            last_reason = "request_error"
            continue

        if resp.status_code in (401, 403):
            logger.info("Token status check rejected (http=%s)", resp.status_code)
            return ("invalid", f"http_{resp.status_code}")

        if resp.status_code != 200:
            last_reason = f"http_{resp.status_code}"
            continue

        try:
            payload = resp.json()
        except ValueError:
            last_reason = "non_json"
            continue

        if isinstance(payload, dict):
            code = payload.get("code")
            if code in (4000, 4002, 401, 403):
                logger.info("Token status check rejected (code=%s)", code)
                return ("invalid", f"code_{code}")

        return ("valid", "ok")

    return ("unknown", last_reason)


def _check_api_token_valid(
    session: requests.Session,
    account_token: str,
    proxies: Optional[Dict[str, str]] = None,
) -> bool:
    status, _ = _check_api_token_status(session, account_token, proxies=proxies)
    return status in ("valid", "unknown")


def main() -> int:
    session = requests.Session()
    proxy = (os.getenv("SOCKS5_PROXY") or os.getenv("VALUESCAN_SOCKS5_PROXY") or os.getenv("VALUESCAN_PROXY") or "").strip()
    proxies = {"http": proxy, "https": proxy} if proxy else None
    logger.info("Token refresher started. token_file=%s refresh_urls=%s", TOKEN_FILE, REFRESH_URLS)

    while True:
        ls = _load_localstorage()
        refresh_token_value = (ls.get("refresh_token") or "").strip()
        account_token = (ls.get("account_token") or "").strip()
        ticket_value = (ls.get("ticket") or "").strip()

        if not refresh_token_value:
            logger.warning("Refresh token missing.")
            _attempt_relogin(ls, "missing_refresh_token", force=not account_token)
            time.sleep(CHECK_INTERVAL_S)
            continue

        token_valid = _check_api_token_valid(session, account_token, proxies=proxies) if account_token else False
        should_refresh = not token_valid

        if should_refresh:
            if SKIP_REFRESH_API:
                logger.warning("Refresh API disabled; attempting relogin.")
                _attempt_relogin(ls, "refresh_skipped", force=not account_token)
            else:
                updated = _refresh(
                    session,
                    refresh_token_value,
                    account_token_value=account_token,
                    ticket_value=ticket_value,
                    proxies=proxies,
                )
                if updated:
                    ls["account_token"] = updated["account_token"]
                    ls["refresh_token"] = updated["refresh_token"]
                    ls["last_refresh"] = datetime.now(timezone.utc).isoformat()
                    if _persist_localstorage(ls):
                        logger.info("Token refreshed successfully.")
                else:
                    logger.warning("Token refresh failed; attempting relogin.")
                    _attempt_relogin(ls, "refresh_failed", force=not account_token)

        time.sleep(CHECK_INTERVAL_S)


if __name__ == "__main__":
    raise SystemExit(main())
