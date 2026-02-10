#!/usr/bin/env python3
"""注入 localStorage tokens 并刷新页面"""
import json, websocket, subprocess

# 读取保存的 tokens
with open('/opt/valuescan/signal_monitor/valuescan_localstorage.json', 'r') as f:
    ls_data = json.load(f)

account_token = ls_data.get('account_token', '')
refresh_token = ls_data.get('refresh_token', '')

if not account_token:
    print("ERROR: No account_token found!")
    exit(1)

print(f"Token to inject: {account_token[:50]}...")

# Get current page ID
result = subprocess.run(['curl', '-s', 'http://127.0.0.1:9222/json'], capture_output=True, text=True)
pages = json.loads(result.stdout)
page_id = pages[0]['id']
print(f"Page ID: {page_id}")

ws = websocket.create_connection(f"ws://127.0.0.1:9222/devtools/page/{page_id}", timeout=10)

# Inject localStorage
inject_js = f"""
localStorage.setItem('account_token', '{account_token}');
localStorage.setItem('refresh_token', '{refresh_token}');
localStorage.setItem('language', 'en-US');
'injected'
"""
ws.send(json.dumps({"id":1,"method":"Runtime.evaluate","params":{"expression": inject_js}}))
r = json.loads(ws.recv())
print("Inject result:", r.get("result", {}).get("result", {}).get("value", "unknown"))

# Refresh page
ws.send(json.dumps({"id":2,"method":"Page.reload"}))
ws.recv()
print("Page refreshed!")

ws.close()

import time
time.sleep(3)

# Verify
result = subprocess.run(['curl', '-s', 'http://127.0.0.1:9222/json'], capture_output=True, text=True)
pages = json.loads(result.stdout)
page_id = pages[0]['id']

ws = websocket.create_connection(f"ws://127.0.0.1:9222/devtools/page/{page_id}", timeout=10)
ws.send(json.dumps({"id":1,"method":"Runtime.evaluate","params":{"expression":"localStorage.getItem('account_token')"}}))
r = json.loads(ws.recv())
token = r.get("result", {}).get("result", {}).get("value")
ws.close()

if token:
    print("✅ Token verified in localStorage!")
else:
    print("❌ Token not found after inject")
