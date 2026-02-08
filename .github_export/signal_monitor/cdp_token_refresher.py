#!/usr/bin/env python3
"""
CDP-based token refresher for VPS environments with limited memory.

This module uses Chrome DevTools Protocol (CDP) to login via an existing
or freshly started headless browser, avoiding the memory overhead of
DrissionPage launching new browser instances.

Usage:
    # Run as standalone service
    python cdp_token_refresher.py --interval 0.8
    
    # Or import and use programmatically
    from cdp_token_refresher import cdp_refresh_token, run_cdp_refresh_loop
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Paths
BASE_DIR = Path(__file__).resolve().parent
LOCALSTORAGE_FILE = Path(os.getenv("VALUESCAN_TOKEN_FILE") or BASE_DIR / "valuescan_localstorage.json")
CREDENTIALS_FILE = BASE_DIR / "valuescan_credentials.json"
CHROME_PROFILE_DIR = Path(os.getenv("VALUESCAN_CDP_PROFILE_DIR") or BASE_DIR / "chrome-debug-profile-cdp")
_CDP_LOG_HANDLE = None

# Configuration
CDP_PORT = int(os.getenv("VALUESCAN_CDP_PORT", "9222"))
CDP_HEADLESS = os.getenv("VALUESCAN_CDP_HEADLESS", "").strip().lower() in ("1", "true", "yes")
TOKEN_REFRESH_INTERVAL_HOURS = float(os.getenv("VALUESCAN_TOKEN_REFRESH_INTERVAL_HOURS", "0.8"))
TOKEN_REFRESH_SAFETY_SECONDS = int(os.getenv("VALUESCAN_TOKEN_REFRESH_SAFETY_SECONDS", "300"))
LOGIN_RETRY_COOLDOWN_SECONDS = int(os.getenv("VALUESCAN_LOGIN_RETRY_COOLDOWN_SECONDS", "60"))
BROWSER_STARTUP_TIMEOUT = int(os.getenv("VALUESCAN_BROWSER_STARTUP_TIMEOUT", "30"))
LOGIN_LOCK_TIMEOUT_SECONDS = int(os.getenv("VALUESCAN_LOGIN_LOCK_TIMEOUT_SECONDS", "180"))
LOGIN_LOCK_STALE_SECONDS = int(os.getenv("VALUESCAN_LOGIN_LOCK_STALE_SECONDS", "1200"))
LOGIN_TIMEOUT_SECONDS = int(os.getenv("VALUESCAN_LOGIN_TIMEOUT_SECONDS", "300"))  # 登录超时300秒

REFRESH_WINDOW_START_HOUR = int(os.getenv("VALUESCAN_REFRESH_WINDOW_START", "0"))
REFRESH_WINDOW_END_HOUR = int(os.getenv("VALUESCAN_REFRESH_WINDOW_END", "6"))
REFRESH_URGENT_THRESHOLD_SECONDS = int(os.getenv("VALUESCAN_REFRESH_URGENT_THRESHOLD", "1800"))

# 主力位图像生成有效期（天）
KEY_LEVELS_CHART_DAYS = int(os.getenv("VALUESCAN_KEY_LEVELS_CHART_DAYS", "7"))
# AI分析模块有效期（天）
KEY_LEVELS_AI_ANALYSIS_DAYS = int(os.getenv("VALUESCAN_AI_ANALYSIS_DAYS", "15"))


def _login_lock_path() -> Path:
    env_path = (os.getenv("VALUESCAN_LOGIN_LOCK_FILE") or "").strip()
    if env_path:
        return Path(env_path)
    return Path(tempfile.gettempdir()) / "valuescan_login_refresh.lock"


@contextmanager
def _login_lock(timeout_seconds: int = LOGIN_LOCK_TIMEOUT_SECONDS):
    """
    Cross-process lock to prevent concurrent Chromium logins.
    """
    lock_path = _login_lock_path()
    deadline = time.time() + max(1, int(timeout_seconds))
    while True:
        try:
            lock_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            try:
                os.write(fd, str(os.getpid()).encode("utf-8", errors="ignore"))
            except Exception:
                pass
            try:
                os.close(fd)
            except Exception:
                pass

            try:
                yield True
            finally:
                try:
                    lock_path.unlink(missing_ok=True)
                except TypeError:
                    try:
                        if lock_path.exists():
                            lock_path.unlink()
                    except Exception:
                        pass
                except Exception:
                    pass
            return
        except FileExistsError:
            try:
                if time.time() - lock_path.stat().st_mtime > LOGIN_LOCK_STALE_SECONDS:
                    lock_path.unlink()
                    continue
            except Exception:
                pass
            if time.time() >= deadline:
                yield False
                return
            time.sleep(1)


def _is_refresh_window() -> bool:
    """Check if current time is within the preferred refresh window (default: 0:00-6:00)."""
    now = datetime.now()
    hour = now.hour
    if REFRESH_WINDOW_START_HOUR <= REFRESH_WINDOW_END_HOUR:
        return REFRESH_WINDOW_START_HOUR <= hour < REFRESH_WINDOW_END_HOUR
    else:
        return hour >= REFRESH_WINDOW_START_HOUR or hour < REFRESH_WINDOW_END_HOUR


def _atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    """Atomic write to avoid half-written JSON."""
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp_path, path)


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8") or "null") if path.exists() else {}
    except Exception:
        return {}


def load_credentials() -> Optional[Dict[str, str]]:
    """Load saved login credentials."""
    data = _load_json(CREDENTIALS_FILE)
    if not data:
        return None
    email = (data.get("email") or "").strip()
    password = (data.get("password") or "").strip()
    if email and password:
        return {"email": email, "password": password}
    return None


def save_credentials(email: str, password: str) -> bool:
    """Persist login credentials."""
    try:
        _atomic_write_json(CREDENTIALS_FILE, {"email": email, "password": password})
        try:
            os.chmod(CREDENTIALS_FILE, 0o600)
        except Exception:
            pass
        logger.info("Credentials saved.")
        return True
    except Exception as exc:
        logger.error("Failed to save credentials: %s", exc)
        return False


def _jwt_expiry_seconds(token: str) -> Optional[int]:
    """Extract expiry timestamp from JWT token."""
    import base64
    parts = (token or "").split(".")
    if len(parts) < 2:
        return None
    try:
        payload = parts[1]
        payload += "=" * (-len(payload) % 4)
        decoded = json.loads(base64.urlsafe_b64decode(payload))
        exp = decoded.get("exp")
        if isinstance(exp, int):
            return exp
    except Exception:
        pass
    return None


def _seconds_until_expiry(token: str) -> Optional[int]:
    exp = _jwt_expiry_seconds(token)
    if not exp:
        return None
    return max(0, exp - int(time.time()))


def _pick_token_from_storage(data: Dict[str, Any]) -> str:
    def _is_valid_token_value(token: str) -> bool:
        if not token:
            return False
        stripped = token.strip()
        if not stripped:
            return False
        if stripped.lower() in {"null", "none", "undefined"}:
            return False
        return True

    for key in ("account_token", "accountToken", "token", "access_token", "accessToken"):
        val = data.get(key)
        if isinstance(val, str) and _is_valid_token_value(val):
            return val.strip()
    return ""


def get_token_status() -> Tuple[bool, Optional[int], Optional[datetime]]:
    """
    Get current token status.
    Returns: (is_valid, seconds_remaining, expiry_datetime)
    
    ???is_valid ??? token ???????? API ?? 401/4000 ???
    """
    data = _load_json(LOCALSTORAGE_FILE)
    token = (data.get("account_token") or "").strip()
    if not token:
        return False, None, None
    return True, None, None


def _find_browser_path() -> str:
    """Find Chromium/Chrome executable."""
    import platform
    import sys

    # Windows paths
    if platform.system() == "Windows":
        candidates = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe"),
        ]
    # Linux paths
    else:
        candidates = [
            "/usr/bin/chromium-browser",
            "/usr/bin/chromium",
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
        ]

    for path in candidates:
        if os.path.exists(path):
            return path
    return ""


def _is_browser_running() -> bool:
    """Check if browser is running on CDP port."""
    try:
        import requests
        resp = requests.get(f"http://127.0.0.1:{CDP_PORT}/json", timeout=5)
        return resp.status_code == 200
    except Exception:
        return False


def _restart_browser_if_needed() -> bool:
    """
    Check if browser is running and restart if not.
    Returns True if browser is running after this call.
    """
    if _is_browser_running():
        return True
    logger.warning("Browser not responding on port %d, attempting restart...", CDP_PORT)
    _kill_browser()
    return _start_browser()


def _kill_browser() -> None:
    """Kill existing browser processes."""
    try:
        subprocess.run(['pkill', '-9', 'chromium'], capture_output=True, timeout=5)
        subprocess.run(['pkill', '-9', 'chrome'], capture_output=True, timeout=5)
    except Exception:
        pass
    time.sleep(2)


def _kill_zombie_browsers() -> None:
    """Kill all zombie/orphan browser processes before starting."""
    logger.info("Cleaning up zombie browser processes...")
    try:
        # Kill any orphaned chromium processes
        subprocess.run(['pkill', '-9', '-f', 'chromium'], capture_output=True, timeout=10)
        subprocess.run(['pkill', '-9', '-f', 'chrome'], capture_output=True, timeout=10)
    except Exception:
        pass
    time.sleep(1)


def _is_chrome_process_running() -> bool:
    """Check if any Chrome/Chromium process is already running."""
    try:
        result = subprocess.run(['pgrep', '-f', 'chrom'], capture_output=True, timeout=5)
        return result.returncode == 0
    except Exception:
        return False


def _check_api_token_valid() -> bool:
    """
    Check if token is valid by actually calling ValuScan API.
    Only returns False if server rejects the token (4000/4002/401).
    """
    try:
        import requests
        data = _load_json(LOCALSTORAGE_FILE)
        token = (data.get("account_token") or "").strip()
        if not token:
            return False
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        resp = requests.get(
            "https://api.valuescan.io/api/account/message/getWarnMessage",
            headers=headers,
            timeout=15,
        )
        result = resp.json()
        code = result.get("code")
        
        # 4000/4002 = token expired, 401/403 = unauthorized
        if code in (4000, 4002) or resp.status_code in (401, 403):
            logger.info("API rejected token (code=%s), needs refresh", code)
            return False
        
        return True
    except Exception as e:
        logger.warning("API check failed: %s", e)
        return True  # On network error, assume token is valid


def _start_browser() -> bool:
    """Start headless browser with CDP enabled."""
    global _CDP_LOG_HANDLE
    browser_path = _find_browser_path()
    if not browser_path:
        logger.error("Browser executable not found")
        return False
    
    CHROME_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    
    cmd = [
        browser_path,
        f"--remote-debugging-port={CDP_PORT}",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--no-first-run",
        "--no-default-browser-check",
        "--dns-over-https-mode=off",
        "--disable-features=UseDnsOverHttps,UseDnsHttpsSvcb",
        f"--user-data-dir={CHROME_PROFILE_DIR}",
        "--remote-allow-origins=*",
    ]
    if CDP_HEADLESS:
        cmd.insert(1, "--headless=new")

    log_path = (os.getenv("VALUESCAN_CDP_LOG_FILE") or "").strip()
    stdout_target = subprocess.DEVNULL
    stderr_target = subprocess.DEVNULL
    if log_path:
        try:
            log_file = open(log_path, "a", encoding="utf-8")
            _CDP_LOG_HANDLE = log_file
            stdout_target = log_file
            stderr_target = log_file
            cmd.extend(["--enable-logging=stderr", "--v=1"])
        except Exception as exc:
            logger.warning("Failed to open CDP log file: %s", exc)
    
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=stdout_target,
            stderr=stderr_target,
            start_new_session=True
        )
        logger.info("Browser started (pid=%s)", proc.pid)
    except Exception as exc:
        logger.error("Failed to start browser: %s", exc)
        return False
    
    # Wait for browser to be ready
    for i in range(BROWSER_STARTUP_TIMEOUT):
        time.sleep(1)
        if _is_browser_running():
            logger.info("Browser ready after %ds", i + 1)
            return True
    
    logger.error("Browser failed to start within timeout")
    return False


def _ensure_browser_running() -> bool:
    """Ensure browser is running, start if needed."""
    if _is_browser_running():
        return True
    
    logger.info("Browser not running, starting...")
    _kill_browser()
    return _start_browser()


def cdp_refresh_token(email: str, password: str) -> bool:
    """Refresh token using CDP protocol with a cross-process login lock."""
    with _login_lock() as acquired:
        if not acquired:
            logger.warning("Login lock is held by another process; skipping this refresh attempt.")
            return False
        return _cdp_refresh_token_inner(email, password)


def _cdp_refresh_token_inner(email: str, password: str) -> bool:
    """
    Refresh token using CDP protocol.
    
    This function:
    1. Ensures browser is running
    2. Navigates to login page
    3. Fills credentials and submits
    4. Extracts token from localStorage
    5. Saves token to file
    """
    try:
        import requests
        import websocket
    except ImportError:
        logger.error("Required packages not installed: requests, websocket-client")
        return False
    
    if not _ensure_browser_running():
        return False
    
    logger.info("Starting CDP login...")
    
    try:
        def _fetch_targets(retry_on_failure: bool = True) -> list:
            """Fetch CDP targets with optional browser restart on failure."""
            max_attempts = 3 if retry_on_failure else 1
            for attempt in range(max_attempts):
                try:
                    resp = requests.get(f"http://127.0.0.1:{CDP_PORT}/json", timeout=10)
                    data = resp.json()
                    return data if isinstance(data, list) else []
                except Exception as exc:
                    logger.warning("Failed to fetch CDP targets (attempt %d/%d): %s", 
                                   attempt + 1, max_attempts, exc)
                    if attempt < max_attempts - 1 and retry_on_failure:
                        logger.info("Attempting to restart browser...")
                        if _restart_browser_if_needed():
                            time.sleep(2)
                            continue
                        else:
                            logger.error("Browser restart failed")
                            break
            return []

        def _select_page_target(targets: list) -> Optional[Dict[str, Any]]:
            pages = [t for t in targets if t.get("type") == "page"]
            if not pages:
                return None
            def _is_bad_url(url: str) -> bool:
                url = (url or "").lower().strip()
                return (
                    not url
                    or url.startswith("chrome-error://")
                    or url.startswith("chrome://")
                    or url.startswith("about:")
                )

            valid_pages = []
            for t in pages:
                url = (t.get("url") or "").lower().strip()
                if _is_bad_url(url):
                    continue
                if url.startswith("http://") or url.startswith("https://"):
                    valid_pages.append(t)

            for t in valid_pages:
                url = (t.get("url") or "").lower()
                if "valuescan" in url:
                    return t
            if valid_pages:
                return valid_pages[0]

            for t in pages:
                url = (t.get("url") or "").lower()
                if "valuescan" in url:
                    return t
            return pages[0]

        def _open_new_page() -> None:
            try:
                requests.put(
                    f"http://127.0.0.1:{CDP_PORT}/json/new?https://www.valuescan.io/login",
                    timeout=15,
                )
            except Exception as exc:
                logger.warning("Failed to open new page: %s", exc)

        def _open_ws() -> Optional[Tuple[Any, str, str]]:
            targets = _fetch_targets()
            page_target = _select_page_target(targets)
            if not page_target:
                logger.info("Creating new page...")
                _open_new_page()
                time.sleep(4)
                targets = _fetch_targets()
                page_target = _select_page_target(targets)
            if not page_target:
                logger.error("No page target found")
                return None

            ws_url = page_target.get("webSocketDebuggerUrl")
            if not ws_url:
                logger.error("Missing webSocketDebuggerUrl")
                return None
            current_url = page_target.get("url", "")
            try:
                ws = websocket.create_connection(ws_url, timeout=10)
                ws.settimeout(5)
                return ws, ws_url, current_url
            except Exception as exc:
                logger.warning("Failed to connect websocket: %s", exc)
                return None

        opened = _open_ws()
        if not opened:
            return False
        ws, ws_url, current_url = opened
        logger.info("Page URL: %s", current_url)

        msg_id = 0

        def _enable_domains() -> None:
            for method in ("Page.enable", "Runtime.enable", "Network.enable"):
                try:
                    cdp(method)
                except Exception:
                    pass

        def _wait_for_dom_ready(timeout_seconds: int = 30) -> bool:
            deadline = time.time() + max(1, int(timeout_seconds))
            while time.time() < deadline:
                r = cdp("Runtime.evaluate", {"expression": "document.readyState"})
                if r:
                    state = r.get("result", {}).get("result", {}).get("value", "")
                    if isinstance(state, str) and state.lower() in ("interactive", "complete"):
                        return True
                time.sleep(1)
            return False

        def _wait_for_login_inputs(timeout_seconds: int = 20) -> bool:
            deadline = time.time() + max(1, int(timeout_seconds))
            while time.time() < deadline:
                r = cdp(
                    "Runtime.evaluate",
                    {
                        "expression": (
                            "(() => {"
                            "const norm = (s) => String(s || '').toLowerCase().replace(/\\s+/g, ' ').trim();"
                            "const inputs = Array.from(document.querySelectorAll('input, textarea'));"
                            "const isVisible = (el) => {"
                            "  if (!el || !el.getBoundingClientRect) return false;"
                            "  const r = el.getBoundingClientRect();"
                            "  return r.width > 0 && r.height > 0;"
                            "};"
                            "for (const i of inputs) {"
                            "  if (!isVisible(i)) continue;"
                            "  const t = norm(i.type);"
                            "  const n = norm(i.name);"
                            "  const ph = norm(i.placeholder);"
                            "  const ac = norm(i.autocomplete);"
                            "  const aria = norm(i.getAttribute && i.getAttribute('aria-label'));"
                            "  if (t === 'password') return true;"
                            "  if (t === 'email' || ph.includes('email') || ph.includes('mail') || ph.includes('邮箱') || "
                            "      n.includes('email') || n.includes('account') || n.includes('user') || "
                            "      aria.includes('email') || aria.includes('邮箱') || ac.includes('username')) return true;"
                            "}"
                            "return false;"
                            "})()"
                        )
                    },
                )
                if r and r.get("result", {}).get("result", {}).get("value"):
                    return True
                time.sleep(1)
            return False

        def _dismiss_logout_dialog() -> None:
            js = """(() => {
                const text = (document.body && document.body.innerText) || '';
                if (!text.includes('账号已下线') && !text.includes('请重新登录')) {
                    return 'no_logout_dialog';
                }
                const buttons = Array.from(document.querySelectorAll('button, [role="button"], a'));
                const target = buttons.find((b) => /确认|ok|confirm/i.test((b.textContent || '').trim()));
                if (target) {
                    target.click();
                    return 'clicked_confirm';
                }
                return 'confirm_not_found';
            })()"""
            r = cdp("Runtime.evaluate", {"expression": js})
            if r:
                val = r.get("result", {}).get("result", {}).get("value", "")
                if isinstance(val, str) and val and val != "no_logout_dialog":
                    logger.info("Logout dialog: %s", val)

        def _reconnect() -> bool:
            nonlocal ws, ws_url, current_url
            try:
                ws.close()
            except Exception:
                pass
            reopened = _open_ws()
            if not reopened:
                return False
            ws, ws_url, current_url = reopened
            logger.info("Reconnected to CDP target: %s", current_url)
            _enable_domains()
            return True

        def cdp(method: str, params: Optional[Dict] = None, retries: int = 1) -> Optional[Dict]:
            nonlocal msg_id
            attempt = 0
            while attempt <= retries:
                msg_id += 1
                msg = {"id": msg_id, "method": method}
                if params:
                    msg["params"] = params
                try:
                    ws.send(json.dumps(msg))
                except Exception as exc:
                    logger.warning("CDP send error: %s", exc)
                    if attempt < retries and _reconnect():
                        attempt += 1
                        continue
                    return None

                deadline = time.time() + 10
                while time.time() < deadline:
                    try:
                        data = ws.recv()
                        result = json.loads(data)
                        if result.get("id") == msg_id:
                            return result
                    except websocket.WebSocketTimeoutException:
                        continue
                    except Exception as exc:
                        logger.warning("CDP error: %s", exc)
                        if attempt < retries and _reconnect():
                            attempt += 1
                            break
                        return None
                attempt += 1
            return None

        _enable_domains()
        
        # Navigate to login if needed
        if "login" not in current_url.lower():
            logger.info("Navigating to login page...")
            cdp("Page.navigate", {"url": "https://www.valuescan.io/login"})
            _wait_for_dom_ready(timeout_seconds=15)
            time.sleep(2)
        _dismiss_logout_dialog()
        
        # Check if already logged in (redirected)
        r = cdp("Runtime.evaluate", {"expression": "window.location.href"})
        if r:
            url = r.get("result", {}).get("result", {}).get("value", "")
            logger.info("Current URL: %s", url)
            url_lower = (url or "").lower().strip()
            is_bad_url = (
                not url_lower
                or url_lower.startswith("chrome-error://")
                or url_lower.startswith("chrome://")
                or url_lower.startswith("about:")
            )
            if is_bad_url:
                logger.warning("Invalid browser URL detected; navigating to login.")
                try:
                    err_preview = cdp("Runtime.evaluate", {
                        "expression": "document.body && document.body.innerText ? document.body.innerText.slice(0, 200) : ''"
                    })
                    if err_preview:
                        err_text = err_preview.get("result", {}).get("result", {}).get("value", "")
                        if isinstance(err_text, str) and err_text.strip():
                            logger.warning("Browser error preview: %s", err_text.strip().replace('\\n', ' '))
                except Exception:
                    pass
                cdp("Page.navigate", {"url": "https://www.valuescan.io/login"})
                _wait_for_dom_ready(timeout_seconds=20)
                time.sleep(2)
            elif "login" not in url_lower and (url_lower.startswith("http://") or url_lower.startswith("https://")):
                logger.info("Already logged in, extracting token...")
                # Already logged in, just get token
                r = cdp("Runtime.evaluate", {"expression": "JSON.stringify(localStorage)"})
                ls_data = {}
                if r:
                    ls_str = r.get("result", {}).get("result", {}).get("value", "{}")
                    try:
                        ls_data = json.loads(ls_str)
                    except Exception:
                        ls_data = {}
                r = cdp("Runtime.evaluate", {"expression": "JSON.stringify(sessionStorage)"})
                ss_data = {}
                if r:
                    ss_str = r.get("result", {}).get("result", {}).get("value", "{}")
                    try:
                        ss_data = json.loads(ss_str)
                    except Exception:
                        ss_data = {}

                token = _pick_token_from_storage(ls_data) or _pick_token_from_storage(ss_data)
                if token:
                    if "account_token" not in ls_data:
                        ls_data["account_token"] = token
                    _atomic_write_json(LOCALSTORAGE_FILE, ls_data)
                    logger.info("Token extracted from existing session")
                    ws.close()
                    return True
        
        # Fill email
        logger.info("Filling email...")
        _wait_for_dom_ready(timeout_seconds=10)
        if not _wait_for_login_inputs(timeout_seconds=15):
            logger.warning("Login inputs not detected yet; attempting to open login form.")
            url_check = cdp("Runtime.evaluate", {"expression": "window.location.href"})
            if url_check:
                cur_url = (url_check.get("result", {}).get("result", {}).get("value", "") or "").lower().strip()
                if cur_url.startswith("chrome-error://") or cur_url.startswith("chrome://") or cur_url.startswith("about:"):
                    logger.warning("Login page not loaded; opening a fresh tab.")
                    _open_new_page()
                    time.sleep(3)
                    _reconnect()
            js_open_login = """(() => {
                const labels = ['login', 'log in', 'sign in', 'continue', '登录', '登陆'];
                const clickable = Array.from(document.querySelectorAll('a, button, [role="button"]'));
                for (const el of clickable) {
                    const text = (el.textContent || el.getAttribute('aria-label') || '').toLowerCase().trim();
                    const href = (el.getAttribute && el.getAttribute('href')) || '';
                    if (labels.some((l) => text.includes(l)) || href.toLowerCase().includes('login')) {
                        el.click();
                        return 'clicked';
                    }
                }
                return 'not_found';
            })()"""
            r = cdp("Runtime.evaluate", {"expression": js_open_login})
            if r:
                val = r.get("result", {}).get("result", {}).get("value", "")
                if isinstance(val, str) and val:
                    logger.info("Login trigger: %s", val)
            _wait_for_login_inputs(timeout_seconds=10)
            _dismiss_logout_dialog()
        email_json = json.dumps(email or "")
        js_email = f"""(() => {{
            try {{
                const EMAIL = {email_json};
                const norm = (s) => String(s || '').toLowerCase().replace(/\\s+/g, ' ').trim();
                const isVisible = (el) => {{
                    if (!el || !el.getBoundingClientRect) return false;
                    const style = window.getComputedStyle(el);
                    if (style && (style.display === 'none' || style.visibility === 'hidden')) return false;
                    const r = el.getBoundingClientRect();
                    return r.width > 0 && r.height > 0;
                }};
                const isEnabled = (el) => !el.disabled && !el.readOnly;
                const setValue = (el, value) => {{
                    const proto = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(el), 'value') ||
                        Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value');
                    if (proto && proto.set) {{
                        proto.set.call(el, value);
                    }} else {{
                        el.value = value;
                    }}
                }};
                const roots = [];
                const seen = new Set();
                const pushRoot = (root) => {{
                    if (root && !seen.has(root)) {{
                        seen.add(root);
                        roots.push(root);
                    }}
                }};
                pushRoot(document);
                try {{
                    const iframes = Array.from(document.querySelectorAll('iframe'));
                    for (const f of iframes) {{
                        try {{
                            if (f.contentDocument) pushRoot(f.contentDocument);
                        }} catch (e) {{}}
                    }}
                }} catch (e) {{}}

                const candidates = [];
                const allInputs = [];
                while (roots.length) {{
                    const root = roots.pop();
                    try {{
                        const inputs = root.querySelectorAll ? Array.from(root.querySelectorAll('input, textarea')) : [];
                        for (const i of inputs) {{
                            if (!isVisible(i) || !isEnabled(i)) continue;
                            allInputs.push(i);
                            const t = norm(i.type);
                            const n = norm(i.name);
                            const ph = norm(i.placeholder);
                            const ac = norm(i.autocomplete);
                            const aria = norm(i.getAttribute && i.getAttribute('aria-label'));
                            const id = norm(i.id);
                            if (
                                t === 'email' ||
                                n.includes('email') || n.includes('account') || n.includes('user') ||
                                ph.includes('email') || ph.includes('mail') || ph.includes('邮箱') ||
                                aria.includes('email') || aria.includes('邮箱') ||
                                ac.includes('username') || id.includes('email')
                            ) {{
                                candidates.push(i);
                            }}
                        }}
                        const nodes = root.querySelectorAll ? Array.from(root.querySelectorAll('*')) : [];
                        for (const n of nodes) {{
                            try {{
                                if (n.shadowRoot) pushRoot(n.shadowRoot);
                            }} catch (e) {{}}
                        }}
                    }} catch (e) {{}}
                }}

                const fallback = allInputs.find((i) => norm(i.type) !== 'password') || allInputs[0];
                const target = candidates[0] || fallback;
                if (target) {{
                    target.focus();
                    setValue(target, EMAIL);
                    target.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    target.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    target.dispatchEvent(new Event('blur', {{ bubbles: true }}));
                    if (candidates.length) return 'ok';
                    return 'fallback';
                }}
                return 'not_found';
            }} catch (e) {{
                return 'js_error:' + (e && e.message ? e.message : String(e));
            }}
        }})()"""
        email_filled = False
        for attempt in range(3):
            r = cdp("Runtime.evaluate", {"expression": js_email})
            if r:
                val = r.get("result", {}).get("result", {}).get("value", "error")
                logger.info("Email: %s", val)
                if isinstance(val, str) and val.startswith("js_error:"):
                    logger.warning("Email JS error: %s", val)
                if r.get("exceptionDetails"):
                    logger.warning("Email JS exception: %s", r.get("exceptionDetails", {}).get("text"))
                if val in ("ok", "fallback"):
                    email_filled = True
                    break
            else:
                logger.warning("Email evaluate returned no response.")
            time.sleep(1)
        if not email_filled:
            logger.warning("Email input not filled; continuing with password step.")
        
        time.sleep(0.5)
        
        # Fill password
        logger.info("Filling password...")
        password_json = json.dumps(password or "")
        js_pwd = f"""(() => {{
            try {{
                const PASSWORD = {password_json};
                const norm = (s) => String(s || '').toLowerCase().replace(/\\s+/g, ' ').trim();
                const isVisible = (el) => {{
                    if (!el || !el.getBoundingClientRect) return false;
                    const style = window.getComputedStyle(el);
                    if (style && (style.display === 'none' || style.visibility === 'hidden')) return false;
                    const r = el.getBoundingClientRect();
                    return r.width > 0 && r.height > 0;
                }};
                const isEnabled = (el) => !el.disabled && !el.readOnly;
                const setValue = (el, value) => {{
                    const proto = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(el), 'value') ||
                        Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value');
                    if (proto && proto.set) {{
                        proto.set.call(el, value);
                    }} else {{
                        el.value = value;
                    }}
                }};
                const roots = [];
                const seen = new Set();
                const pushRoot = (root) => {{
                    if (root && !seen.has(root)) {{
                        seen.add(root);
                        roots.push(root);
                    }}
                }};
                pushRoot(document);
                try {{
                    const iframes = Array.from(document.querySelectorAll('iframe'));
                    for (const f of iframes) {{
                        try {{
                            if (f.contentDocument) pushRoot(f.contentDocument);
                        }} catch (e) {{}}
                    }}
                }} catch (e) {{}}

                const candidates = [];
                const allInputs = [];
                while (roots.length) {{
                    const root = roots.pop();
                    try {{
                        const inputs = root.querySelectorAll ? Array.from(root.querySelectorAll('input, textarea')) : [];
                        for (const i of inputs) {{
                            if (!isVisible(i) || !isEnabled(i)) continue;
                            allInputs.push(i);
                            const t = norm(i.type);
                            const n = norm(i.name);
                            const ph = norm(i.placeholder);
                            const ac = norm(i.autocomplete);
                            const aria = norm(i.getAttribute && i.getAttribute('aria-label'));
                            const id = norm(i.id);
                            if (
                                t === 'password' ||
                                n.includes('password') || n.includes('passwd') || n.includes('pwd') ||
                                ph.includes('password') || ph.includes('密码') ||
                                aria.includes('password') || aria.includes('密码') ||
                                ac.includes('current-password') || ac.includes('new-password') ||
                                id.includes('password')
                            ) {{
                                candidates.push(i);
                            }}
                        }}
                        const nodes = root.querySelectorAll ? Array.from(root.querySelectorAll('*')) : [];
                        for (const n of nodes) {{
                            try {{
                                if (n.shadowRoot) pushRoot(n.shadowRoot);
                            }} catch (e) {{}}
                        }}
                    }} catch (e) {{}}
                }}

                const fallback = allInputs.find((i) => norm(i.type) === 'password') || allInputs[1];
                const target = candidates[0] || fallback;
                if (target) {{
                    target.focus();
                    setValue(target, PASSWORD);
                    target.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    target.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    target.dispatchEvent(new Event('blur', {{ bubbles: true }}));
                    if (candidates.length) return 'ok';
                    if (target === allInputs[1]) return 'fallback_second';
                    return 'fallback';
                }}
                return 'not_found';
            }} catch (e) {{
                return 'js_error:' + (e && e.message ? e.message : String(e));
            }}
        }})()"""
        password_filled = False
        for attempt in range(3):
            r = cdp("Runtime.evaluate", {"expression": js_pwd})
            if r:
                val = r.get("result", {}).get("result", {}).get("value", "error")
                logger.info("Password: %s", val)
                if isinstance(val, str) and val.startswith("js_error:"):
                    logger.warning("Password JS error: %s", val)
                if r.get("exceptionDetails"):
                    logger.warning("Password JS exception: %s", r.get("exceptionDetails", {}).get("text"))
                if val in ("ok", "fallback", "fallback_second"):
                    password_filled = True
                    break
            else:
                logger.warning("Password evaluate returned no response.")
            time.sleep(1)
        if not password_filled:
            logger.warning("Password input not filled; continuing anyway.")
        
        time.sleep(0.5)

        # Ensure terms checkbox is checked if present
        logger.info("Ensuring terms checkbox...")
        js_terms = """(() => {
            const isVisible = (el) => {
                if (!el || !el.getBoundingClientRect) return false;
                const style = window.getComputedStyle(el);
                if (style && (style.display === 'none' || style.visibility === 'hidden')) return false;
                const r = el.getBoundingClientRect();
                return r.width > 0 && r.height > 0;
            };
            const labels = ['agree', 'terms', 'policy', '同意', '服务', '条款', '协议'];
            const checkboxes = Array.from(document.querySelectorAll('input[type="checkbox"]')).filter(isVisible);
            const findByLabel = (cb) => {
                const label = cb.closest && cb.closest('label');
                const text = (label && label.innerText) || (cb.parentElement && cb.parentElement.innerText) || '';
                return labels.some((l) => text.toLowerCase().includes(String(l).toLowerCase()));
            };
            const target = checkboxes.find(findByLabel) || checkboxes[0];
            if (!target) return 'not_found';
            if (!target.checked) {
                if (target.disabled) target.disabled = false;
                target.click();
                target.dispatchEvent(new Event('change', { bubbles: true }));
                return 'checked';
            }
            return 'already_checked';
        })()"""
        r = cdp("Runtime.evaluate", {"expression": js_terms})
        if r:
            val = r.get("result", {}).get("result", {}).get("value", "")
            if val:
                logger.info("Terms checkbox: %s", val)
        
        # Click login with improved button detection
        logger.info("Clicking login...")
        js_click = """(() => {
            // Try multiple strategies to find and click login button

            // Strategy 1: Find by text content (English and Chinese)
            const labels = ['login', 'log in', 'sign in', 'continue', '登录', '登入'];
            const buttons = Array.from(document.querySelectorAll('button, [role="button"], input[type="submit"], input[type="button"], a.btn, a.button'));

            for (const btn of buttons) {
                const text = (btn.textContent || btn.value || btn.getAttribute('aria-label') || '').toLowerCase().trim();
                if (labels.some((l) => text.includes(l.toLowerCase()))) {
                    console.log('Found login button by text:', text);
                    if (btn.disabled) {
                        btn.disabled = false;
                        btn.removeAttribute('disabled');
                    }
                    btn.click();
                    return 'clicked_button';
                }
            }

            // Strategy 2: Find submit button in form
            const forms = document.querySelectorAll('form');
            for (const form of forms) {
                const submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
                if (submitBtn) {
                    console.log('Found submit button in form');
                    if (submitBtn.disabled) {
                        submitBtn.disabled = false;
                        submitBtn.removeAttribute('disabled');
                    }
                    submitBtn.click();
                    return 'clicked_submit';
                }
            }

            // Strategy 3: Try to submit form directly (last resort)
            const form = document.querySelector('form');
            if (form) {
                console.log('Submitting form directly');
                // Trigger submit event first
                const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
                if (form.dispatchEvent(submitEvent)) {
                    if (form.requestSubmit) {
                        form.requestSubmit();
                        return 'form_requestSubmit';
                    }
                }
            }

            return 'not_found';
        })()"""
        r = cdp("Runtime.evaluate", {"expression": js_click})
        if r:
            val = r.get("result", {}).get("result", {}).get("value", "error")
            logger.info("Click: %s", val)
        
        # Wait for redirect with better error handling
        logger.info("Waiting for login...")
        login_success = False
        final_url = ""

        for i in range(60):  # Increased from 45 to 60 seconds
            time.sleep(1)
            try:
                r = cdp("Runtime.evaluate", {"expression": "window.location.href"}, retries=1)
                if r:
                    url = r.get("result", {}).get("result", {}).get("value", "")
                    final_url = url

                    # Log every 5 seconds instead of 10
                    if i % 5 == 0:
                        logger.info("Waiting... %ds, URL: %s", i, url)

                    # Check if redirected away from login
                    if url and "login" not in url.lower():
                        logger.info("Redirected to: %s", url)
                        login_success = True
                        break

                    # Enhanced diagnostics every 10 seconds
                    if i > 10 and i % 10 == 0:
                        # Check for error messages
                        err_check = cdp("Runtime.evaluate", {
                            "expression": """(() => {
                                const text = document.body.innerText.toLowerCase();
                                const errors = ['error', 'incorrect', 'invalid', 'failed', 'wrong'];
                                return errors.some(e => text.includes(e));
                            })()"""
                        })
                        if err_check and err_check.get("result", {}).get("result", {}).get("value"):
                            logger.warning("Possible error message detected on page")

                        # Check for CAPTCHA
                        captcha_check = cdp("Runtime.evaluate", {
                            "expression": """(() => {
                                const captchaKeywords = ['captcha', 'recaptcha', 'hcaptcha', 'verify', 'robot'];
                                const html = document.body.innerHTML.toLowerCase();
                                return captchaKeywords.some(k => html.includes(k));
                            })()"""
                        })
                        if captcha_check and captcha_check.get("result", {}).get("result", {}).get("value"):
                            logger.warning("CAPTCHA detected on page - manual intervention may be required")

                        # Check if still on login page with form
                        form_check = cdp("Runtime.evaluate", {
                            "expression": "document.querySelector('form') !== null"
                        })
                        if form_check and form_check.get("result", {}).get("result", {}).get("value"):
                            logger.info("Login form still present on page")
            except Exception as e:
                logger.warning("Error checking URL at %ds: %s", i, e)
                continue

        if not login_success:
            logger.warning("Login may have failed - still on URL: %s", final_url)

            # Extract page content for debugging
            try:
                page_text = cdp("Runtime.evaluate", {
                    "expression": "document.body.innerText.substring(0, 500)"
                })
                if page_text:
                    text_content = page_text.get("result", {}).get("result", {}).get("value", "")
                    if text_content:
                        logger.info("Page text preview: %s", text_content[:200])
            except Exception as e:
                logger.warning("Failed to extract page text: %s", e)

        time.sleep(3)  # Increased wait time for token to be written
        
        # Get localStorage/sessionStorage with retry and token polling
        logger.info("Getting localStorage...")
        ls_data = {}
        ss_data = {}
        token = ""

        for attempt in range(5):  # Increased from 3 to 5 attempts
            try:
                # Try to reconnect if needed
                if attempt > 0:
                    logger.info("Retry %d: reconnecting...", attempt)
                    if not _reconnect():
                        logger.warning("Reconnect failed on attempt %d", attempt)
                        time.sleep(2)
                        continue
                    time.sleep(2)

                # First check if we can access localStorage
                access_check = cdp("Runtime.evaluate", {
                    "expression": "typeof localStorage !== 'undefined'"
                }, retries=1)

                if not access_check or not access_check.get("result", {}).get("result", {}).get("value"):
                    logger.warning("localStorage not accessible on attempt %d", attempt)
                    time.sleep(2)
                    continue

                r = cdp("Runtime.evaluate", {"expression": "JSON.stringify(localStorage)"}, retries=2)
                if r:
                    ls_str = r.get("result", {}).get("result", {}).get("value", "{}")
                    try:
                        ls_data = json.loads(ls_str)
                    except Exception as e:
                        logger.warning("Failed to parse localStorage JSON: %s", e)
                        ls_data = {}

                r = cdp("Runtime.evaluate", {"expression": "JSON.stringify(sessionStorage)"}, retries=2)
                if r:
                    ss_str = r.get("result", {}).get("result", {}).get("value", "{}")
                    try:
                        ss_data = json.loads(ss_str)
                    except Exception as e:
                        logger.warning("Failed to parse sessionStorage JSON: %s", e)
                        ss_data = {}

                if ls_data:
                    logger.info("LocalStorage keys: %s", list(ls_data.keys()))
                if ss_data:
                    logger.info("SessionStorage keys: %s", list(ss_data.keys()))

                token = _pick_token_from_storage(ls_data) or _pick_token_from_storage(ss_data)
                if token:
                    logger.info("Found token in storage")
                    break

                logger.warning("No token found yet, attempt %d", attempt)
                time.sleep(2)
            except Exception as e:
                logger.warning("Attempt %d failed: %s", attempt, e)
                time.sleep(2)
        if token:
            token_len = len(token)
            logger.info("SUCCESS! Token length: %d", token_len)
            if "account_token" not in ls_data:
                ls_data["account_token"] = token
            _atomic_write_json(LOCALSTORAGE_FILE, ls_data)
            try:
                ws.close()
            except Exception:
                pass
            return True
        logger.error("No token found in storage")
        
        ws.close()
        return False
        
    except Exception as exc:
        logger.error("CDP login failed: %s", exc)
        import traceback
        traceback.print_exc()
        return False


def refresh_if_needed(force: bool = False) -> bool:
    """
    Check token status and refresh if needed.
    Uses saved credentials from file or environment.
    
    Refresh strategy:
    - Only refresh when token is missing or force=True.
    """
    is_valid, _seconds_left, _expiry = get_token_status()
    needs_refresh = force or (not is_valid)

    if not needs_refresh:
        logger.info("Token present; skip refresh.")
        return True

    logger.info("Token missing or invalid, refreshing...")

    # Get credentials
    creds = load_credentials()
    if not creds:
        env_email = (os.getenv("VALUESCAN_EMAIL") or "").strip()
        env_password = (os.getenv("VALUESCAN_PASSWORD") or "").strip()
        if env_email and env_password:
            creds = {"email": env_email, "password": env_password}
    
    if not creds:
        logger.error("No credentials available for login")
        return False
    
    return cdp_refresh_token(creds["email"], creds["password"])


def run_cdp_refresh_loop(interval_hours: float = TOKEN_REFRESH_INTERVAL_HOURS) -> None:
    """
    Run continuous token refresh loop.
    Only refreshes when API actually rejects the token (4000/4002/401).
    No proactive expiry-based refresh.
    """
    logger.info("=" * 50)
    logger.info("Starting CDP token refresh loop (API-driven)")
    logger.info("Check interval: %.1f hours", interval_hours)
    logger.info("Login timeout: %d seconds", LOGIN_TIMEOUT_SECONDS)
    logger.info("Key levels chart days: %d, AI analysis days: %d", KEY_LEVELS_CHART_DAYS, KEY_LEVELS_AI_ANALYSIS_DAYS)
    logger.info("=" * 50)
    
    # Kill zombie browsers on startup
    _kill_zombie_browsers()
    
    while True:
        try:
            # Check if Chrome is already running by another process
            if _is_chrome_process_running() and not _is_browser_running():
                logger.info("Chrome process exists but not responding on CDP port, waiting...")
                time.sleep(60)
                continue
            
            # Check token validity by calling API (not by JWT expiry)
            is_api_valid = _check_api_token_valid()
            
            if is_api_valid:
                logger.info("Token valid (API check passed)")
                sleep_seconds = interval_hours * 3600
            else:
                logger.info("Token invalid (API rejected), refreshing...")
                
                # Kill zombie browsers before login attempt
                _kill_zombie_browsers()
                
                # Attempt login with timeout
                login_start = time.time()
                success = False
                
                try:
                    success = refresh_if_needed(force=True)
                except Exception as e:
                    logger.error("Login attempt failed: %s", e)
                
                login_duration = time.time() - login_start
                
                # If login took too long, kill zombies and retry
                if login_duration > LOGIN_TIMEOUT_SECONDS:
                    logger.warning("Login timeout (%.0fs > %ds), killing zombies and retrying...", 
                                   login_duration, LOGIN_TIMEOUT_SECONDS)
                    _kill_zombie_browsers()
                    sleep_seconds = LOGIN_RETRY_COOLDOWN_SECONDS
                elif success:
                    logger.info("Token refreshed successfully (took %.0fs)", login_duration)
                    sleep_seconds = interval_hours * 3600
                else:
                    logger.error("Token refresh failed, retrying in %d seconds", LOGIN_RETRY_COOLDOWN_SECONDS)
                    sleep_seconds = LOGIN_RETRY_COOLDOWN_SECONDS

            logger.info("Sleeping for %.0f seconds (%.1f hours)", sleep_seconds, sleep_seconds / 3600)
            time.sleep(sleep_seconds)
            
        except KeyboardInterrupt:
            logger.info("Refresh loop stopped by user")
            break
        except Exception as exc:
            logger.error("Refresh loop error: %s", exc)
            _kill_zombie_browsers()
            time.sleep(LOGIN_RETRY_COOLDOWN_SECONDS)


def main() -> None:
    import argparse
    
    parser = argparse.ArgumentParser(description="CDP-based ValueScan token refresher")
    parser.add_argument("--email", "-e", help="Login email")
    parser.add_argument("--password", "-p", help="Login password")
    parser.add_argument("--once", action="store_true", help="Refresh once and exit")
    parser.add_argument(
        "--interval", "-i",
        type=float,
        default=TOKEN_REFRESH_INTERVAL_HOURS,
        help=f"Refresh interval in hours (default: {TOKEN_REFRESH_INTERVAL_HOURS})"
    )
    parser.add_argument("--force", "-f", action="store_true", help="Force refresh even if token is valid")
    
    args = parser.parse_args()
    
    # Save credentials if provided
    if args.email and args.password:
        save_credentials(args.email, args.password)
    
    if args.once:
        success = refresh_if_needed(force=args.force)
        sys.exit(0 if success else 1)
    else:
        run_cdp_refresh_loop(args.interval)


if __name__ == "__main__":
    main()
