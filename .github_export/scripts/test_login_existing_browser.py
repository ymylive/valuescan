#!/usr/bin/env python3
"""Login using the existing Chromium browser instance on VPS"""
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
    
    test_code = '''
import time
import json
import requests
import websocket
from pathlib import Path

email = "ymy_live@outlook.com"
pwd = "Qq159741."

def get_page_ws_url():
    """Get WebSocket URL for the first page target"""
    resp = requests.get("http://127.0.0.1:9222/json", timeout=10)
    targets = resp.json()
    for t in targets:
        if t.get("type") == "page":
            return t.get("webSocketDebuggerUrl")
    return None

def send_and_recv(ws, msg_id, method, params=None):
    """Send CDP command and receive response"""
    msg = {"id": msg_id, "method": method}
    if params:
        msg["params"] = params
    ws.send(json.dumps(msg))
    
    # Wait for response with matching id
    for _ in range(10):
        try:
            result = json.loads(ws.recv())
            if result.get("id") == msg_id:
                return result
        except websocket.WebSocketTimeoutException:
            continue
    return None

print("Connecting to existing browser on port 9222...")

try:
    ws_url = get_page_ws_url()
    if not ws_url:
        print("No page target found")
        print("\\n=== LOGIN FAILED ===")
        exit(1)
    
    print(f"Connecting to: {ws_url}")
    ws = websocket.create_connection(ws_url, timeout=30)
    
    # Navigate to login page
    print("Navigating to login page...")
    result = send_and_recv(ws, 1, "Page.navigate", {"url": "https://www.valuescan.io/login"})
    print(f"Navigate: {result}")
    
    # Wait for page to load
    print("Waiting for page to load...")
    time.sleep(10)
    
    # Reconnect after navigation (page may have changed)
    ws.close()
    time.sleep(2)
    
    ws_url = get_page_ws_url()
    if not ws_url:
        print("Lost connection to page")
        print("\\n=== LOGIN FAILED ===")
        exit(1)
    
    print(f"Reconnecting to: {ws_url}")
    ws = websocket.create_connection(ws_url, timeout=30)
    
    # Get current URL
    result = send_and_recv(ws, 2, "Runtime.evaluate", {"expression": "window.location.href"})
    url = result.get("result", {}).get("result", {}).get("value", "") if result else ""
    print(f"Current URL: {url}")
    
    # Fill email
    js = f"(() => {{ const inputs = document.querySelectorAll('input'); for (let inp of inputs) {{ const ph = (inp.placeholder || '').toLowerCase(); if (ph.includes('email')) {{ inp.value = '{email}'; inp.dispatchEvent(new Event('input', {{ bubbles: true }})); return 'ok'; }} }} return 'not_found'; }})()"
    result = send_and_recv(ws, 3, "Runtime.evaluate", {"expression": js})
    val = result.get("result", {}).get("result", {}).get("value", "error") if result else "error"
    print(f"Email: {val}")
    
    time.sleep(0.5)
    
    # Fill password
    js = f"(() => {{ const p = document.querySelector('input[type=\\"password\\"]'); if (p) {{ p.value = '{pwd}'; p.dispatchEvent(new Event('input', {{ bubbles: true }})); return 'ok'; }} return 'not_found'; }})()"
    result = send_and_recv(ws, 4, "Runtime.evaluate", {"expression": js})
    val = result.get("result", {}).get("result", {}).get("value", "error") if result else "error"
    print(f"Password: {val}")
    
    time.sleep(0.5)
    
    # Click login
    js = "(() => { const btns = document.querySelectorAll('button'); for (let btn of btns) { const txt = (btn.textContent || '').toLowerCase(); if (txt.includes('login')) { btn.click(); return 'clicked'; } } return 'not_found'; })()"
    result = send_and_recv(ws, 5, "Runtime.evaluate", {"expression": js})
    val = result.get("result", {}).get("result", {}).get("value", "error") if result else "error"
    print(f"Click: {val}")
    
    # Wait for redirect
    print("Waiting for login...")
    for i in range(45):
        time.sleep(1)
        result = send_and_recv(ws, 100+i, "Runtime.evaluate", {"expression": "window.location.href"})
        url = result.get("result", {}).get("result", {}).get("value", "") if result else ""
        if url and "login" not in url.lower():
            print(f"Redirected: {url}")
            break
        if i % 10 == 0:
            print(f"Waiting... ({i}s)")
    
    time.sleep(3)
    
    # Get localStorage
    result = send_and_recv(ws, 200, "Runtime.evaluate", {"expression": "JSON.stringify(localStorage)"})
    ls_str = result.get("result", {}).get("result", {}).get("value", "{}") if result else "{}"
    ls_data = json.loads(ls_str)
    print(f"Keys: {list(ls_data.keys())[:5]}")
    
    if "account_token" in ls_data:
        print(f"SUCCESS! Token length: {len(ls_data['account_token'])}")
        Path("/root/valuescan/signal_monitor/valuescan_localstorage.json").write_text(
            json.dumps(ls_data, indent=2), encoding="utf-8"
        )
        print("Token saved!")
        print("\\n=== LOGIN SUCCESSFUL ===")
    else:
        print("FAILED: No token")
        print("\\n=== LOGIN FAILED ===")
    
    ws.close()
        
except Exception as e:
    import traceback
    print(f"Error: {e}")
    traceback.print_exc()
    print("\\n=== LOGIN FAILED ===")
'''
    
    # Write script to VPS
    sftp = ssh.open_sftp()
    with sftp.file('/tmp/test_login_existing.py', 'w') as f:
        f.write(test_code)
    sftp.close()
    
    # Run script
    stdin, stdout, stderr = ssh.exec_command('python3.9 /tmp/test_login_existing.py 2>&1', timeout=180)
    print(stdout.read().decode())
    print(stderr.read().decode())
    ssh.close()

if __name__ == "__main__":
    main()
