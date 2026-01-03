#!/usr/bin/env python3
"""
ValueScan login helper for the web dashboard.

This script logs into https://www.valuescan.io using DrissionPage, then saves:
  - valuescan_cookies.json
  - valuescan_localstorage.json (account_token/refresh_token + full localStorage dump if available)
  - valuescan_sessionstorage.json (best-effort)

Usage:
  python http_login.py <email> <password>

Or set env vars:
  VALUESCAN_EMAIL, VALUESCAN_PASSWORD
"""

import json
import os
import sys
import time
from pathlib import Path

# Python 3.7+ compatible type hints
try:
    from typing import Any, Dict, Optional, Tuple
except ImportError:
    pass


def _get_credentials():
    email = (os.getenv("VALUESCAN_EMAIL") or "").strip()
    password = (os.getenv("VALUESCAN_PASSWORD") or "").strip()
    if len(sys.argv) > 1:
        email = sys.argv[1].strip()
    if len(sys.argv) > 2:
        password = sys.argv[2].strip()
    if not email or not password:
        raise SystemExit(
            "Missing credentials. Use: python http_login.py <email> <password> "
            "or set VALUESCAN_EMAIL/VALUESCAN_PASSWORD."
        )
    return email, password


def _pick_browser_path():
    candidates = [
        "/usr/bin/chromium-browser",
        "/usr/bin/chromium",
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


def _dp_localstorage_get(page, key):
    try:
        expr = f"localStorage.getItem({json.dumps(key)})"
        val = page.run_js(expr, as_expr=True)
        if isinstance(val, str):
            val = val.strip()
            return val if val else None
    except Exception:
        return None
    return None


def _dp_storage_dump(page, storage_name):
    try:
        js = f"JSON.stringify({storage_name})"
        raw = page.run_js(js, as_expr=True)
        if isinstance(raw, str) and raw.strip():
            return json.loads(raw)
    except Exception:
        return {}
    return {}


def main():
    email, password = _get_credentials()

    out_dir = Path(os.getenv("VALUESCAN_LOGIN_OUT_DIR") or Path(__file__).resolve().parent)
    out_dir.mkdir(parents=True, exist_ok=True)

    cookies_path = Path(os.getenv("VALUESCAN_COOKIES_FILE") or (out_dir / "valuescan_cookies.json"))
    token_path = Path(os.getenv("VALUESCAN_TOKEN_FILE") or (out_dir / "valuescan_localstorage.json"))
    session_path = out_dir / "valuescan_sessionstorage.json"

    headless = os.getenv("VALUESCAN_LOGIN_HEADLESS", "1").strip() != "0"

    try:
        from DrissionPage import ChromiumOptions, ChromiumPage
    except Exception as exc:
        print(f"DrissionPage not available: {exc}", file=sys.stderr)
        return 2

    options = ChromiumOptions()
    try:
        options.headless(headless)
    except Exception:
        if headless:
            options.set_argument("--headless", "new")

    options.set_argument("--no-sandbox")
    options.set_argument("--disable-dev-shm-usage")
    options.set_argument("--disable-gpu")
    options.set_argument("--window-size", "1920,1080")

    browser_path = (os.getenv("VALUESCAN_BROWSER_PATH") or "").strip() or _pick_browser_path()
    if browser_path:
        try:
            options.set_browser_path(browser_path)
        except Exception:
            pass

    # Use a dedicated profile directory to avoid conflicts with other Chrome instances
    profile_dir = (os.getenv("VALUESCAN_LOGIN_PROFILE_DIR") or "").strip()
    if not profile_dir:
        # Default to a unique temp directory for login sessions
        import tempfile
        profile_dir = os.path.join(tempfile.gettempdir(), "valuescan_login_profile")
    try:
        Path(profile_dir).mkdir(parents=True, exist_ok=True)
        options.set_user_data_path(profile_dir)
    except Exception:
        pass

    page = None
    try:
        page = ChromiumPage(addr_or_opts=options)
        page.get("https://www.valuescan.io/login")
        
        # Wait longer for page to fully load
        time.sleep(5)
        
        # Try multiple selectors for email input
        email_selectors = [
            'xpath://input[@type="email"]',
            'xpath://input[contains(@placeholder, "email")]',
            'xpath://input[contains(@placeholder, "Email")]',
            'xpath://input[contains(@placeholder, "mail")]',
            'css:input[type="email"]',
            'css:input[placeholder*="email" i]',
        ]
        
        email_input = None
        for selector in email_selectors:
            try:
                email_input = page.ele(selector, timeout=3)
                if email_input:
                    print(f"Found email input with: {selector}")
                    break
            except Exception:
                continue
        
        if not email_input:
            print("Email input not found", file=sys.stderr)
            print(f"Page URL: {page.url}", file=sys.stderr)
            return 1
        email_input.clear()
        email_input.input(email)
        time.sleep(0.5)

        pwd_input = page.ele('xpath://input[@type="password"]', timeout=5) or page.ele('css:input[type="password"]', timeout=3)
        if not pwd_input:
            print("Password input not found", file=sys.stderr)
            return 1
        pwd_input.clear()
        pwd_input.input(password)

        # Try multiple selectors for login button
        login_selectors = [
            'xpath://button[contains(text(), "Login")]',
            'xpath://button[contains(text(), "登录")]',
            'xpath://button[contains(text(), "Sign")]',
            'xpath://button[@type="submit"]',
            'css:button[type="submit"]',
        ]
        
        login_btn = None
        for selector in login_selectors:
            try:
                login_btn = page.ele(selector, timeout=3)
                if login_btn:
                    print(f"Found login button with: {selector}")
                    break
            except Exception:
                continue
        
        if not login_btn:
            print("Login button not found", file=sys.stderr)
            return 1
        login_btn.click()

        # Wait for redirect / tokens to appear.
        print("Waiting for login to complete...")
        for i in range(30):
            if "login" not in (page.url or "").lower():
                print(f"Redirected to: {page.url}")
                break
            time.sleep(1)
        
        # Extra wait for tokens to be set
        time.sleep(2)

        account_token = _dp_localstorage_get(page, "account_token") or ""
        refresh_token = _dp_localstorage_get(page, "refresh_token") or ""

        cookies = []
        try:
            cookies = page.cookies() or []
        except Exception:
            cookies = []

        local_storage = _dp_storage_dump(page, "localStorage")
        session_storage = _dp_storage_dump(page, "sessionStorage")

        token_payload = dict(local_storage) if isinstance(local_storage, dict) else {}
        if account_token:
            token_payload["account_token"] = account_token
        if refresh_token:
            token_payload["refresh_token"] = refresh_token

        cookies_path.parent.mkdir(parents=True, exist_ok=True)
        cookies_path.write_text(json.dumps(cookies, indent=2, ensure_ascii=False), encoding="utf-8")

        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(json.dumps(token_payload, indent=2, ensure_ascii=False), encoding="utf-8")

        session_path.write_text(json.dumps(session_storage, indent=2, ensure_ascii=False), encoding="utf-8")

        ok = bool(account_token) or bool(cookies)
        if not ok:
            print("Login finished but no tokens/cookies found (captcha/2FA?)", file=sys.stderr)
            return 1

        print(f"Saved cookies to: {cookies_path}")
        print(f"Saved localStorage to: {token_path}")
        print(f"Saved sessionStorage to: {session_path}")
        return 0
    except Exception as exc:
        print(f"Login error: {exc}", file=sys.stderr)
        return 1
    finally:
        try:
            if page:
                page.quit()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())

