#!/usr/bin/env python3
"""Direct login test on VPS - stops signal monitor first to free memory"""
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
    
    # Upload and run test script
    test_code = '''#!/usr/bin/env python3
import time
import json
import tempfile
import shutil
import subprocess
from pathlib import Path
from DrissionPage import ChromiumOptions, ChromiumPage

email = "ymy_live@outlook.com"
password = "Qq159741."

# Stop signal monitor to free memory
print("Stopping signal monitor to free memory...")
subprocess.run(["systemctl", "stop", "valuescan-signal"], timeout=30)
time.sleep(3)

# Kill any remaining chromium processes
subprocess.run(["pkill", "-9", "chromium"], capture_output=True)
subprocess.run(["pkill", "-9", "chrome"], capture_output=True)
time.sleep(2)

# Create fresh profile directory
profile_dir = tempfile.mkdtemp(prefix="vs_login_")
print(f"Using profile dir: {profile_dir}")

options = ChromiumOptions()
options.headless(True)
options.set_argument("--no-sandbox")
options.set_argument("--disable-dev-shm-usage")
options.set_argument("--disable-gpu")
options.set_argument("--disable-software-rasterizer")
options.set_argument("--disable-extensions")
options.set_argument("--window-size", "1280,720")
options.set_argument("--js-flags", "--max-old-space-size=256")
options.set_browser_path("/usr/bin/chromium-browser")
options.set_user_data_path(profile_dir)

page = None
success = False
try:
    page = ChromiumPage(addr_or_opts=options)
    print("Browser launched successfully")
    
    page.get("https://www.valuescan.io/login")
    print("Navigated to login page")
    
    # Wait for page to fully load
    time.sleep(8)
    print(f"Current URL: {page.url}")
    
    # Use JavaScript to fill the form directly
    print("Filling form via JavaScript...")
    
    # Wait for React to render
    for i in range(20):
        try:
            result = page.run_js("document.querySelectorAll('input').length", as_expr=True)
            if result and int(result) >= 2:
                print(f"Found {result} inputs")
                break
        except:
            pass
        time.sleep(1)
    
    # Fill email via JS
    try:
        js_fill_email = f"""
        (() => {{
            const inputs = document.querySelectorAll('input');
            for (let inp of inputs) {{
                const ph = (inp.placeholder || '').toLowerCase();
                const t = (inp.type || '').toLowerCase();
                if (ph.includes('email') || t === 'email') {{
                    inp.focus();
                    inp.value = '{email}';
                    inp.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    inp.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    return 'email_filled';
                }}
            }}
            return 'email_not_found';
        }})()
        """
        result = page.run_js(js_fill_email, as_expr=True)
        print(f"Email fill result: {result}")
    except Exception as e:
        print(f"Email fill error: {e}")
    
    time.sleep(1)
    
    # Fill password via JS
    try:
        js_fill_pwd = f"""
        (() => {{
            const pwd = document.querySelector('input[type="password"]');
            if (pwd) {{
                pwd.focus();
                pwd.value = '{password}';
                pwd.dispatchEvent(new Event('input', {{ bubbles: true }}));
                pwd.dispatchEvent(new Event('change', {{ bubbles: true }}));
                return 'password_filled';
            }}
            return 'password_not_found';
        }})()
        """
        result = page.run_js(js_fill_pwd, as_expr=True)
        print(f"Password fill result: {result}")
    except Exception as e:
        print(f"Password fill error: {e}")
    
    time.sleep(1)
    
    # Click login button via JS
    try:
        js_click_login = """
        (() => {
            const buttons = document.querySelectorAll('button');
            for (let btn of buttons) {
                const text = (btn.textContent || '').toLowerCase();
                if (text.includes('login') || text.includes('sign in') || text.includes('登录')) {
                    btn.click();
                    return 'clicked';
                }
            }
            const submit = document.querySelector('button[type="submit"]');
            if (submit) {
                submit.click();
                return 'clicked_submit';
            }
            return 'button_not_found';
        })()
        """
        result = page.run_js(js_click_login, as_expr=True)
        print(f"Login click result: {result}")
    except Exception as e:
        print(f"Login click error: {e}")
    
    # Wait for login to complete
    print("Waiting for login to complete...")
    for i in range(40):
        time.sleep(1)
        try:
            current_url = page.url or ""
            if "login" not in current_url.lower():
                print(f"Redirected to: {current_url}")
                break
        except:
            pass
        if i % 10 == 0:
            print(f"Still waiting... ({i}s)")
    
    time.sleep(3)
    
    # Check for token
    try:
        js = "JSON.stringify(localStorage)"
        ls = page.run_js(js, as_expr=True)
        ls_data = json.loads(ls) if ls else {}
        print(f"localStorage keys: {list(ls_data.keys())[:10]}")
        if "account_token" in ls_data:
            token = ls_data.get("account_token", "")
            print(f"SUCCESS! account_token found! Length: {len(token)}")
            
            # Save to file
            Path("/root/valuescan/signal_monitor/valuescan_localstorage.json").write_text(
                json.dumps(ls_data, indent=2), encoding="utf-8"
            )
            print("Token saved to valuescan_localstorage.json")
            success = True
        else:
            print("FAILED: account_token NOT found")
            print(f"Final URL: {page.url}")
    except Exception as e:
        print(f"Error getting localStorage: {e}")
        
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
    # Cleanup profile
    try:
        shutil.rmtree(profile_dir, ignore_errors=True)
    except:
        pass
    
    # Restart signal monitor
    print("Restarting signal monitor...")
    subprocess.run(["systemctl", "start", "valuescan-signal"], timeout=30)
    
    if success:
        print("\\n=== LOGIN SUCCESSFUL ===")
    else:
        print("\\n=== LOGIN FAILED ===")
'''
    
    # Write script to VPS
    sftp = ssh.open_sftp()
    with sftp.file('/tmp/test_login.py', 'w') as f:
        f.write(test_code)
    sftp.close()
    
    # Run script
    stdin, stdout, stderr = ssh.exec_command('python3.9 /tmp/test_login.py 2>&1', timeout=180)
    print(stdout.read().decode())
    print(stderr.read().decode())
    ssh.close()

if __name__ == "__main__":
    main()
