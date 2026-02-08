#!/usr/bin/env python3
"""
Chrome-based token refresher with remote debugging
More stable for VPS environments
"""
import time
import sys
import os
import json
import logging
import subprocess
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
CREDENTIALS_FILE = BASE_DIR / "valuescan_credentials.json"
TOKEN_FILE = BASE_DIR / "valuescan_localstorage.json"
CHROME_DEBUG_PORT = 9222

def load_credentials():
    """Load credentials from environment variables or file"""
    email = os.getenv('VALUESCAN_EMAIL')
    password = os.getenv('VALUESCAN_PASSWORD')

    if email and password:
        logger.info(f"Loaded credentials from environment: {email}")
        return email, password

    if CREDENTIALS_FILE.exists():
        try:
            with open(CREDENTIALS_FILE, 'r', encoding='utf-8') as f:
                creds = json.load(f)
                return creds.get('email'), creds.get('password')
        except Exception as e:
            logger.error(f"Failed to load credentials: {e}")

    return None, None

def start_chrome_debug():
    """Start Chrome in remote debugging mode with low memory settings"""
    chrome_cmd = [
        '/usr/bin/chromium-browser',
        f'--remote-debugging-address=127.0.0.1',
        f'--remote-debugging-port={CHROME_DEBUG_PORT}',
        '--no-first-run',
        '--no-default-browser-check',
        '--disable-gpu',
        '--disable-dev-shm-usage',
        '--disable-software-rasterizer',
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--user-data-dir=/tmp/chrome-valuescan',
        '--headless=new',
        '--window-size=1280,720',
        '--disable-extensions',
        '--disable-plugins',
        '--disable-images',
        '--blink-settings=imagesEnabled=false',
        '--disable-background-networking',
        '--disable-sync',
        '--mute-audio',
        '--no-pings'
    ]

    try:
        # Kill existing Chrome processes
        subprocess.run(['pkill', '-f', 'chromium-browser'], stderr=subprocess.DEVNULL)
        time.sleep(2)

        # Start Chrome
        proc = subprocess.Popen(chrome_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(3)
        logger.info(f"Chrome started with PID: {proc.pid}")
        return proc
    except Exception as e:
        logger.error(f"Failed to start Chrome: {e}")
        return None

def refresh_token():
    """Refresh token using Chrome with remote debugging"""
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    email, password = load_credentials()
    if not email or not password:
        logger.error("No credentials available")
        return False

    chrome_proc = None
    driver = None

    try:
        # Start Chrome in debug mode
        chrome_proc = start_chrome_debug()
        if not chrome_proc:
            return False

        # Connect to Chrome
        options = Options()
        options.add_experimental_option("debuggerAddress", f"127.0.0.1:{CHROME_DEBUG_PORT}")

        driver = webdriver.Chrome(options=options)
        logger.info("Connected to Chrome")

        # Navigate to valuescan.io
        logger.info("Navigating to valuescan.io...")
        driver.get("https://valuescan.io")
        time.sleep(5)

        # Look for login button
        logger.info("Looking for login button...")
        wait = WebDriverWait(driver, 20)
        login_found = False

        for selector in [
            "//button[contains(., 'Login')]",
            "//button[contains(., 'login')]",
            "//a[contains(., 'Login')]"
        ]:
            try:
                login_btn = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                login_btn.click()
                login_found = True
                logger.info(f"Clicked login button")
                break
            except:
                continue

        if not login_found:
            logger.warning("Login button not found, might already be logged in")

        time.sleep(3)

        # Find email input with explicit wait
        logger.info("Looking for email input...")
        email_input = None
        for selector in ["input[type='email']", "input[name='email']", "input[placeholder*='email' i]"]:
            try:
                email_input = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                break
            except:
                continue

        if email_input:
            email_input.clear()
            email_input.send_keys(email)
            logger.info("Email entered")
            time.sleep(3)  # 增加等待时间，让密码框出现

            # Find password input with more selectors
            logger.info("Looking for password input...")
            password_input = None
            password_selectors = [
                "input[type='password']",
                "input[name='password']",
                "input[placeholder*='password' i]",
                "input[placeholder*='Password']",
                "input[autocomplete='current-password']",
                "input[id*='password' i]"
            ]

            for selector in password_selectors:
                try:
                    password_input = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                    logger.info(f"Found password input with: {selector}")
                    break
                except:
                    continue

            if not password_input:
                logger.error("Password input not found")
                return False

            password_input.clear()
            password_input.send_keys(password)
            logger.info("Password entered")
            time.sleep(2)

            # Submit form and immediately extract localStorage
            submit_btn = driver.find_element(By.XPATH, "//button[@type='submit']")
            submit_btn.click()
            logger.info("Login form submitted")
            time.sleep(2)  # 最小等待时间

        # 快速提取 localStorage
        logger.info("Extracting localStorage...")
        storage_data = None

        # 先尝试快速提取
        try:
            local_storage = driver.execute_script("return JSON.stringify(localStorage);")
            storage_data = json.loads(local_storage)
            logger.info("localStorage extracted successfully")
        except Exception as e:
            logger.warning(f"Quick extraction failed: {e}")
            # 等待后重试
            time.sleep(2)
            for attempt in range(2):
                try:
                    local_storage = driver.execute_script("return JSON.stringify(localStorage);")
                    storage_data = json.loads(local_storage)
                    logger.info(f"localStorage extracted on attempt {attempt+2}")
                    break
                except Exception as e:
                    logger.warning(f"Attempt {attempt+2} failed: {e}")
                    if attempt < 1:
                        time.sleep(1)

        if not storage_data:
            logger.error("Failed to extract localStorage")
            return False

        # 验证 localStorage 内容是否有效
        if len(storage_data) <= 2 or 'last_error' in storage_data:
            logger.error(f"Invalid localStorage content: {list(storage_data.keys())}")
            return False

        # 检查是否包含必要的认证信息
        has_auth = any(key for key in storage_data.keys() if 'token' in key.lower() or 'auth' in key.lower() or 'user' in key.lower())
        if not has_auth:
            logger.warning(f"No auth tokens found in localStorage: {list(storage_data.keys())}")

        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            json.dump(storage_data, f, ensure_ascii=False, indent=2)

        logger.info(f"Token saved to {TOKEN_FILE}")
        logger.info(f"Storage keys: {list(storage_data.keys())}")

        driver.quit()
        if chrome_proc:
            chrome_proc.terminate()
        return True

    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        if driver:
            try:
                driver.quit()
            except:
                pass
        if chrome_proc:
            try:
                chrome_proc.terminate()
            except:
                pass
        return False

def main():
    """Main loop"""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--interval', type=float, default=0.8)
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()

    if args.once:
        success = refresh_token()
        sys.exit(0 if success else 1)

    logger.info(f"Starting token refresher (interval: {args.interval}h)")
    while True:
        try:
            success = refresh_token()
            if success:
                logger.info(f"Success, sleeping {args.interval}h")
            else:
                logger.error("Failed, retry in 5 min")
                time.sleep(300)
                continue
            time.sleep(args.interval * 3600)
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Error: {e}")
            time.sleep(300)

if __name__ == "__main__":
    main()
