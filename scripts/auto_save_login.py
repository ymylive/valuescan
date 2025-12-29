#!/usr/bin/env python3
"""
Automate ValueScan login and save browser storage/cookies.

This is a helper for local development. It never hardcodes credentials.

Usage:
  python scripts/auto_save_login.py <email> <password>

Or set env vars:
  VALUESCAN_EMAIL, VALUESCAN_PASSWORD
"""

from __future__ import annotations

import json
import os
import sys
import time


def _get_credentials() -> tuple[str, str]:
    email = (os.getenv("VALUESCAN_EMAIL") or "").strip()
    password = (os.getenv("VALUESCAN_PASSWORD") or "").strip()
    if len(sys.argv) > 1:
        email = sys.argv[1].strip()
    if len(sys.argv) > 2:
        password = sys.argv[2].strip()
    if not email or not password:
        raise SystemExit(
            "Missing credentials. Pass args: scripts/auto_save_login.py <email> <password> "
            "or set env VALUESCAN_EMAIL/VALUESCAN_PASSWORD."
        )
    return email, password


def main() -> int:
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.chrome.options import Options
    except ImportError:
        raise SystemExit("selenium not installed. Run: pip install selenium")

    email, password = _get_credentials()

    print("=" * 60)
    print("ValueScan auto-login helper")
    print("After login completes, this script will save cookies/localStorage/sessionStorage.")
    print("=" * 60)

    options = Options()
    options.add_argument("--start-maximized")

    driver = webdriver.Chrome(options=options)
    try:
        driver.get("https://www.valuescan.io/login")
        time.sleep(3)

        try:
            email_input = driver.find_element(
                By.XPATH,
                "//input[@type='email' or @name='email' or contains(@placeholder, 'mail')]",
            )
            email_input.clear()
            email_input.send_keys(email)
        except Exception:
            print("Email input not found; please fill it manually.")

        try:
            pwd_input = driver.find_element(By.XPATH, "//input[@type='password']")
            pwd_input.clear()
            pwd_input.send_keys(password)
        except Exception:
            print("Password input not found; please fill it manually.")

        print("Please finish login in the browser (captcha/2FA if any).")
        print("Waiting 60 seconds before saving...")
        for i in range(60, 0, -5):
            print(f"  saving in {i}s ...")
            time.sleep(5)

        out_dir = os.path.dirname(__file__)

        cookies = driver.get_cookies()
        with open(os.path.join(out_dir, "valuescan_cookies.json"), "w", encoding="utf-8") as f:
            json.dump(cookies, f, indent=2, ensure_ascii=False)

        local_storage = driver.execute_script("return JSON.stringify(localStorage);")
        with open(os.path.join(out_dir, "valuescan_localstorage.json"), "w", encoding="utf-8") as f:
            f.write(local_storage or "{}")

        session_storage = driver.execute_script("return JSON.stringify(sessionStorage);")
        with open(os.path.join(out_dir, "valuescan_sessionstorage.json"), "w", encoding="utf-8") as f:
            f.write(session_storage or "{}")

        print("Saved artifacts to scripts/: valuescan_cookies.json, valuescan_localstorage.json, valuescan_sessionstorage.json")
        return 0
    finally:
        driver.quit()


if __name__ == "__main__":
    raise SystemExit(main())

