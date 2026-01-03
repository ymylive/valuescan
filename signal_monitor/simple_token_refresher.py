#!/usr/bin/env python3
"""
Simple token refresher using Selenium
Compatible with Python 3.9+
"""
import time
import sys
import os
import json
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
CREDENTIALS_FILE = BASE_DIR / "valuescan_credentials.json"
TOKEN_FILE = BASE_DIR / "valuescan_localstorage.json"

def load_credentials():
    """Load credentials from environment variables or file"""
    # 优先从环境变量读取
    email = os.getenv('VALUESCAN_EMAIL')
    password = os.getenv('VALUESCAN_PASSWORD')

    if email and password:
        logger.info(f"Loaded credentials from environment variables: {email}")
        return email, password

    # 如果环境变量没有，从文件读取
    if not CREDENTIALS_FILE.exists():
        logger.error(f"Credentials file not found: {CREDENTIALS_FILE}")
        return None, None

    try:
        with open(CREDENTIALS_FILE, 'r', encoding='utf-8') as f:
            creds = json.load(f)
            return creds.get('email'), creds.get('password')
    except Exception as e:
        logger.error(f"Failed to load credentials: {e}")
        return None, None

def refresh_token():
    """Refresh token using Selenium"""
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    email, password = load_credentials()
    if not email or not password:
        logger.error("No credentials available")
        return False

    logger.info("Starting token refresh...")

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-proxy-server")
    options.add_argument("--proxy-server='direct://'")
    options.add_argument("--proxy-bypass-list=*")
    options.binary_location = "/usr/bin/chromium-browser"

    user_data_dir = "/root/.config/chromium/valuescan_token"
    os.makedirs(user_data_dir, exist_ok=True)
    options.add_argument(f"--user-data-dir={user_data_dir}")

    driver = None
    try:
        driver = webdriver.Chrome(options=options)
        logger.info("Browser started")

        logger.info("Navigating to valuescan.io...")
        driver.get("https://valuescan.io")
        time.sleep(5)

        logger.info("Looking for login button...")
        wait = WebDriverWait(driver, 20)

        # Try multiple selectors for login button
        login_found = False
        for selector in [
            "//button[contains(., 'Login')]",
            "//button[contains(., 'login')]",
            "//a[contains(., 'Login')]",
            "//button[contains(@class, 'login')]"
        ]:
            try:
                login_btn = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                login_btn.click()
                login_found = True
                logger.info(f"Clicked login button: {selector}")
                break
            except:
                continue

        if not login_found:
            logger.warning("Login button not found, might already be logged in")

        time.sleep(3)

        # Try to find and fill email input
        logger.info("Looking for email input...")
        email_input = None
        for selector in ["input[type='email']", "input[name='email']", "input[placeholder*='email' i]"]:
            try:
                email_input = driver.find_element(By.CSS_SELECTOR, selector)
                break
            except:
                continue

        if email_input:
            email_input.clear()
            email_input.send_keys(email)
            logger.info("Email entered")
            time.sleep(2)

            # Find password input with multiple selectors
            logger.info("Looking for password input...")
            password_input = None
            password_selectors = [
                "input[type='password']",
                "input[name='password']",
                "input[placeholder*='password' i]",
                "input[placeholder*='Password']",
                "input[autocomplete='current-password']"
            ]

            for selector in password_selectors:
                try:
                    password_input = driver.find_element(By.CSS_SELECTOR, selector)
                    logger.info(f"Found password input with: {selector}")
                    break
                except:
                    continue

            if not password_input:
                logger.error("Password input not found")
                driver.save_screenshot("/tmp/valuescan_login_error.png")
                driver.quit()
                return False

            password_input.clear()
            password_input.send_keys(password)
            logger.info("Password entered")
            time.sleep(2)

            # Submit form
            submit_btn = driver.find_element(By.XPATH, "//button[@type='submit']")
            submit_btn.click()
            logger.info("Login form submitted")
            time.sleep(5)

        # Extract localStorage
        logger.info("Extracting localStorage...")
        local_storage = driver.execute_script("return JSON.stringify(localStorage);")
        storage_data = json.loads(local_storage)

        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            json.dump(storage_data, f, ensure_ascii=False, indent=2)

        logger.info(f"Token saved to {TOKEN_FILE}")
        logger.info(f"Storage keys: {list(storage_data.keys())}")

        driver.quit()
        return True

    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        import traceback
        traceback.print_exc()
        if driver:
            try:
                driver.quit()
            except:
                pass
        return False

def main():
    """Main loop for token refresher"""
    import argparse

    parser = argparse.ArgumentParser(description='ValueScan Token Refresher')
    parser.add_argument('--interval', type=float, default=0.8, help='Refresh interval in hours')
    parser.add_argument('--once', action='store_true', help='Run once and exit')
    args = parser.parse_args()

    if args.once:
        logger.info("Running token refresh once...")
        success = refresh_token()
        sys.exit(0 if success else 1)

    logger.info(f"Starting token refresher with interval: {args.interval} hours")

    while True:
        try:
            success = refresh_token()
            if success:
                logger.info(f"Token refresh successful, sleeping for {args.interval} hours")
            else:
                logger.error("Token refresh failed, will retry in 5 minutes")
                time.sleep(300)
                continue

            time.sleep(args.interval * 3600)
        except KeyboardInterrupt:
            logger.info("Token refresher stopped by user")
            break
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            time.sleep(300)

if __name__ == "__main__":
    main()
