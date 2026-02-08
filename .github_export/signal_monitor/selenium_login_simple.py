#!/usr/bin/env python3
import time
import sys
import os
import json

def login_valuescan(email, password):
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    print("Starting browser...")

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.binary_location = "/usr/bin/chromium-browser"

    user_data_dir = "/root/.config/chromium/valuescan_selenium"
    os.makedirs(user_data_dir, exist_ok=True)
    options.add_argument(f"--user-data-dir={user_data_dir}")

    try:
        driver = webdriver.Chrome(options=options)
        print("Browser started successfully")

        print("Navigating to valuescan.io...")
        driver.get("https://valuescan.io")
        time.sleep(3)

        print("Looking for login button...")
        wait = WebDriverWait(driver, 20)

        # Try to find login button
        login_selectors = [
            "//button[contains(text(), 'Login')]",
            "//button[contains(text(), 'login')]",
            "//a[contains(text(), 'Login')]",
            "//a[contains(text(), 'login')]",
        ]

        login_btn = None
        for selector in login_selectors:
            try:
                login_btn = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                break
            except:
                continue

        if not login_btn:
            print("Could not find login button")
            driver.quit()
            return False

        login_btn.click()
        time.sleep(2)

        print("Entering credentials...")

        # Find email input
        email_selectors = [
            "input[type='email']",
            "input[name='email']",
            "input[placeholder*='email' i]",
        ]

        email_input = None
        for selector in email_selectors:
            try:
                email_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                break
            except:
                continue

        if not email_input:
            print("Could not find email input")
            driver.quit()
            return False

        email_input.clear()
        email_input.send_keys(email)
        time.sleep(1)

        # Find password input
        password_input = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
        password_input.clear()
        password_input.send_keys(password)
        time.sleep(1)

        print("Submitting login form...")
        submit_btn = driver.find_element(By.XPATH, "//button[@type='submit']")
        submit_btn.click()

        print("Waiting for login to complete...")
        time.sleep(5)

        print("Extracting localStorage...")
        local_storage = driver.execute_script("return JSON.stringify(localStorage);")
        storage_data = json.loads(local_storage)

        token_file = "/root/valuescan/signal_monitor/valuescan_localstorage.json"
        with open(token_file, "w", encoding="utf-8") as f:
            json.dump(storage_data, f, ensure_ascii=False, indent=2)

        print(f"Token saved to {token_file}")
        print(f"Storage keys: {list(storage_data.keys())}")

        driver.quit()
        return True

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        try:
            driver.quit()
        except:
            pass
        return False

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 selenium_login_simple.py <email> <password>")
        sys.exit(1)

    email = sys.argv[1]
    password = sys.argv[2]

    success = login_valuescan(email, password)
    sys.exit(0 if success else 1)
