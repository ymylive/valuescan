#!/usr/bin/env python3
"""
Login to ValueScan locally and upload token to VPS.
Updated version with better element detection.
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
    options.headless(False)  # Show browser
    options.set_argument("--no-sandbox")
    options.set_argument("--disable-dev-shm-usage")
    options.set_argument("--window-size=1400,900")
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
        print(f"Page title: {page.title}")
        
        # Try multiple selectors for email input
        email_selectors = [
            'css:input[type="email"]',
            'css:input[placeholder*="email" i]',
            'css:input[placeholder*="邮箱"]',
            'css:input[name="email"]',
            'css:input[id*="email" i]',
            'xpath://input[@type="text"][1]',
        ]
        
        email_input = None
        for sel in email_selectors:
            try:
                email_input = page.ele(sel, timeout=2)
                if email_input:
                    print(f"Found email input with: {sel}")
                    break
            except:
                continue
        
        if not email_input:
            # List all inputs for debugging
            print("\nAll inputs on page:")
            inputs = page.eles('css:input')
            for i, inp in enumerate(inputs):
                try:
                    print(f"  {i}: type={inp.attr('type')}, placeholder={inp.attr('placeholder')}, name={inp.attr('name')}")
                except:
                    pass
            
            # Try first text/email input
            for inp in inputs:
                try:
                    t = inp.attr('type') or ''
                    if t in ['text', 'email', '']:
                        email_input = inp
                        print(f"Using first text input")
                        break
                except:
                    continue
        
        if email_input:
            email_input.clear()
            email_input.input(email)
            print("Email entered")
            time.sleep(1)
        else:
            print("Email input not found!")
            input("Press Enter to continue after manual login...")
        
        # Find password input
        pwd_input = page.ele('css:input[type="password"]', timeout=5)
        if pwd_input:
            pwd_input.clear()
            pwd_input.input(password)
            print("Password entered")
            time.sleep(1)
        else:
            print("Password input not found!")
        
        # Find and click login button
        btn_selectors = [
            'xpath://button[contains(text(), "Login")]',
            'xpath://button[contains(text(), "登录")]',
            'xpath://button[contains(text(), "Sign")]',
            'css:button[type="submit"]',
            'css:form button',
        ]
        
        login_btn = None
        for sel in btn_selectors:
            try:
                login_btn = page.ele(sel, timeout=2)
                if login_btn:
                    print(f"Found login button with: {sel}")
                    break
            except:
                continue
        
        if login_btn:
            login_btn.click()
            print("Login button clicked")
        else:
            print("Login button not found - please click manually")
        
        # Wait for login to complete
        print("\nWaiting for login to complete...")
        print("If you see a captcha, please complete it manually.")
        print("The script will wait up to 60 seconds.\n")
        
        for i in range(60):
            time.sleep(1)
            url = page.url or ""
            if "login" not in url.lower():
                print(f"Redirected to: {url}")
                break
            if i % 10 == 0:
                print(f"Still on login page... ({i}s)")
        
        time.sleep(3)
        
        # Get localStorage
        try:
            js = "JSON.stringify(localStorage)"
            ls = page.run_js(js, as_expr=True)
            ls_data = json.loads(ls) if ls else {}
            print(f"\nlocalStorage keys: {list(ls_data.keys())}")
            
            if "account_token" in ls_data:
                token = ls_data["account_token"]
                print(f"\n✅ SUCCESS! Token found (length: {len(token)})")
            else:
                print("\n❌ No account_token found in localStorage")
                print("Please complete login manually if needed, then press Enter...")
                input()
                
                # Try again
                ls = page.run_js(js, as_expr=True)
                ls_data = json.loads(ls) if ls else {}
                if "account_token" in ls_data:
                    print(f"✅ Token found after manual login!")
                else:
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
    try:
        import paramiko
    except ImportError:
        import subprocess, sys
        subprocess.run([sys.executable, "-m", "pip", "install", "paramiko"], check=True)
        import paramiko
    
    password = os.environ.get('VALUESCAN_VPS_PASSWORD', 'Qq159741')
    
    print(f"\nConnecting to VPS...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('82.158.88.34', username='root', password=password, timeout=30)
    
    # Upload token file
    sftp = ssh.open_sftp()
    token_path = '/root/valuescan/signal_monitor/valuescan_localstorage.json'
    with sftp.file(token_path, 'w') as f:
        f.write(json.dumps(ls_data, indent=2, ensure_ascii=False))
    sftp.close()
    
    print(f"✅ Token uploaded to {token_path}")
    
    # Restart services
    print("Restarting services...")
    stdin, stdout, stderr = ssh.exec_command(
        'systemctl restart valuescan-signal valuescan-token-refresher && echo "Services restarted"'
    )
    print(stdout.read().decode())
    
    # Check status
    time.sleep(3)
    stdin, stdout, stderr = ssh.exec_command(
        'journalctl -u valuescan-signal -n 10 --no-pager'
    )
    print("\nRecent signal monitor logs:")
    print(stdout.read().decode())
    
    ssh.close()
    return True


def main():
    print("=" * 50)
    print("Local Login and Upload to VPS")
    print("=" * 50)
    print("\nThis will:")
    print("1. Open a browser window on your local machine")
    print("2. Navigate to ValueScan login page")
    print("3. Auto-fill credentials and login")
    print("4. Extract the token and upload to VPS")
    print("\nIf there's a captcha, please complete it manually.\n")
    
    ls_data = login_locally()
    
    if ls_data and "account_token" in ls_data:
        print("\n" + "=" * 50)
        print("Uploading to VPS...")
        print("=" * 50)
        if upload_to_vps(ls_data):
            print("\n" + "=" * 50)
            print("✅ SUCCESS!")
            print("Token uploaded and services restarted.")
            print("=" * 50)
        else:
            print("\n❌ Upload failed")
    else:
        print("\n❌ Login failed - no token obtained")


if __name__ == "__main__":
    main()
