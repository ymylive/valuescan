#!/usr/bin/env python3
"""Minimal login test - stops ALL services first to maximize memory"""
import os
import paramiko

def main():
    password = os.environ.get('VALUESCAN_VPS_PASSWORD')
    if not password:
        print("Missing VALUESCAN_VPS_PASSWORD env var")
        return
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('82.158.88.34', username='root', password=password, timeout=30)
    
    # Upload and run test script - use base64 to avoid escaping issues
    test_code = '''
import time
import json
import subprocess
import tempfile
import shutil
from pathlib import Path

email = "ymy_live@outlook.com"
pwd = "Qq159741."

# Stop ALL services to free maximum memory
print("Stopping all services to free memory...")
services = ["valuescan-signal", "valuescan-trader", "valuescan-api", "valuescan-keepalive", "valuescan-token-refresher", "proxy-checker"]
for svc in services:
    try:
        subprocess.run(["systemctl", "stop", svc], timeout=10, capture_output=True)
    except:
        pass

time.sleep(2)

# Kill ALL chromium processes
subprocess.run(["pkill", "-9", "chromium"], capture_output=True)
subprocess.run(["pkill", "-9", "chrome"], capture_output=True)
time.sleep(2)

# Check memory
result = subprocess.run(["free", "-m"], capture_output=True, text=True)
print(f"Memory status:\\n{result.stdout}")

# Create fresh profile
profile_dir = tempfile.mkdtemp(prefix="vs_login_")
print(f"Using profile: {profile_dir}")

from DrissionPage import ChromiumOptions, ChromiumPage

options = ChromiumOptions()
options.headless(True)
options.set_argument("--no-sandbox")
options.set_argument("--disable-dev-shm-usage")
options.set_argument("--disable-gpu")
options.set_argument("--disable-software-rasterizer")
options.set_argument("--disable-extensions")
options.set_argument("--disable-background-networking")
options.set_argument("--disable-sync")
options.set_argument("--disable-translate")
options.set_argument("--disable-default-apps")
options.set_argument("--no-first-run")
options.set_argument("--single-process")
options.set_argument("--window-size=1024,768")
options.set_argument("--js-flags=--max-old-space-size=128")
options.set_browser_path("/usr/bin/chromium-browser")
options.set_user_data_path(profile_dir)

page = None
success = False
try:
    print("Launching browser...")
    page = ChromiumPage(addr_or_opts=options)
    print("Browser launched!")
    
    print("Navigating to login page...")
    page.get("https://www.valuescan.io/login")
    
    print("Waiting for page to load...")
    time.sleep(12)
    
    url = page.url
    print(f"Current URL: {url}")
    
    if "login" not in url.lower():
        print("Not on login page, checking if already logged in...")
        try:
            ls = page.run_js("JSON.stringify(localStorage)", as_expr=True)
            ls_data = json.loads(ls) if ls else {}
            if "account_token" in ls_data:
                print("Already logged in!")
                success = True
        except:
            pass
    
    if not success:
        print("Filling login form...")
        
        # Fill email
        js_email = "(() => { const inputs = document.querySelectorAll('input'); for (let inp of inputs) { const ph = (inp.placeholder || '').toLowerCase(); if (ph.includes('email')) { inp.value = '" + email + "'; inp.dispatchEvent(new Event('input', { bubbles: true })); return 'ok'; } } return 'not_found'; })()"
        result = page.run_js(js_email, as_expr=True)
        print(f"Email: {result}")
        
        time.sleep(0.5)
        
        # Fill password
        js_pwd = "(() => { const p = document.querySelector('input[type=\\"password\\"]'); if (p) { p.value = '" + pwd + "'; p.dispatchEvent(new Event('input', { bubbles: true })); return 'ok'; } return 'not_found'; })()"
        result = page.run_js(js_pwd, as_expr=True)
        print(f"Password: {result}")
        
        time.sleep(0.5)
        
        # Click login
        js_click = "(() => { const btns = document.querySelectorAll('button'); for (let btn of btns) { const txt = (btn.textContent || '').toLowerCase(); if (txt.includes('login') || txt.includes('sign')) { btn.click(); return 'clicked'; } } const submit = document.querySelector('button[type=\\"submit\\"]'); if (submit) { submit.click(); return 'submit'; } return 'not_found'; })()"
        result = page.run_js(js_click, as_expr=True)
        print(f"Click: {result}")
        
        print("Waiting for login...")
        for i in range(45):
            time.sleep(1)
            try:
                url = page.url
                if "login" not in url.lower():
                    print(f"Redirected to: {url}")
                    break
            except:
                pass
            if i % 10 == 0:
                print(f"Waiting... ({i}s)")
        
        time.sleep(3)
        
        try:
            ls = page.run_js("JSON.stringify(localStorage)", as_expr=True)
            ls_data = json.loads(ls) if ls else {}
            print(f"Keys: {list(ls_data.keys())[:5]}")
            
            if "account_token" in ls_data:
                token = ls_data["account_token"]
                print(f"SUCCESS! Token length: {len(token)}")
                
                Path("/root/valuescan/signal_monitor/valuescan_localstorage.json").write_text(
                    json.dumps(ls_data, indent=2), encoding="utf-8"
                )
                print("Token saved!")
                success = True
            else:
                print("FAILED: No token found")
                print(f"Final URL: {page.url}")
        except Exception as e:
            print(f"Error: {e}")

except Exception as e:
    import traceback
    print(f"Error: {e}")
    traceback.print_exc()
finally:
    if page:
        try:
            page.quit()
        except:
            pass
    
    try:
        shutil.rmtree(profile_dir, ignore_errors=True)
    except:
        pass
    
    print("\\nRestarting services...")
    for svc in ["valuescan-api", "valuescan-signal", "valuescan-keepalive"]:
        try:
            subprocess.run(["systemctl", "start", svc], timeout=10, capture_output=True)
        except:
            pass
    
    if success:
        print("\\n=== LOGIN SUCCESSFUL ===")
    else:
        print("\\n=== LOGIN FAILED ===")
'''
    
    # Write script to VPS
    sftp = ssh.open_sftp()
    with sftp.file('/tmp/test_login_minimal.py', 'w') as f:
        f.write(test_code)
    sftp.close()
    
    # Run script
    stdin, stdout, stderr = ssh.exec_command('python3.9 /tmp/test_login_minimal.py 2>&1', timeout=180)
    print(stdout.read().decode())
    print(stderr.read().decode())
    ssh.close()

if __name__ == "__main__":
    main()
