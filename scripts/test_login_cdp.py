#!/usr/bin/env python3
"""Login test using direct CDP connection"""
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
import subprocess
import tempfile
import shutil
import socket
from pathlib import Path

email = "ymy_live@outlook.com"
pwd = "Qq159741."

# Stop services
print("Stopping services...")
for svc in ["valuescan-signal", "valuescan-api", "valuescan-keepalive"]:
    subprocess.run(["systemctl", "stop", svc], capture_output=True, timeout=10)

subprocess.run(["pkill", "-9", "chromium"], capture_output=True)
subprocess.run(["pkill", "-9", "chrome"], capture_output=True)
time.sleep(2)

# Find free port
def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]

port = find_free_port()
print(f"Using port: {port}")

profile_dir = tempfile.mkdtemp(prefix="vs_login_")
print(f"Profile: {profile_dir}")

# Start chromium with remote debugging
cmd = [
    "/usr/bin/chromium-browser",
    "--headless=new",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--disable-extensions",
    "--disable-background-networking",
    "--window-size=1024,768",
    f"--remote-debugging-port={port}",
    "--remote-allow-origins=*",
    f"--user-data-dir={profile_dir}",
    "https://www.valuescan.io/login",
]

process = None
success = False
try:
    print("Starting chromium...")
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Wait for browser to start
    time.sleep(15)
    
    # Check if process is still running
    if process.poll() is not None:
        print(f"Browser exited with code: {process.returncode}")
        stdout, stderr = process.communicate()
        print(f"STDOUT: {stdout.decode()[:500]}")
        print(f"STDERR: {stderr.decode()[:500]}")
    else:
        print("Browser is running!")
        
        # Connect via CDP
        import websocket
        import requests
        
        # Get websocket URL
        try:
            resp = requests.get(f"http://127.0.0.1:{port}/json", timeout=10)
            targets = resp.json()
            print(f"Found {len(targets)} targets")
            
            ws_url = None
            for t in targets:
                if t.get("type") == "page":
                    ws_url = t.get("webSocketDebuggerUrl")
                    break
            
            if ws_url:
                print(f"Connecting to: {ws_url}")
                ws = websocket.create_connection(ws_url, timeout=30)
                
                # Get current URL
                ws.send(json.dumps({"id": 1, "method": "Runtime.evaluate", "params": {"expression": "window.location.href"}}))
                result = json.loads(ws.recv())
                url = result.get("result", {}).get("result", {}).get("value", "")
                print(f"Current URL: {url}")
                
                # Fill email
                js = f"(() => {{ const inputs = document.querySelectorAll('input'); for (let inp of inputs) {{ const ph = (inp.placeholder || '').toLowerCase(); if (ph.includes('email')) {{ inp.value = '{email}'; inp.dispatchEvent(new Event('input', {{ bubbles: true }})); return 'ok'; }} }} return 'not_found'; }})()"
                ws.send(json.dumps({"id": 2, "method": "Runtime.evaluate", "params": {"expression": js}}))
                result = json.loads(ws.recv())
                print(f"Email: {result.get('result', {}).get('result', {}).get('value', 'error')}")
                
                time.sleep(0.5)
                
                # Fill password
                js = f"(() => {{ const p = document.querySelector('input[type=\\"password\\"]'); if (p) {{ p.value = '{pwd}'; p.dispatchEvent(new Event('input', {{ bubbles: true }})); return 'ok'; }} return 'not_found'; }})()"
                ws.send(json.dumps({"id": 3, "method": "Runtime.evaluate", "params": {"expression": js}}))
                result = json.loads(ws.recv())
                print(f"Password: {result.get('result', {}).get('result', {}).get('value', 'error')}")
                
                time.sleep(0.5)
                
                # Click login
                js = "(() => { const btns = document.querySelectorAll('button'); for (let btn of btns) { const txt = (btn.textContent || '').toLowerCase(); if (txt.includes('login')) { btn.click(); return 'clicked'; } } return 'not_found'; })()"
                ws.send(json.dumps({"id": 4, "method": "Runtime.evaluate", "params": {"expression": js}}))
                result = json.loads(ws.recv())
                print(f"Click: {result.get('result', {}).get('result', {}).get('value', 'error')}")
                
                # Wait for redirect
                print("Waiting for login...")
                for i in range(45):
                    time.sleep(1)
                    ws.send(json.dumps({"id": 100+i, "method": "Runtime.evaluate", "params": {"expression": "window.location.href"}}))
                    result = json.loads(ws.recv())
                    url = result.get("result", {}).get("result", {}).get("value", "")
                    if "login" not in url.lower():
                        print(f"Redirected: {url}")
                        break
                    if i % 10 == 0:
                        print(f"Waiting... ({i}s)")
                
                time.sleep(3)
                
                # Get localStorage
                ws.send(json.dumps({"id": 200, "method": "Runtime.evaluate", "params": {"expression": "JSON.stringify(localStorage)"}}))
                result = json.loads(ws.recv())
                ls_str = result.get("result", {}).get("result", {}).get("value", "{}")
                ls_data = json.loads(ls_str)
                print(f"Keys: {list(ls_data.keys())[:5]}")
                
                if "account_token" in ls_data:
                    print(f"SUCCESS! Token length: {len(ls_data['account_token'])}")
                    Path("/root/valuescan/signal_monitor/valuescan_localstorage.json").write_text(
                        json.dumps(ls_data, indent=2), encoding="utf-8"
                    )
                    success = True
                else:
                    print("FAILED: No token")
                
                ws.close()
            else:
                print("No page target found")
        except Exception as e:
            print(f"CDP error: {e}")
            import traceback
            traceback.print_exc()

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    if process:
        process.terminate()
        try:
            process.wait(timeout=5)
        except:
            process.kill()
    
    shutil.rmtree(profile_dir, ignore_errors=True)
    
    print("\\nRestarting services...")
    for svc in ["valuescan-api", "valuescan-signal", "valuescan-keepalive"]:
        subprocess.run(["systemctl", "start", svc], capture_output=True, timeout=10)
    
    if success:
        print("\\n=== LOGIN SUCCESSFUL ===")
    else:
        print("\\n=== LOGIN FAILED ===")
'''
    
    # Write script to VPS
    sftp = ssh.open_sftp()
    with sftp.file('/tmp/test_login_cdp.py', 'w') as f:
        f.write(test_code)
    sftp.close()
    
    # Install websocket-client if needed
    ssh.exec_command('pip3.9 install websocket-client requests 2>&1', timeout=60)
    
    # Run script
    stdin, stdout, stderr = ssh.exec_command('python3.9 /tmp/test_login_cdp.py 2>&1', timeout=180)
    print(stdout.read().decode())
    print(stderr.read().decode())
    ssh.close()

if __name__ == "__main__":
    main()
