#!/usr/bin/env python3
"""
ValueScan token refresher driven by a Chromium engine (DrissionPage).

Responsibilities:
- Sign in with the ValueScan web UI (Chromium) and capture account/refresh tokens.
- Persist localStorage/sessionStorage/cookies to json files used by the signal monitor.
- Detect near‑expiry or invalid tokens and perform an automatic browser re-login.

This module is imported by the API server and the polling monitor, so keep functions
lightweight and side-effect free unless explicitly performing a login.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
COOKIES_FILE = Path(os.getenv("VALUESCAN_COOKIES_FILE") or BASE_DIR / "valuescan_cookies.json")
SESSIONSTORAGE_FILE = Path(os.getenv("VALUESCAN_SESSIONSTORAGE_FILE") or BASE_DIR / "valuescan_sessionstorage.json")
CREDENTIALS_FILE = BASE_DIR / "valuescan_credentials.json"

# Timing knobs (seconds)
TOKEN_REFRESH_INTERVAL_HOURS = float(os.getenv("VALUESCAN_TOKEN_REFRESH_INTERVAL_HOURS", "0.8"))
TOKEN_REFRESH_SAFETY_SECONDS = int(os.getenv("VALUESCAN_TOKEN_REFRESH_SAFETY_SECONDS", "300"))
LOGIN_RETRY_COOLDOWN_SECONDS = int(os.getenv("VALUESCAN_LOGIN_RETRY_COOLDOWN_SECONDS", "60"))
LOGIN_LOCK_TIMEOUT_SECONDS = int(os.getenv("VALUESCAN_LOGIN_LOCK_TIMEOUT_SECONDS", "180"))
LOGIN_LOCK_STALE_SECONDS = int(os.getenv("VALUESCAN_LOGIN_LOCK_STALE_SECONDS", "1200"))

LOGIN_METHOD_RAW = os.getenv("VALUESCAN_LOGIN_METHOD", "auto")

REFRESH_WINDOW_START_HOUR = int(os.getenv("VALUESCAN_REFRESH_WINDOW_START", "0"))
REFRESH_WINDOW_END_HOUR = int(os.getenv("VALUESCAN_REFRESH_WINDOW_END", "6"))
REFRESH_URGENT_THRESHOLD_SECONDS = int(os.getenv("VALUESCAN_REFRESH_URGENT_THRESHOLD", "1800"))


def _is_refresh_window() -> bool:
    """Check if current time is within the preferred refresh window (default: 0:00-6:00)."""
    now = datetime.now()
    hour = now.hour
    if REFRESH_WINDOW_START_HOUR <= REFRESH_WINDOW_END_HOUR:
        return REFRESH_WINDOW_START_HOUR <= hour < REFRESH_WINDOW_END_HOUR
    else:
        return hour >= REFRESH_WINDOW_START_HOUR or hour < REFRESH_WINDOW_END_HOUR


def _resolve_bool_env(name: str, default: Optional[bool] = None) -> Optional[bool]:
    raw = os.getenv(name)
    if raw is None:
        return default
    value = raw.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    return default


def _resolve_headless(default: bool) -> bool:
    override = _resolve_bool_env("VALUESCAN_LOGIN_HEADLESS")
    return override if override is not None else default


def _resolve_profile_dir() -> Tuple[str, str]:
    env_path = (os.getenv("VALUESCAN_LOGIN_PROFILE_DIR") or "").strip()
    if env_path:
        return env_path, "env"
    shared_path = BASE_DIR / "chrome-debug-profile"
    if shared_path.exists():
        return str(shared_path), "shared"
    return os.path.join(tempfile.gettempdir(), "valuescan_login_profile"), "temp"


def _login_lock_path() -> Path:
    env_path = (os.getenv("VALUESCAN_LOGIN_LOCK_FILE") or "").strip()
    if env_path:
        return Path(env_path)
    return Path(tempfile.gettempdir()) / "valuescan_login_refresh.lock"


@contextmanager
def _login_lock(timeout_seconds: int = LOGIN_LOCK_TIMEOUT_SECONDS):
    """
    Cross-process lock to prevent concurrent Chromium logins.
    This avoids multiple services overlapping browser sessions.
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
                    lock_path.unlink(missing_ok=True)  # Python 3.8+
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
            # Best-effort stale lock cleanup
            try:
                age = time.time() - lock_path.stat().st_mtime
                if age > LOGIN_LOCK_STALE_SECONDS:
                    lock_path.unlink()
                    continue
            except Exception:
                pass

            if time.time() >= deadline:
                yield False
                return
            time.sleep(0.5)
        except Exception:
            yield False
            return


def _atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    """Atomic write to avoid half-written JSON when multiple processes touch the file."""
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


