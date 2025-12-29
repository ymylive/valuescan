#!/usr/bin/env python3
"""Direct login test on VPS using Selenium"""
import os
import paramiko

def main():
    password = os.environ.get('VALUESCAN_VPS_PASSWORD')
    if not password:
        print("Missing VALUESCAN_VPS_PASSWORD env var")
        return
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('82.158.88.34', username='root', password=password)
    
    # First check if selenium is installed
    stdin, stdout, stderr = ssh.exec_command('pip3.9 show selenium 2>&1')
    output = stdout.read().decode()
    if 'not found' in output.lower() or not output.strip():
        print("Installing selenium...")
        stdin, stdout, stderr = ssh.exec_command('pip3.9 install selenium 2>&1', timeout=120)
        print(stdout.read().decode())
    
    # Upload and run test script
    test_code = r'''#!/usr/bin/env python3
import time
import json
import subprocess
from pathlib import Path

email = "ymy_live@outlook.com"
pwd = "Qq159741."

# Stop signal monitor to free memory
print("Stopping signal monitor to free memory...")
subprocess.run(["systemctl", "stop", "valuescan-signal"], timeout=30)
time.sleep(3)

# Kill any remaining chromium processes
subprocess.run(["pkill", "-9", "chromium"], capture_output=True)
subprocess.run(["pkill", "-9", "chrome"], capture_output=True)
time.sleep(2)

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1280,720")
options.add_argument("--disable-extensions")
options.binary_location = "/usr/bin/chromium-browser"

driver = None
success = False
try:
    # Try to find chromedriver
    chromedriver_paths = [
        "/usr/bin/chromedriver",
        "/usr/local/bin/chromedriver",
        "/snap/bin/chromium.chromedriver",
    ]
    chromedriver = None
    for p in chromedriver_paths:
        if Path(p).exists():
            chromedriver = p
            break
    
    if chromedriver:
        service = Service(chromedriver)
        driver = webdriver.Chrome(service=service, options=options)
    else:
        driver = webdriver.Chrome(options=options)
    
    print("Browser launched successfully")
    
    driver.get("https://www.valuescan.io/login")
    print("Navigated to login page")
    
    time.sleep(8)
    print(f"Current URL: {driver.current_url}")
    
    wait = WebDriverWait(driver, 20)
    
    # Find and fill email
    try:
        email_input = wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, 'input[placeholder*="email" i], input[type="email"]')
        ))
        email_input.clear()
        email_input.send_keys(email)
        print("Email entered")
    except Exception as e:
        print(f"Email input error: {e}")
        js = "const inputs = document.querySelectorAll('input'); for (let inp of inputs) { const ph = (inp.placeholder || '').toLowerCase(); if (ph.includes('email')) { inp.value = '" + email + "'; inp.dispatchEvent(new Event('input', { bubbles: true })); break; } }"
        driver.execute_script(js)
        print("Email entered via JS")
    
    time.sleep(1)
    
    # Find and fill password
    try:
        pwd_input = wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, 'input[type="password"]')
        ))
        pwd_input.clear()
        pwd_input.send_keys(pwd)
        print("Password entered")
    except Exception as e:
        print(f"Password input error: {e}")
        js = "const p = document.querySelector('input[type=\"password\"]'); if (p) { p.value = '" + pwd + "'; p.dispatchEvent(new Event('input', { bubbles: true })); }"
        driver.execute_script(js)
        print("Password entered via JS")
    
    time.sleep(1)
    
    # Click login button
    try:
        login_btn = driver.find_element(By.XPATH, '//button[contains(text(), "Login")]')
        login_btn.click()
        print("Login button clicked")
    except:
        try:
            login_btn = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
            login_btn.click()
            print("Submit button clicked")
        except:
            driver.execute_script("const buttons = document.querySelectorAll('button'); for (let btn of buttons) { const text = (btn.textContent || '').toLowerCase(); if (text.includes('login')) { btn.click(); break; } }")
            print("Login clicked via JS")
    
    # Wait for login to complete
    print("Waiting for login to complete...")
    for i in range(40):
        time.sleep(1)
        current_url = driver.current_url
        if "login" not in current_url.lower():
            print(f"Redirected to: {current_url}")
            break
        if i % 10 == 0:
            print(f"Still waiting... ({i}s)")
    
    time.sleep(3)
    print(f"Final URL: {driver.current_url}")
    
    # Get localStorage
    ls_data = driver.execute_script("return JSON.stringify(localStorage)")
    ls_data = json.loads(ls_data) if ls_data else {}
    print(f"localStorage keys: {list(ls_data.keys())[:10]}")
    
    if "account_token" in ls_data:
        token = ls_data.get("account_token", "")
        print(f"SUCCESS! account_token found! Length: {len(token)}")
        
        Path("/root/valuescan/signal_monitor/valuescan_localstorage.json").write_text(
            json.dumps(ls_data, indent=2), encoding="utf-8"
        )
        print("Token saved to valuescan_localstorage.json")
        success = True
    else:
        print("FAILED: account_token NOT found")
        
except Exception as e:
    import traceback
    print(f"Error: {e}")
    traceback.print_exc()
finally:
    if driver:
        try:
            driver.quit()
        except:
            pass
    
    print("Restarting signal monitor...")
    subprocess.run(["systemctl", "start", "valuescan-signal"], timeout=30)
    
    if success:
        print("\n=== LOGIN SUCCESSFUL ===")
    else:
        print("\n=== LOGIN FAILED ===")
'''
    
    # Write script to VPS
    sftp = ssh.open_sftp()
    with sftp.file('/tmp/test_login_selenium.py', 'w') as f:
        f.write(test_code)
    sftp.close()
    
    # Run script
    stdin, stdout, stderr = ssh.exec_command('python3.9 /tmp/test_login_selenium.py 2>&1', timeout=180)
    print(stdout.read().decode())
    print(stderr.read().decode())
    ssh.close()

if __name__ == "__main__":
    main()
