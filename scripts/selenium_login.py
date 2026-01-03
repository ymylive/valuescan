#!/usr/bin/env python3
"""
Use Selenium to login and save ValueScan token localStorage to a JSON file.

Usage:
  python scripts/selenium_login.py <email> <password>

Or set env vars:
  VALUESCAN_EMAIL, VALUESCAN_PASSWORD
  SOCKS5_PROXY (optional, e.g. socks5://127.0.0.1:1080)
  VALUESCAN_TOKEN_FILE (optional output path)
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
            "Missing credentials. Pass args: scripts/selenium_login.py <email> <password> "
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
    proxy = (os.getenv("SOCKS5_PROXY") or "").strip()

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    if proxy:
        options.add_argument(f"--proxy-server={proxy}")

    driver = webdriver.Chrome(options=options)
    try:
        driver.get("https://www.valuescan.io/login")
        time.sleep(3)

        wait = WebDriverWait(driver, 15)
        email_input = wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "input[type='text'], input[type='email'], input[placeholder*='mail']")
            )
        )
        email_input.clear()
        email_input.send_keys(email)

        pwd_input = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
        pwd_input.clear()
        pwd_input.send_keys(password)

        try:
            login_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            login_btn.click()
        except Exception:
            pass

        time.sleep(6)

        account_token = driver.execute_script("return localStorage.getItem('account_token')")
        refresh_token = driver.execute_script("return localStorage.getItem('refresh_token')")
        if not account_token:
            print("Login did not produce account_token; check captcha/2FA.")
            return 1

        output_path = os.getenv("VALUESCAN_TOKEN_FILE") or os.path.join(
            os.getcwd(), "valuescan_localstorage.json"
        )
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(
                {"account_token": account_token, "refresh_token": refresh_token or "", "language": "en-US"},
                f,
                indent=2,
                ensure_ascii=False,
            )
        print(f"Token saved to: {output_path}")
        return 0
    finally:
        driver.quit()


if __name__ == "__main__":
    raise SystemExit(main())

