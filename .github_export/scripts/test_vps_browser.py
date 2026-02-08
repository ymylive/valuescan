#!/usr/bin/env python3
"""Test browser on VPS"""
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
    print("Title:", page.title)
    
    # Get page HTML
    html = page.html[:2000] if page.html else "No HTML"
    print("HTML preview:", html)
    
    # Try to find inputs
    inputs = page.eles("css:input") or []
    print(f"Found {len(inputs)} input elements")
    for i, inp in enumerate(inputs[:5]):
        print(f"  Input {i}: type={inp.attr('type')}, placeholder={inp.attr('placeholder')}")
        
except Exception as e:
    print(f"Error: {e}")
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
