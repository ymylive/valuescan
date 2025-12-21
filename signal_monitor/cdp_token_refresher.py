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
import time
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
CHROME_PROFILE_DIR = BASE_DIR / "chrome-debug-profile"

# Configuration
CDP_PORT = int(os.getenv("VALUESCAN_CDP_PORT", "9222"))
TOKEN_REFRESH_INTERVAL_HOURS = float(os.getenv("VALUESCAN_TOKEN_REFRESH_INTERVAL_HOURS", "0.8"))
TOKEN_REFRESH_SAFETY_SECONDS = int(os.getenv("VALUESCAN_TOKEN_REFRESH_SAFETY_SECONDS", "300"))
LOGIN_RETRY_COOLDOWN_SECONDS = int(os.getenv("VALUESCAN_LOGIN_RETRY_COOLDOWN_SECONDS", "60"))
BROWSER_STARTUP_TIMEOUT = int(os.getenv("VALUESCAN_BROWSER_STARTUP_TIMEOUT", "30"))


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
    for key in ("account_token", "accountToken", "token", "access_token", "accessToken"):
        val = data.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return ""


def get_token_status() -> Tuple[bool, Optional[int], Optional[datetime]]:
    """
    Get current token status.
    Returns: (is_valid, seconds_remaining, expiry_datetime)
    """
    data = _load_json(LOCALSTORAGE_FILE)
    token = (data.get("account_token") or "").strip()
    if not token:
        return False, None, None
    
    seconds_left = _seconds_until_expiry(token)
    if seconds_left is None:
        return False, None, None
    
    exp = _jwt_expiry_seconds(token)
    expiry_dt = datetime.fromtimestamp(exp, tz=timezone.utc) if exp else None
    
    is_valid = seconds_left > TOKEN_REFRESH_SAFETY_SECONDS
    return is_valid, seconds_left, expiry_dt


def _find_browser_path() -> str:
    """Find Chromium/Chrome executable."""
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
        resp = requests.get(f"http://127.0.0.1:{CDP_PORT}/json", timeout=3)
        return resp.status_code == 200
    except Exception:
        return False


def _kill_browser() -> None:
    """Kill existing browser processes."""
    try:
        subprocess.run(['pkill', '-9', 'chromium'], capture_output=True, timeout=5)
        subprocess.run(['pkill', '-9', 'chrome'], capture_output=True, timeout=5)
    except Exception:
        pass
    time.sleep(2)


