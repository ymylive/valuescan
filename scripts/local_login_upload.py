#!/usr/bin/env python3
"""
Login to ValueScan locally and upload token to VPS.
This works around VPS memory limitations by doing browser login locally.
"""
import os
import json
import time
import tempfile
import shutil
from pathlib import Path

def login_locally():
    """Login using local browser and return localStorage data."""
    try:
        from DrissionPage import ChromiumOptions, ChromiumPage
    except ImportError:
        print("DrissionPage not installed. Install with: pip install DrissionPage")
        return None
    
    email = "ymy_live@outlook.com"
    password = "Qq159741."
    
    profile_dir = tempfile.mkdtemp(prefix="vs_login_")
    print(f"Using profile: {profile_dir}")
    
    options = ChromiumOptions()
    options.headless(False)  # Show browser for debugging
    options.set_argument("--no-sandbox")
    options.set_argument("--disable-dev-shm-usage")
    options.set_argument("--window-size=1280,720")
    options.set_user_data_path(profile_dir)
    
    page = None
    ls_data = None
    try:
        print("Launching browser...")
        page = ChromiumPage(addr_or_opts=options)
        
        print("Navigating to login page...")
        page.get("https://www.valuescan.io/login")
        time.sleep(5)
        
        print(f"Current URL: {page.url}")
        
        # Fill email
        email_input = page.ele('css:input[placeholder*="email" i]', timeout=10)
        if email_input:
            email_input.clear()
            email_input.input(email)
            print("Email entered")
        else:
            print("Email input not found!")
            return None
        
        time.sleep(1)
        
        # Fill password
        pwd_input = page.ele('css:input[type="password"]', timeout=10)
        if pwd_input:
            pwd_input.clear()
            pwd_input.input(password)
            print("Password entered")
        else:
            print("Password input not found!")
            return None
        
        time.sleep(1)
        
        # Click login
        login_btn = page.ele('xpath://button[contains(text(), "Login")]', timeout=5)
        if not login_btn:
            login_btn = page.ele('css:button[type="submit"]', timeout=3)
        if not login_btn:
            login_btn = page.ele('css:button', timeout=3)
        
        if login_btn:
            login_btn.click()
            print("Login button clicked")
        else:
            print("Login button not found!")
            return None
        
        # Wait for redirect
        print("Waiting for login to complete...")
        for i in range(45):
            time.sleep(1)
            url = page.url or ""
            if "login" not in url.lower():
                print(f"Redirected to: {url}")
                break
            if i % 10 == 0:
                print(f"Still waiting... ({i}s)")
        
        time.sleep(3)
        
        # Get localStorage
        try:
            js = "JSON.stringify(localStorage)"
            ls = page.run_js(js, as_expr=True)
            ls_data = json.loads(ls) if ls else {}
            print(f"localStorage keys: {list(ls_data.keys())[:10]}")
            
            if "account_token" in ls_data:
                token = ls_data["account_token"]
                print(f"SUCCESS! Token length: {len(token)}")
            else:
                print("FAILED: No token found")
                ls_data = None
        except Exception as e:
            print(f"Error getting localStorage: {e}")
            ls_data = None
            
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
        shutil.rmtree(profile_dir, ignore_errors=True)
    
    return ls_data


def upload_to_vps(ls_data):
    """Upload localStorage data to VPS."""
    import paramiko
    
    password = os.environ.get('VALUESCAN_VPS_PASSWORD')
    if not password:
        print("Missing VALUESCAN_VPS_PASSWORD env var")
        return False
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('82.158.88.34', username='root', password=password, timeout=30)
    
    # Upload token file
    sftp = ssh.open_sftp()
    token_path = '/root/valuescan/signal_monitor/valuescan_localstorage.json'
    with sftp.file(token_path, 'w') as f:
        f.write(json.dumps(ls_data, indent=2, ensure_ascii=False))
    sftp.close()
    
    print(f"Token uploaded to {token_path}")
    
    # Restart signal monitor
    stdin, stdout, stderr = ssh.exec_command('systemctl restart valuescan-signal && echo OK')
    print(stdout.read().decode())
    
    ssh.close()
    return True


def main():
    print("=== Local Login and Upload ===")
    print("This will login to ValueScan using your local browser")
    print("and upload the token to VPS.\n")
    
    ls_data = login_locally()
    
    if ls_data and "account_token" in ls_data:
        print("\n=== Uploading to VPS ===")
        if upload_to_vps(ls_data):
            print("\n=== SUCCESS ===")
            print("Token has been uploaded to VPS and signal monitor restarted.")
        else:
            print("\n=== UPLOAD FAILED ===")
    else:
        print("\n=== LOGIN FAILED ===")
        print("Could not get token from ValueScan.")


if __name__ == "__main__":
    main()
