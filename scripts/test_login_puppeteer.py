#!/usr/bin/env python3
"""Login test using pyppeteer (puppeteer for Python)"""
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
    
    # First install pyppeteer if needed
    print("Checking pyppeteer installation...")
    stdin, stdout, stderr = ssh.exec_command('pip3.9 show pyppeteer 2>&1', timeout=30)
    output = stdout.read().decode()
    if 'not found' in output.lower() or not output.strip():
        print("Installing pyppeteer...")
        stdin, stdout, stderr = ssh.exec_command('pip3.9 install pyppeteer 2>&1', timeout=120)
        print(stdout.read().decode())
    
    test_code = '''
import asyncio
import json
import subprocess
import tempfile
import shutil
from pathlib import Path

email = "ymy_live@outlook.com"
pwd = "Qq159741."

async def login():
    # Stop services
    print("Stopping services...")
    for svc in ["valuescan-signal", "valuescan-api", "valuescan-keepalive"]:
        subprocess.run(["systemctl", "stop", svc], capture_output=True, timeout=10)
    
    subprocess.run(["pkill", "-9", "chromium"], capture_output=True)
    subprocess.run(["pkill", "-9", "chrome"], capture_output=True)
    await asyncio.sleep(2)
    
    from pyppeteer import launch
    
    profile_dir = tempfile.mkdtemp(prefix="vs_login_")
    print(f"Profile: {profile_dir}")
    
    browser = None
    success = False
    try:
        browser = await launch(
            executablePath="/usr/bin/chromium-browser",
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-extensions",
                "--single-process",
                "--window-size=1024,768",
            ],
            userDataDir=profile_dir,
        )
        
        page = await browser.newPage()
        print("Browser launched!")
        
        await page.goto("https://www.valuescan.io/login", waitUntil="networkidle2", timeout=60000)
        print(f"URL: {page.url}")
        
        await asyncio.sleep(5)
        
        # Fill email
        await page.evaluate(f"() => {{ const inputs = document.querySelectorAll('input'); for (let inp of inputs) {{ const ph = (inp.placeholder || '').toLowerCase(); if (ph.includes('email')) {{ inp.value = '{email}'; inp.dispatchEvent(new Event('input', {{ bubbles: true }})); return; }} }} }}")
        print("Email filled")
        
        await asyncio.sleep(0.5)
        
        # Fill password
        await page.evaluate(f"() => {{ const p = document.querySelector('input[type=\\"password\\"]'); if (p) {{ p.value = '{pwd}'; p.dispatchEvent(new Event('input', {{ bubbles: true }})); }} }}")
        print("Password filled")
        
        await asyncio.sleep(0.5)
        
        # Click login
        await page.evaluate("() => { const btns = document.querySelectorAll('button'); for (let btn of btns) { const txt = (btn.textContent || '').toLowerCase(); if (txt.includes('login')) { btn.click(); return; } } }")
        print("Login clicked")
        
        # Wait for redirect
        for i in range(45):
            await asyncio.sleep(1)
            url = page.url
            if "login" not in url.lower():
                print(f"Redirected: {url}")
                break
            if i % 10 == 0:
                print(f"Waiting... ({i}s)")
        
        await asyncio.sleep(3)
        
        # Get localStorage
        ls = await page.evaluate("() => JSON.stringify(localStorage)")
        ls_data = json.loads(ls) if ls else {}
        print(f"Keys: {list(ls_data.keys())[:5]}")
        
        if "account_token" in ls_data:
            print(f"SUCCESS! Token length: {len(ls_data['account_token'])}")
            Path("/root/valuescan/signal_monitor/valuescan_localstorage.json").write_text(
                json.dumps(ls_data, indent=2), encoding="utf-8"
            )
            success = True
        else:
            print("FAILED: No token")
            
    except Exception as e:
        import traceback
        print(f"Error: {e}")
        traceback.print_exc()
    finally:
        if browser:
            await browser.close()
        shutil.rmtree(profile_dir, ignore_errors=True)
        
        print("Restarting services...")
        for svc in ["valuescan-api", "valuescan-signal", "valuescan-keepalive"]:
            subprocess.run(["systemctl", "start", svc], capture_output=True, timeout=10)
        
        if success:
            print("\\n=== LOGIN SUCCESSFUL ===")
        else:
            print("\\n=== LOGIN FAILED ===")

asyncio.get_event_loop().run_until_complete(login())
'''
    
    # Write script to VPS
    sftp = ssh.open_sftp()
    with sftp.file('/tmp/test_login_puppeteer.py', 'w') as f:
        f.write(test_code)
    sftp.close()
    
    # Run script
    stdin, stdout, stderr = ssh.exec_command('python3.9 /tmp/test_login_puppeteer.py 2>&1', timeout=180)
    print(stdout.read().decode())
    print(stderr.read().decode())
    ssh.close()

if __name__ == "__main__":
    main()