def _start_browser() -> bool:
    """Start headless browser with CDP enabled."""
    browser_path = _find_browser_path()
    if not browser_path:
        logger.error("Browser executable not found")
        return False
    
    CHROME_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    
    cmd = [
        browser_path,
        "--headless=new",
        f"--remote-debugging-port={CDP_PORT}",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        f"--user-data-dir={CHROME_PROFILE_DIR}",
        "--remote-allow-origins=*",
    ]
    
    try:
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        logger.info("Browser started")
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
        def _fetch_targets() -> list:
            try:
                resp = requests.get(f"http://127.0.0.1:{CDP_PORT}/json", timeout=10)
                data = resp.json()
                return data if isinstance(data, list) else []
            except Exception as exc:
                logger.warning("Failed to fetch CDP targets: %s", exc)
                return []

        def _select_page_target(targets: list) -> Optional[Dict[str, Any]]:
            pages = [t for t in targets if t.get("type") == "page"]
            if not pages:
                return None
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
                ws = websocket.create_connection(ws_url, timeout=30)
                ws.settimeout(15)
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

                deadline = time.time() + 20
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
            _wait_for_dom_ready(timeout_seconds=40)
            time.sleep(2)
        
        # Check if already logged in (redirected)
        r = cdp("Runtime.evaluate", {"expression": "window.location.href"})
        if r:
            url = r.get("result", {}).get("result", {}).get("value", "")
            logger.info("Current URL: %s", url)
            if url and "login" not in url.lower():
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
                    seconds_left = _seconds_until_expiry(token) if token else None
                    if seconds_left is None or seconds_left <= TOKEN_REFRESH_SAFETY_SECONDS:
                        logger.info("Existing token expiring/expired; continuing login.")
                    else:
                        if "account_token" not in ls_data:
                            ls_data["account_token"] = token
                        _atomic_write_json(LOCALSTORAGE_FILE, ls_data)
                        logger.info("Token extracted from existing session")
                        ws.close()
                        return True
        
        # Fill email
        logger.info("Filling email...")
        _wait_for_dom_ready(timeout_seconds=20)
        email_json = json.dumps(email or "")
        js_email = f"""(() => {{
            const EMAIL = {email_json};
            const norm = (s) => String(s || '').toLowerCase().replace(/\\s+/g, ' ').trim();
            const inputs = Array.from(document.querySelectorAll('input, textarea'));
            const candidates = inputs.filter((i) => {{
                const t = norm(i.type);
                const n = norm(i.name);
                const ph = norm(i.placeholder);
                const ac = norm(i.autocomplete);
                return t === 'email' || ph.includes('email') || ph.includes('mail') ||
                    n.includes('email') || n.includes('account') || n.includes('user') ||
                    ac.includes('username');
            }});
            const target = candidates[0] || inputs[0];
            if (target) {{
                target.focus();
                target.value = EMAIL;
                target.dispatchEvent(new Event('input', {{ bubbles: true }}));
                target.dispatchEvent(new Event('change', {{ bubbles: true }}));
                return 'ok';
            }}
            return 'not_found';
        }})()"""
        r = cdp("Runtime.evaluate", {"expression": js_email})
        if r:
            val = r.get("result", {}).get("result", {}).get("value", "error")
            logger.info("Email: %s", val)
        
        time.sleep(0.5)
        
        # Fill password
        logger.info("Filling password...")
        password_json = json.dumps(password or "")
        js_pwd = f"""(() => {{
            const PASSWORD = {password_json};
            const p = document.querySelector('input[type=\"password\"]');
            if (p) {{
                p.focus();
                p.value = PASSWORD;
                p.dispatchEvent(new Event('input', {{ bubbles: true }}));
                p.dispatchEvent(new Event('change', {{ bubbles: true }}));
                return 'ok';
            }}
            return 'not_found';
        }})()"""
        r = cdp("Runtime.evaluate", {"expression": js_pwd})
        if r:
            val = r.get("result", {}).get("result", {}).get("value", "error")
            logger.info("Password: %s", val)
        
        time.sleep(0.5)
        
        # Click login
        logger.info("Clicking login...")
        js_click = """(() => {
            const labels = ['login', 'log in', 'sign in', 'continue'];
            const buttons = Array.from(document.querySelectorAll('button, [role=\"button\"], input[type=\"submit\"], input[type=\"button\"]'));
            for (const btn of buttons) {
                const raw = (btn.textContent || btn.value || btn.getAttribute('aria-label') || '').toLowerCase();
                if (labels.some((l) => raw.includes(l))) {
                    btn.click();
                    return 'clicked';
                }
                const type = (btn.getAttribute('type') || '').toLowerCase();
                if (type === 'submit') {
                    btn.click();
                    return 'clicked';
                }
            }
            const form = document.querySelector('form');
            if (form) {
                if (form.requestSubmit) { form.requestSubmit(); return 'form_submit'; }
                if (form.submit) { form.submit(); return 'form_submit'; }
            }
            return 'not_found';
        })()"""
        r = cdp("Runtime.evaluate", {"expression": js_click})
        if r:
            val = r.get("result", {}).get("result", {}).get("value", "error")
            logger.info("Click: %s", val)
        
        # Wait for redirect
        logger.info("Waiting for login...")
        for i in range(45):
            time.sleep(1)
            r = cdp("Runtime.evaluate", {"expression": "window.location.href"})
            if r:
                url = r.get("result", {}).get("result", {}).get("value", "")
                if i % 10 == 0:
                    logger.info("Waiting... %ds, URL: %s", i, url)
                if url and "login" not in url.lower():
                    logger.info("Redirected to: %s", url)
                    break
        
        time.sleep(3)
        
        # Get localStorage/sessionStorage
        logger.info("Getting localStorage...")
        r = cdp("Runtime.evaluate", {"expression": "JSON.stringify(localStorage)"})
        ls_data = {}
        if r:
            ls_str = r.get("result", {}).get("result", {}).get("value", "{}")
            try:
                ls_data = json.loads(ls_str)
            except Exception:
                ls_data = {}
        logger.info("LocalStorage keys: %s", list(ls_data.keys()))

        r = cdp("Runtime.evaluate", {"expression": "JSON.stringify(sessionStorage)"})
        ss_data = {}
        if r:
            ss_str = r.get("result", {}).get("result", {}).get("value", "{}")
            try:
                ss_data = json.loads(ss_str)
            except Exception:
                ss_data = {}
        if ss_data:
            logger.info("SessionStorage keys: %s", list(ss_data.keys()))

        token = _pick_token_from_storage(ls_data) or _pick_token_from_storage(ss_data)
        if token:
            token_len = len(token)
            logger.info("SUCCESS! Token length: %d", token_len)
            if "account_token" not in ls_data:
                ls_data["account_token"] = token
            _atomic_write_json(LOCALSTORAGE_FILE, ls_data)
            ws.close()
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
    """
    is_valid, seconds_left, expiry = get_token_status()
    
    if is_valid and not force:
        logger.info("Token valid, expires in %.1f hours", (seconds_left or 0) / 3600)
        return True
    
    if seconds_left is not None:
        logger.info("Token expiring in %d seconds, refreshing...", seconds_left)
    else:
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
    Checks token status and refreshes when needed.
    """
    logger.info("=" * 50)
    logger.info("Starting CDP token refresh loop")
    logger.info("Refresh interval: %.1f hours", interval_hours)
    logger.info("Safety buffer: %d seconds", TOKEN_REFRESH_SAFETY_SECONDS)
    logger.info("=" * 50)
    
    while True:
        try:
            is_valid, seconds_left, expiry = get_token_status()
            
            if is_valid:
                logger.info("Token valid until %s", expiry.isoformat() if expiry else "unknown")
                # Calculate sleep time
                sleep_seconds = interval_hours * 3600
                if seconds_left is not None:
                    # Sleep until safety buffer, but not longer than interval
                    sleep_seconds = min(
                        sleep_seconds,
                        max(60, seconds_left - TOKEN_REFRESH_SAFETY_SECONDS)
                    )
            else:
                # Token invalid, try to refresh
                logger.info("Token invalid or expiring, refreshing...")
                success = refresh_if_needed(force=True)
                
                if success:
                    _, seconds_left, expiry = get_token_status()
                    logger.info("Token refreshed, valid until %s", expiry.isoformat() if expiry else "unknown")
                    sleep_seconds = interval_hours * 3600
                    if seconds_left is not None:
                        sleep_seconds = min(
                            sleep_seconds,
                            max(60, seconds_left - TOKEN_REFRESH_SAFETY_SECONDS)
                        )
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