def _load_env_credentials() -> Optional[Dict[str, str]]:
    email = (os.getenv("VALUESCAN_EMAIL") or "").strip()
    password = (os.getenv("VALUESCAN_PASSWORD") or "").strip()
    if email and password:
        return {"email": email, "password": password}
    return None


def save_credentials(email: str, password: str) -> bool:
    """Persist login credentials (plaintext; ensure file perms are restrictive)."""
    try:
        _atomic_write_json(CREDENTIALS_FILE, {"email": email, "password": password})
        try:
            os.chmod(CREDENTIALS_FILE, 0o600)
        except Exception:
            # Best-effort on platforms that support chmod
            pass
        logger.info("Login credentials saved locally for auto-refresh.")
        return True
    except Exception as exc:
        logger.error("Failed to save credentials: %s", exc)
        return False


def _b64url_decode(segment: str) -> bytes:
    seg = (segment or "").strip()
    if not seg:
        return b""
    pad = "=" * (-len(seg) % 4)
    return base64.urlsafe_b64decode((seg + pad).encode("ascii", errors="ignore"))


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


def _load_localstorage(retries: int = 3, delay: float = 0.2) -> Dict[str, Any]:
    for attempt in range(max(1, retries)):
        try:
            return _load_json(LOCALSTORAGE_FILE)
        except json.JSONDecodeError as exc:
            if attempt < retries - 1:
                time.sleep(delay)
                continue
            logger.warning("Token JSON corrupted: %s", exc)
            return {}
        except Exception as exc:
            if attempt < retries - 1:
                time.sleep(delay)
                continue
            logger.warning("Failed to load token file: %s", exc)
            return {}
    return {}


def _persist_localstorage(data: Dict[str, Any]) -> bool:
    try:
        _atomic_write_json(LOCALSTORAGE_FILE, data)
        return True
    except Exception as exc:
        logger.error("Failed to persist token file: %s", exc)
        return False


