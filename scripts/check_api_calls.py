#!/usr/bin/env python3
"""检查页面实际调用的 API"""
import json, subprocess, time

# Get page ID
result = subprocess.run(['curl', '-s', 'http://127.0.0.1:9222/json'], capture_output=True, text=True)
pages = json.loads(result.stdout)
page_id = pages[0]['id']
print(f"Page: {pages[0]['url']}")

import websocket
ws = websocket.create_connection(f"ws://127.0.0.1:9222/devtools/page/{page_id}", timeout=10)

# Enable network monitoring
ws.send(json.dumps({"id":1,"method":"Network.enable"}))
ws.recv()
print("Network monitoring enabled, refreshing page...")

# Refresh page
ws.send(json.dumps({"id":2,"method":"Page.reload"}))

# Listen for network requests for 10 seconds
print("Listening for API calls (10 seconds)...")
api_calls = []
start = time.time()
while time.time() - start < 10:
    try:
        ws.settimeout(1)
        msg = ws.recv()
        data = json.loads(msg)
        if data.get('method') == 'Network.requestWillBeSent':
            url = data.get('params', {}).get('request', {}).get('url', '')
            if 'api.valuescan.io' in url:
                api_calls.append(url)
                print(f"  API: {url}")
    except:
        pass

ws.close()
print(f"\nFound {len(api_calls)} API calls")
