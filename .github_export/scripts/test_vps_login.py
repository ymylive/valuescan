#!/usr/bin/env python3
"""Test actual login on VPS"""
import os
import sys
import paramiko

def main():
    password = os.environ.get('VALUESCAN_VPS_PASSWORD')
    if not password:
        print("Missing VALUESCAN_VPS_PASSWORD env var")
        return
    
    # Get ValueScan credentials from command line or env
    vs_email = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('VALUESCAN_EMAIL', '')
    vs_password = sys.argv[2] if len(sys.argv) > 2 else os.environ.get('VALUESCAN_PASSWORD', '')
    
    if not vs_email or not vs_password:
        print("Usage: python test_vps_login.py <email> <password>")
        print("Or set VALUESCAN_EMAIL and VALUESCAN_PASSWORD env vars")
        return
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('82.158.88.34', username='root', password=password)
    
    # Test login with DrissionPage
    test_script = f'''
import time
import json
from DrissionPage import ChromiumOptions, ChromiumPage

email = "{vs_email}"
password = "{vs_password}"

options = ChromiumOptions()
options.headless(True)
options.set_argument("--no-sandbox")
options.set_argument("--disable-dev-shm-usage")
options.set_argument("--disable-gpu")
options.set_argument("--window-size", "1920,1080")

page = None
try:
    page = ChromiumPage(addr_or_opts=options)
    page.get("https://www.valuescan.io/login")
    time.sleep(8)
    
    print("Initial URL:", page.url)
    
    # Find and fill email
    email_input = page.ele('css:input[placeholder*="email" i]', timeout=10)
    if email_input:
        print("Found email input")
        email_input.clear()
        email_input.input(email)
    else:
        print("Email input not found!")
        
    # Find and fill password
    pwd_input = page.ele('css:input[type="password"]', timeout=10)
    if pwd_input:
        print("Found password input")
        pwd_input.clear()
        pwd_input.input(password)
    else:
        print("Password input not found!")
    
    time.sleep(1)
    
    # Find and click login button
    login_btn = page.ele('xpath://button[contains(text(), "Login")]', timeout=5)
    if not login_btn:
        login_btn = page.ele('css:button', timeout=3)
    
    if login_btn:
        print("Found login button, clicking...")
        login_btn.click()
    else:
        print("Login button not found!")
    
    # Wait for login
    print("Waiting for login to complete...")
    for i in range(30):
        time.sleep(1)
        current_url = page.url or ""
        if "login" not in current_url.lower():
            print(f"Redirected to: {{current_url}}")
            break
        if i % 5 == 0:
            print(f"Still on login page... ({{i}}s)")
    
    time.sleep(3)
    print("Final URL:", page.url)
    
    # Check for error messages
    error_els = page.eles('css:.t-message--error') or []
    for el in error_els[:3]:
        print("Error message:", el.text)
    
    # Try to get localStorage
    try:
        js = "JSON.stringify(localStorage)"
        ls = page.run_js(js, as_expr=True)
        ls_data = json.loads(ls) if ls else {{}}
        print("localStorage keys:", list(ls_data.keys())[:10])
        if "account_token" in ls_data:
            print("account_token found! Length:", len(ls_data.get("account_token", "")))
        else:
            print("account_token NOT found in localStorage")
    except Exception as e:
        print("Error getting localStorage:", e)
        
except Exception as e:
    import traceback
    print(f"Error: {{e}}")
    traceback.print_exc()
finally:
    if page:
        try:
            page.quit()
        except:
            pass
'''
    
    stdin, stdout, stderr = ssh.exec_command(
        f'cd /root/valuescan/signal_monitor && python3.9 -c \'{test_script}\' 2>&1',
        timeout=180
    )
    print("Output:", stdout.read().decode())
    ssh.close()

if __name__ == "__main__":
    main()
