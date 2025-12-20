#!/usr/bin/env python3
"""Test browser on VPS - find login form"""
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
    
    # Test DrissionPage browser
    test_script = '''
import time
from DrissionPage import ChromiumOptions, ChromiumPage

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
    time.sleep(10)
    
    print("URL:", page.url)
    
    # Try to find inputs with different selectors
    inputs = page.eles("css:input") or []
    print(f"Found {len(inputs)} input elements")
    
    for i, inp in enumerate(inputs[:10]):
        t = inp.attr("type") or ""
        p = inp.attr("placeholder") or ""
        c = inp.attr("class") or ""
        print(f"  Input {i}: type={t}, placeholder={p[:30]}, class={c[:50]}")
    
    # Try specific selectors
    email_selectors = [
        "xpath://input[@type=\\"email\\"]",
        "css:input[type=\\"email\\"]",
        "css:input[placeholder*=\\"email\\" i]",
        "css:input[placeholder*=\\"邮箱\\"]",
        "css:input[placeholder*=\\"账号\\"]",
        "css:input[placeholder*=\\"account\\"]",
    ]
    
    print("\\nTrying email selectors:")
    for sel in email_selectors:
        try:
            el = page.ele(sel, timeout=2)
            if el:
                print(f"  FOUND with {sel}")
                break
        except:
            print(f"  Not found: {sel}")
    
    # Try password selectors
    pwd_selectors = [
        "xpath://input[@type=\\"password\\"]",
        "css:input[type=\\"password\\"]",
    ]
    
    print("\\nTrying password selectors:")
    for sel in pwd_selectors:
        try:
            el = page.ele(sel, timeout=2)
            if el:
                print(f"  FOUND with {sel}")
                break
        except:
            print(f"  Not found: {sel}")
            
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
'''
    
    stdin, stdout, stderr = ssh.exec_command(f'cd /root/valuescan/signal_monitor && python3.9 -c \'{test_script}\' 2>&1', timeout=120)
    print("Output:", stdout.read().decode())
    ssh.close()

if __name__ == "__main__":
    main()
