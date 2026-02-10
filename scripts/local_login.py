#!/usr/bin/env python3
"""
Local login helper: open ValueScan login page, then save cookies for server use.

Usage:
  python scripts/local_login.py <email> <password>

Or set env vars:
  VALUESCAN_EMAIL, VALUESCAN_PASSWORD

Output (ignored by git):
  scripts/valuescan_cookies.json
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
            "Missing credentials. Pass args: scripts/local_login.py <email> <password> "
            "or set env VALUESCAN_EMAIL/VALUESCAN_PASSWORD."
        )
    return email, password


def main() -> int:
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
    except ImportError:
        raise SystemExit("selenium not installed. Run: pip install selenium")

    email, password = _get_credentials()

    options = Options()
    options.add_argument("--start-maximized")

    driver = webdriver.Chrome(options=options)
    try:
        driver.get("https://www.valuescan.io/login")
        time.sleep(3)

        wait = WebDriverWait(driver, 15)

        try:
            email_input = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//input[@type='email' or @name='email' or contains(@placeholder, 'mail')]")
                )
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

        print("Finish login in the browser (captcha/2FA if any).")
        print("When done, type 'ok' here and press Enter.")
        while True:
            if input().strip().lower() == "ok":
                break
            print("Type 'ok' when login is complete.")

        cookies = driver.get_cookies()
        cookies_file = os.path.join(os.path.dirname(__file__), "valuescan_cookies.json")
        with open(cookies_file, "w", encoding="utf-8") as f:
            json.dump(cookies, f, indent=2, ensure_ascii=False)

        print(f"Saved cookies to: {cookies_file}")
        return 0
    finally:
        driver.quit()


if __name__ == "__main__":
    raise SystemExit(main())

