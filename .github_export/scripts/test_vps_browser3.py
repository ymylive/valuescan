#!/usr/bin/env python3
"""Test browser on VPS - find login button"""
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
    
    # Find buttons
    buttons = page.eles("css:button") or []
    print(f"Found {len(buttons)} button elements")
    
    for i, btn in enumerate(buttons[:10]):
        text = btn.text or ""
        t = btn.attr("type") or ""
        c = btn.attr("class") or ""
        print(f"  Button {i}: text={text[:30]}, type={t}, class={c[:50]}")
    
    # Try login button selectors
    login_selectors = [
        "xpath://button[contains(text(), \\"Login\\")]",
        "xpath://button[contains(text(), \\"登录\\")]",
        "xpath://button[contains(text(), \\"Sign\\")]",
        "xpath://button[@type=\\"submit\\"]",
        "css:button[type=\\"submit\\"]",
        "css:button.t-button--primary",
    ]
    
    print("\\nTrying login button selectors:")
    for sel in login_selectors:
        try:
            el = page.ele(sel, timeout=2)
            if el:
                txt = (el.text or "")[:30]
                print(f"  FOUND with {sel}: text={txt}")
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