def _pick_browser_path() -> str:
    """
    Resolve a Chromium/Chrome executable. Respects env VALUESCAN_BROWSER_PATH if set.
    """
    env_path = (os.getenv("VALUESCAN_BROWSER_PATH") or "").strip()
    if env_path:
        return env_path

    candidates = [
        "/usr/bin/chromium-browser",
        "/usr/bin/chromium",
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/snap/bin/chromium",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return ""


def _apply_browser_stealth_options(options: Any) -> None:
    ua = (
        os.getenv("VALUESCAN_LOGIN_USER_AGENT")
        or os.getenv("VALUESCAN_BROWSER_USER_AGENT")
        or ""
    ).strip()
    if not ua:
        ua = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    for arg in (
        f"--user-agent={ua}",
        "--lang=en-US,en",
        "--disable-blink-features=AutomationControlled",
    ):
        try:
            options.set_argument(arg)
        except Exception:
            pass


def _get_login_urls() -> List[str]:
    env_urls = (os.getenv("VALUESCAN_LOGIN_URLS") or "").strip()
    if env_urls:
        urls = [u.strip() for u in env_urls.split(",") if u.strip()]
        if urls:
            return urls
    env_url = (os.getenv("VALUESCAN_LOGIN_URL") or "").strip()
    if env_url:
        return [env_url]
    return [
        "https://www.valuescan.io/login",
        "https://www.valuescan.io/#/login",
    ]


def _normalize_login_method(value: str) -> str:
    raw = (value or "").strip().lower()
    if raw in {"api", "http", "http_api", "http-api", "httpapi"}:
        return "api"
    if raw in {"browser", "chromium", "ui", "drission"}:
        return "browser"
    if raw in {"cdp", "devtools", "cdp_browser"}:
        return "cdp"
    return "auto"


def _http_login_allowed() -> bool:
    return not _resolve_bool_env("VALUESCAN_DISABLE_HTTP_LOGIN", False)


def _run_http_api_login(email: str, password: str, timeout_seconds: int = 90) -> bool:
    """Attempt ValueScan login using the HTTP API helper script."""
    script = BASE_DIR / "http_api_login.py"
    if not script.exists():
        logger.warning("HTTP login script missing: %s", script)
        return False

    python_bin = sys.executable or "python3"
    env = dict(os.environ)
    env.setdefault("VALUESCAN_LOGIN_OUT_DIR", str(BASE_DIR))
    env.setdefault("VALUESCAN_TOKEN_FILE", str(LOCALSTORAGE_FILE))
    env.setdefault("VALUESCAN_COOKIES_FILE", str(COOKIES_FILE))
    env.setdefault("VALUESCAN_SESSION_FILE", str(SESSIONSTORAGE_FILE))
    env["VALUESCAN_EMAIL"] = email
    env["VALUESCAN_PASSWORD"] = password

    try:
        res = subprocess.run(
            [python_bin, str(script)],
            cwd=str(BASE_DIR),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except Exception as exc:
        logger.warning("HTTP login failed to run: %s", exc)
        return False

    if res.returncode != 0:
        msg = (res.stderr or res.stdout or "").strip()
        if msg:
            logger.warning("HTTP login failed: %s", msg[-200:])
        return False

    data = _load_localstorage(retries=3)
    if (data.get("account_token") or "").strip():
        logger.info("Token refreshed successfully via HTTP login.")
        return True

    msg = (res.stderr or res.stdout or "").strip()
    if msg:
        logger.warning("HTTP login completed but no account_token found: %s", msg[-200:])
    return False


def _run_cdp_login(email: str, password: str) -> bool:
    try:
        from cdp_token_refresher import cdp_refresh_token
    except Exception as exc:
        logger.warning("CDP login unavailable: %s", exc)
        return False
    try:
        return bool(cdp_refresh_token(email, password))
    except Exception as exc:
        logger.warning("CDP login failed: %s", exc)
        return False


def get_token_expiry() -> Optional[datetime]:
    """Parse `account_token` expiry from the local storage file."""
    data = _load_localstorage()
    token = (data.get("account_token") or "").strip()
    exp = _jwt_expiry_seconds(token)
    if exp:
        return datetime.fromtimestamp(exp, tz=timezone.utc)
    return None


def is_token_valid(buffer_seconds: int = TOKEN_REFRESH_SAFETY_SECONDS) -> bool:
    """
    Return True when a non-empty account_token exists.
    """
    data = _load_localstorage()
    token = (data.get("account_token") or "").strip()
    return bool(token)


def _extract_storage(page, storage_name: str) -> Dict[str, str]:
    """
    Convert localStorage/sessionStorage into a plain dict.
    """
    try:
        js = f"""
        (() => {{
            const store = {storage_name};
            const out = {{}};
            for (let i = 0; i < store.length; i++) {{
                const key = store.key(i);
                out[key] = store.getItem(key);
            }}
            return JSON.stringify(out);
        }})()
        """
        raw = page.run_js(js, as_expr=True)
        if isinstance(raw, str) and raw.strip():
            return json.loads(raw)
    except Exception:
        return {}
    return {}


def _get_storage_item(page, key: str) -> Optional[str]:
    try:
        expr = f"localStorage.getItem({json.dumps(key)})"
        val = page.run_js(expr, as_expr=True)
        if isinstance(val, str) and val.strip():
            return val.strip()
    except Exception:
        return None
    return None


def _persist_existing_token_from_page(page) -> bool:
    pre_ls = _extract_storage(page, "localStorage")
    pre_token = (pre_ls.get("account_token") or _get_storage_item(page, "account_token") or "").strip()
    if pre_token:
        logger.info("Existing account_token found in browser profile; persisting without relogin.")
        token_payload = dict(pre_ls)
        token_payload["account_token"] = pre_token
        token_payload.setdefault("language", "en-US")
        _atomic_write_json(LOCALSTORAGE_FILE, token_payload)
        _atomic_write_json(SESSIONSTORAGE_FILE, _extract_storage(page, "sessionStorage"))
        try:
            _atomic_write_json(COOKIES_FILE, page.cookies() or [])
        except Exception:
            _atomic_write_json(COOKIES_FILE, [])
        return True
    return False


def _cleanup_stale_browsers() -> None:
    """Kill any stale chromium processes that might block new browser instances."""
    if os.getenv("VALUESCAN_KILL_STALE_BROWSERS", "0").strip() != "1":
        return
    try:
        subprocess.run(["pkill", "-9", "chromium"], capture_output=True, timeout=5)
        subprocess.run(["pkill", "-9", "chrome"], capture_output=True, timeout=5)
    except Exception:
        pass


def _safe_page_title(page) -> str:
    try:
        title = getattr(page, "title", None)
        if callable(title):
            title = title()
        if isinstance(title, str):
            return title.strip()
    except Exception:
        pass
    try:
        raw = page.run_js("document.title", as_expr=True)
        if isinstance(raw, str):
            return raw.strip()
    except Exception:
        pass
    return ""


def _count_login_inputs(page) -> int:
    js = """
    (() => {
      const roots = [];
      const seen = new Set();
      const pushRoot = (root) => {
        if (root && !seen.has(root)) {
          seen.add(root);
          roots.push(root);
        }
      };
      pushRoot(document);
      try {
        const iframes = Array.from(document.querySelectorAll('iframe'));
        for (const f of iframes) {
          try { pushRoot(f.contentDocument); } catch (e) {}
        }
      } catch (e) {}
      let count = 0;
      while (roots.length) {
        const root = roots.pop();
        try {
          const inputs = root.querySelectorAll ? root.querySelectorAll('input, textarea') : [];
          count += inputs.length;
          const nodes = root.querySelectorAll ? root.querySelectorAll('*') : [];
          for (const n of nodes) {
            try {
              if (n.shadowRoot) {
                pushRoot(n.shadowRoot);
              }
            } catch (e) {}
          }
        } catch (e) {}
      }
      return count;
    })()
    """
    try:
        raw = page.run_js(js, as_expr=True)
        return int(raw or 0)
    except Exception:
        return 0


def _wait_for_dom_inputs(page, timeout_seconds: int = 40) -> bool:
    """Wait for the SPA to render at least one input element."""
    deadline = time.time() + max(1, int(timeout_seconds))
    while time.time() < deadline:
        try:
            ready = page.run_js("document.readyState", as_expr=True)
        except Exception:
            ready = ""
        if not ready or (isinstance(ready, str) and ready.lower() in ("interactive", "complete")):
            if _count_login_inputs(page) >= 1:
                return True
        time.sleep(1)
    return False


def _detect_login_block_reason(page) -> str:
    try:
        text = page.run_js("document.body ? document.body.innerText : ''", as_expr=True)
    except Exception:
        return ""
    if not isinstance(text, str):
        return ""
    low = text.lower()
    if "cloudflare" in low or "just a moment" in low or "checking your browser" in low:
        return "cloudflare_or_bot_check"
    if "access denied" in low or "forbidden" in low or "blocked" in low:
        return "access_denied"
    if "enable javascript" in low or "javascript is required" in low:
        return "javascript_required"
    return ""


def _try_login_via_js(page, email: str, password: str) -> Dict[str, Any]:
    """
    Best-effort login using JS to reliably trigger React/Vue input handlers.
    Returns a small diagnostics dict (safe for logs).
    """
    email_js = json.dumps(email or "")
    password_js = json.dumps(password or "")
    js = f"""
    (() => {{
      const EMAIL = {email_js};
      const PASSWORD = {password_js};

      const norm = (s) => String(s || '').toLowerCase().replace(/\\s+/g, ' ').trim();
      const visible = (el) => {{
        try {{
          const r = el.getBoundingClientRect();
          return !!(r && r.width > 0 && r.height > 0);
        }} catch (e) {{
          return true;
        }}
      }};
      const setValue = (el, value) => {{
        try {{
          el.focus();
          const proto = el.tagName === 'TEXTAREA'
            ? window.HTMLTextAreaElement.prototype
            : window.HTMLInputElement.prototype;
          const desc = Object.getOwnPropertyDescriptor(proto, 'value');
          if (desc && desc.set) {{
            desc.set.call(el, value);
          }} else {{
            el.value = value;
          }}
          el.dispatchEvent(new Event('input', {{ bubbles: true }}));
          el.dispatchEvent(new Event('change', {{ bubbles: true }}));
        }} catch (e) {{
          try {{ el.value = value; }} catch (_) {{}}
        }}
      }};

      const result = {{
        email_filled: false,
        password_filled: false,
        clicked: false,
        url: String(location.href || ''),
        title: String(document.title || ''),
        reason: '',
        input_count: 0,
        button_count: 0
      }};

      const rootDocs = [document];
      try {{
        const iframes = Array.from(document.querySelectorAll('iframe'));
        for (const f of iframes) {{
          try {{
            const d = f.contentDocument;
            if (d) rootDocs.push(d);
          }} catch (e) {{}}
        }}
      }} catch (e) {{}}

      const allInputs = [];
      for (const d of rootDocs) {{
        try {{
          for (const el of Array.from(d.querySelectorAll('input, textarea'))) allInputs.push(el);
        }} catch (e) {{}}
      }}
      result.input_count = allInputs.length;

      const inputs = allInputs.filter((i) => i && !i.disabled);
      const emailCandidates = inputs.filter((i) => {{
        const t = norm(i.type);
        const ph = norm(i.placeholder);
        const nm = norm(i.name);
        const ac = norm(i.autocomplete);
        return (
          t === 'email' ||
          ac === 'email' ||
          nm.includes('email') ||
          ph.includes('email') ||
          ph.includes('mail') ||
          ph.includes('邮箱') ||
          ph.includes('账号')
        );
      }});
      const emailInput =
        emailCandidates.find((i) => visible(i)) ||
        emailCandidates[0] ||
        inputs.find((i) => visible(i) && (norm(i.type) === 'text' || norm(i.type) === '')) ||
        inputs[0] ||
        null;

      const passwordInput =
        inputs.find((i) => norm(i.type) === 'password' && visible(i)) ||
        inputs.find((i) => norm(i.type) === 'password') ||
        null;

      if (emailInput) {{
        setValue(emailInput, EMAIL);
        result.email_filled = true;
      }}
      if (passwordInput) {{
        setValue(passwordInput, PASSWORD);
        result.password_filled = true;
      }}

      const allButtons = [];
      for (const d of rootDocs) {{
        try {{
          for (const el of Array.from(d.querySelectorAll('button, [role=\"button\"], input[type=\"submit\"], a'))) {{
            allButtons.push(el);
          }}
        }} catch (e) {{}}
      }}
      result.button_count = allButtons.length;

      const btnText = (b) => norm(b.textContent || b.value || b.getAttribute('aria-label') || '');
      const isSubmit = (b) => norm(b.getAttribute && b.getAttribute('type')) === 'submit';

      const candidates = [];
      for (const b of allButtons) {{
        const t = btnText(b);
        if (!t) continue;
        if (
          t.includes('login') ||
          t.includes('log in') ||
          t.includes('sign in') ||
          t.includes('continue') ||
          t.includes('登录') ||
          t.includes('登 录') ||
          t.includes('登錄') ||
          t.includes('登入')
        ) {{
          candidates.push(b);
        }}
      }}
      let loginBtn = candidates.find((b) => visible(b)) || candidates[0] || null;
      if (!loginBtn) {{
        loginBtn =
          allButtons.find((b) => isSubmit(b) && visible(b)) ||
          allButtons.find((b) => isSubmit(b)) ||
          null;
      }}

      if (!loginBtn) {{
        // As a fallback, try to submit the form that contains the password input.
        try {{
          const form = (passwordInput && passwordInput.closest) ? passwordInput.closest('form') : null;
          if (form) {{
            if (form.requestSubmit) {{
              form.requestSubmit();
            }} else if (form.submit) {{
              form.submit();
            }}
            result.clicked = true;
            result.reason = 'form_submit_fallback';
            return JSON.stringify(result);
          }}
        }} catch (e) {{}}
        result.reason = 'login_button_not_found';
        return JSON.stringify(result);
      }}

      try {{ loginBtn.scrollIntoView({{ block: 'center', inline: 'center' }}); }} catch (e) {{}}
      try {{ loginBtn.click(); result.clicked = true; }} catch (e) {{
        try {{ loginBtn.dispatchEvent(new MouseEvent('click', {{ bubbles: true }})); result.clicked = true; }} catch (e2) {{}}
      }}
      if (!result.clicked) result.reason = 'login_click_failed';
      return JSON.stringify(result);
    }})()
    """
    try:
        raw = page.run_js(js, as_expr=True)
        if isinstance(raw, str) and raw.strip().startswith("{"):
            return json.loads(raw)
    except Exception as exc:
        return {"reason": f"js_error:{exc}"}
    return {"reason": "js_return_unexpected"}


def _dump_login_debug(page, reason: str) -> Optional[Path]:
    """Persist a small debug report when the login page changes/breaks."""
    try:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out_dir = BASE_DIR / "login_debug"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"login_debug_{ts}.json"

        report: Dict[str, Any] = {
            "reason": (reason or "").strip(),
            "url": str(getattr(page, "url", "") or ""),
            "title": _safe_page_title(page),
        }
        try:
            report["ready_state"] = page.run_js("document.readyState", as_expr=True)
        except Exception:
            report["ready_state"] = ""
        try:
            report["inputs"] = page.run_js(
                "Array.from(document.querySelectorAll('input')).map(i => ({type:i.type, name:i.name, placeholder:i.placeholder})).slice(0, 10)",
                as_expr=True,
            )
        except Exception:
            report["inputs"] = []
        try:
            report["buttons"] = page.run_js(
                "Array.from(document.querySelectorAll('button, [role=\"button\"], input[type=\"submit\"], a')).map(b => (b.textContent || b.value || b.getAttribute('aria-label') || '')).slice(0, 15)",
                as_expr=True,
            )
        except Exception:
            report["buttons"] = []

        out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return out_path
    except Exception:
        return None


def login_and_refresh_token(email: str, password: str, headless: bool = True) -> bool:
    """
    Use DrissionPage to login via Chromium and save fresh tokens.
    """
    try:
        from DrissionPage import ChromiumOptions, ChromiumPage
    except ImportError:
        logger.error("DrissionPage is not installed. Install with: pip install DrissionPage")
        return False

    with _login_lock() as acquired:
        if not acquired:
            logger.warning("Login lock is held by another process; skipping this refresh attempt.")
            return False

        # Optional cleanup (disabled by default)
        _cleanup_stale_browsers()

        login_method = _normalize_login_method(LOGIN_METHOD_RAW)
        if login_method == "cdp":
            logger.info("Attempting CDP login (method=cdp)...")
            if _run_cdp_login(email, password):
                return True
            logger.error("CDP login failed and other methods are disabled.")
            return False

        http_attempted = False
        if login_method in {"auto", "api"} and _http_login_allowed():
            logger.info("Attempting HTTP API login (method=%s)...", login_method)
            http_attempted = True
            if _run_http_api_login(email, password):
                return True
            if login_method == "api":
                logger.error("HTTP API login failed and browser login is disabled.")
                return False
        elif login_method == "api":
            logger.error("HTTP API login is disabled via VALUESCAN_DISABLE_HTTP_LOGIN.")
            return False

        headless = _resolve_headless(headless)
        logger.info("Launching Chromium for ValueScan login (headless=%s)...", headless)

        options = ChromiumOptions()
        try:
            options.headless(headless)
        except Exception:
            if headless:
                options.set_argument("--headless", "new")
        options.set_argument("--no-sandbox")
        options.set_argument("--disable-dev-shm-usage")
        options.set_argument("--disable-gpu")
        options.set_argument("--disable-software-rasterizer")
        options.set_argument("--window-size", "1920,1080")
        options.set_argument("--remote-allow-origins=*")
        _apply_browser_stealth_options(options)

        # Dedicated user data dir to avoid clobbering an interactive session
        profile_dir, profile_source = _resolve_profile_dir()
        try:
            Path(profile_dir).mkdir(parents=True, exist_ok=True)
            options.set_user_data_path(profile_dir)
            logger.info("Using Chromium profile dir: %s (source=%s)", profile_dir, profile_source)
        except Exception as exc:
            logger.warning("Failed to set profile dir (%s): %s", profile_dir, exc)

        browser_path = _pick_browser_path()
        if browser_path:
            try:
                options.set_browser_path(browser_path)
                logger.info("Using browser executable: %s", browser_path)
            except Exception as exc:
                logger.warning("Failed to set browser path (%s): %s", browser_path, exc)

        page = None
        try:
            try:
                page = ChromiumPage(addr_or_opts=options)
            except Exception as exc:
                logger.error("Failed to start Chromium session: %s", exc)
                if profile_source != "env":
                    _cleanup_stale_browsers()
                    fallback_dir = os.path.join(
                        tempfile.gettempdir(),
                        f"valuescan_login_profile_{int(time.time())}",
                    )
                    try:
                        Path(fallback_dir).mkdir(parents=True, exist_ok=True)
                        options.set_user_data_path(fallback_dir)
                        logger.warning("Retrying with fresh profile dir: %s", fallback_dir)
                        page = ChromiumPage(addr_or_opts=options)
                    except Exception as retry_exc:
                        logger.error("Chromium retry failed: %s", retry_exc)
                if page is None:
                    if _resolve_bool_env("VALUESCAN_LOGIN_CDP_FALLBACK", True):
                        if _run_cdp_login(email, password):
                            return True
                    return False

            login_urls = _get_login_urls()
            login_ready = False
            for idx, login_url in enumerate(login_urls):
                try:
                    page.get(login_url)
                except Exception as exc:
                    logger.warning("Failed to open login URL %s: %s", login_url, exc)
                    continue
                time.sleep(4 if idx == 0 else 2)

                if _persist_existing_token_from_page(page):
                    return True

                wait_timeout = 45 if idx == 0 else 25
                if _wait_for_dom_inputs(page, timeout_seconds=wait_timeout):
                    login_ready = True
                    break

                reason = _detect_login_block_reason(page)
                debug_reason = reason or f"no_inputs_rendered:{login_url}"
                debug_path = _dump_login_debug(page, debug_reason)
                if debug_path:
                    logger.warning("Login inputs not found at %s; debug saved to %s", login_url, debug_path)
                else:
                    logger.warning("Login inputs not found at %s", login_url)

            if not login_ready:
                if not http_attempted and _http_login_allowed():
                    logger.warning(
                        "Login page did not render inputs; attempting HTTP API login fallback."
                    )
                    if _run_http_api_login(email, password):
                        return True
                logger.error("Login page did not render inputs.")
                return False

            # Prefer JS-driven login (more robust when text is wrapped in spans, etc.)
            js_result = _try_login_via_js(page, email, password)
            submitted = False
            if js_result.get("clicked"):
                logger.info(
                    "Login submitted via JS (inputs=%s buttons=%s title=%s reason=%s)",
                    js_result.get("input_count"),
                    js_result.get("button_count"),
                    (js_result.get("title") or "").strip(),
                    js_result.get("reason"),
                )
                if js_result.get("reason") == "form_submit_fallback":
                    submitted = True
                elif js_result.get("email_filled") and js_result.get("password_filled"):
                    submitted = True
                else:
                    logger.warning(
                        "JS clicked but did not fill inputs (email_filled=%s password_filled=%s); falling back to selectors.",
                        js_result.get("email_filled"),
                        js_result.get("password_filled"),
                    )
            else:
                logger.warning(
                    "JS login attempt did not click (reason=%s); falling back to selectors.",
                    js_result.get("reason"),
                )

            if not submitted:
                email_selectors = [
                    # ValueScan uses type="text" with placeholder, so check placeholder first
                    'css:input[placeholder*="email" i]',
                    'css:input[placeholder*="邮箱"]',
                    'css:input[placeholder*="账号"]',
                    'xpath://input[contains(@placeholder, "mail")]',
                    'xpath://input[@type="email"]',
                    'css:input[type="email"]',
                ]
                email_input = None
                for selector in email_selectors:
                    try:
                        email_input = page.ele(selector, timeout=5)
                        if email_input:
                            logger.info(f"Email input found with selector: {selector}")
                            break
                    except Exception:
                        continue
                if not email_input:
                    # Fallback: pick the first text-like input
                    try:
                        inputs = page.eles("css:input", timeout=5) or []
                        for ele in inputs:
                            t = (ele.attr("type") or "").lower()
                            if t in ("email", "text", ""):
                                email_input = ele
                                logger.info("Email input found via fallback selector.")
                                break
                    except Exception:
                        pass
                if not email_input:
                    logger.error("Email input not found on login page.")
                    debug_path = _dump_login_debug(page, "email_input_not_found")
                    if debug_path:
                        logger.error("Login debug saved to %s", debug_path)
                    return False
                email_input.clear()
                email_input.input(email)

                # Small delay after email input to ensure page is ready
                time.sleep(1)

                pwd_input = page.ele('css:input[type="password"]', timeout=8)
                if pwd_input:
                    logger.info('Password input found with selector: css:input[type="password"]')
                else:
                    pwd_input = page.ele('xpath://input[@type="password"]', timeout=5)
                    if pwd_input:
                        logger.info('Password input found with selector: xpath://input[@type="password"]')
                if not pwd_input:
                    pwd_input = page.ele('xpath://input[contains(@placeholder, "password")]', timeout=5)
                    if pwd_input:
                        logger.info("Password input found with selector: xpath placeholder")
                if not pwd_input:
                    try:
                        inputs = page.eles("css:input", timeout=5) or []
                        pwd_input = inputs[1] if len(inputs) > 1 else None
                        if pwd_input:
                            logger.info("Password input found via fallback selector (2nd input).")
                    except Exception:
                        pwd_input = None
                if not pwd_input:
                    logger.error("Password input not found on login page.")
                    debug_path = _dump_login_debug(page, "password_input_not_found")
                    if debug_path:
                        logger.error("Login debug saved to %s", debug_path)
                    return False
                pwd_input.clear()
                pwd_input.input(password)
                logger.info("Password entered successfully.")

                login_selectors = [
                    'xpath://button[contains(text(), "Login")]',
                    'xpath://button[contains(text(), "登录")]',
                    'xpath://button[contains(text(), "Sign")]',
                    'xpath://button[contains(text(), "Continue")]',
                    'xpath://button[@type="submit"]',
                    'css:button[type="submit"]',
                    'xpath://*[@role="button" and (contains(text(), "Login") or contains(text(), "登录") or contains(text(), "Continue"))]',
                ]
                login_btn = None
                for selector in login_selectors:
                    try:
                        login_btn = page.ele(selector, timeout=5)
                        if login_btn:
                            logger.info(f"Login button found with selector: {selector}")
                            break
                    except Exception:
                        continue
                if not login_btn:
                    # Try submitting the form via JS as a last resort.
                    try:
                        submitted_by_form = page.run_js(
                            "(() => { const form = document.querySelector('form'); "
                            "if (!form) return false; "
                            "if (form.requestSubmit) { form.requestSubmit(); return true; } "
                            "if (form.submit) { form.submit(); return true; } "
                            "return false; })()",
                            as_expr=True,
                        )
                        if submitted_by_form:
                            logger.info("Login submitted via JS form submit fallback.")
                            submitted = True
                    except Exception:
                        pass

                if not login_btn and not submitted:
                    try:
                        login_btn = page.ele("css:button", timeout=3)
                        if login_btn:
                            logger.info("Login button found via fallback selector.")
                    except Exception:
                        login_btn = None
                if not login_btn and not submitted:
                    logger.error("Login button not found.")
                    debug_path = _dump_login_debug(page, "login_button_not_found")
                    if debug_path:
                        logger.error("Login debug saved to %s", debug_path)
                    return False
                if login_btn:
                    login_btn.click()
                    submitted = True

            if not submitted:
                debug_path = _dump_login_debug(page, "login_not_submitted")
                if debug_path:
                    logger.error("Login was not submitted; debug saved to %s", debug_path)
                else:
                    logger.error("Login was not submitted.")
                return False

            logger.info("Waiting for login to complete...")
            for _ in range(60):
                try:
                    token_now = (_get_storage_item(page, "account_token") or "").strip()
                    if token_now:
                        break
                except Exception:
                    pass
                try:
                    if "login" not in (page.url or "").lower():
                        pass
                except Exception:
                    pass
                time.sleep(1)
            time.sleep(2)

            local_storage = _extract_storage(page, "localStorage")
            session_storage = _extract_storage(page, "sessionStorage")

            account_token = (local_storage.get("account_token") or _get_storage_item(page, "account_token") or "").strip()
            refresh_token = (local_storage.get("refresh_token") or _get_storage_item(page, "refresh_token") or "").strip()

            if not account_token:
                logger.error("Login finished but account_token not found (captcha/2FA?).")
                debug_path = _dump_login_debug(page, "account_token_not_found")
                if debug_path:
                    logger.error("Login debug saved to %s", debug_path)
                return False

            # Save artifacts
            token_payload = dict(local_storage)
            token_payload["account_token"] = account_token
            if refresh_token:
                token_payload["refresh_token"] = refresh_token
            token_payload.setdefault("language", "en-US")
            _atomic_write_json(LOCALSTORAGE_FILE, token_payload)
            _atomic_write_json(SESSIONSTORAGE_FILE, session_storage)

            cookies = []
            try:
                cookies = page.cookies() or []
            except Exception:
                cookies = []
            _atomic_write_json(COOKIES_FILE, cookies)

            logger.info("Token refreshed successfully via Chromium.")
            return True
        except Exception as exc:
            logger.error("Browser login failed: %s", exc)
            if _resolve_bool_env("VALUESCAN_LOGIN_CDP_FALLBACK", True):
                if _run_cdp_login(email, password):
                    return True
            return False
        finally:
            if page:
                try:
                    page.quit()
                except Exception:
                    pass


def refresh_if_needed(
    email: Optional[str] = None,
    password: Optional[str] = None,
    headless: bool = False,
    force: bool = False,
) -> bool:
    """
    Ensure tokens are present and not expiring soon. Uses saved credentials if not provided.
    Returns True if tokens are valid or refresh succeeded.
    """
    data = _load_localstorage()
    account_token = (data.get("account_token") or "").strip()
    needs_login = force or (not account_token)

    if not needs_login:
        return True

    creds = {"email": email or "", "password": password or ""}
    if not creds["email"] or not creds["password"]:
        saved = load_credentials()
        if saved:
            creds = saved
    if not creds["email"] or not creds["password"]:
        env_email = (os.getenv("VALUESCAN_EMAIL") or "").strip()
        env_password = (os.getenv("VALUESCAN_PASSWORD") or "").strip()
        if env_email and env_password:
            creds = {"email": env_email, "password": env_password}

    if not creds["email"] or not creds["password"]:
        logger.warning("No credentials available for browser login; cannot refresh token.")
        return False

    logger.info("Token missing/expiring; refreshing via Chromium login...")
    ok = login_and_refresh_token(creds["email"], creds["password"], headless=headless)
    if ok:
        save_credentials(creds["email"], creds["password"])
    else:
        time.sleep(LOGIN_RETRY_COOLDOWN_SECONDS)
    return ok


def run_refresh_loop(email: str, password: str, interval_hours: float = TOKEN_REFRESH_INTERVAL_HOURS) -> None:
    """
    Background loop: refresh when near expiry; otherwise sleep until the next window.
    """
    save_credentials(email, password)
    while True:
        try:
            refreshed = refresh_if_needed(email, password, headless=False)
            if refreshed:
                sleep_seconds = interval_hours * 3600
            else:
                sleep_seconds = LOGIN_RETRY_COOLDOWN_SECONDS
            logger.info("Sleeping for %.0f seconds before next check.", sleep_seconds)
            time.sleep(sleep_seconds)
        except KeyboardInterrupt:
            logger.info("Token refresher stopped by user.")
            break
        except Exception as exc:
            logger.error("Refresh loop error: %s", exc)
            time.sleep(LOGIN_RETRY_COOLDOWN_SECONDS)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="ValueScan token refresher (Chromium based)")
    parser.add_argument("--email", "-e", help="Login email")
    parser.add_argument("--password", "-p", help="Login password")
    parser.add_argument("--once", action="store_true", help="Login once and exit")
    parser.add_argument(
        "--interval",
        "-i",
        type=float,
        default=TOKEN_REFRESH_INTERVAL_HOURS,
        help=f"Refresh interval hours (default {TOKEN_REFRESH_INTERVAL_HOURS})",
    )
    parser.add_argument("--no-headless", action="store_true", help="Show browser window for debugging")

    args = parser.parse_args()

    email = args.email
    password = args.password

    if not email or not password:
        env_creds = _load_env_credentials()
        if env_creds:
            email = env_creds["email"]
            password = env_creds["password"]

    if not email or not password:
        saved = load_credentials()
        if saved:
            email = saved.get("email")
            password = saved.get("password")

    if not email or not password:
        logger.error("Please provide credentials: --email <email> --password <password>")
        sys.exit(1)

    if args.once:
        success = login_and_refresh_token(email, password, headless=not args.no_headless)
        sys.exit(0 if success else 1)
    else:
        run_refresh_loop(email, password, args.interval)


if __name__ == "__main__":
    main()
