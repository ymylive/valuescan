#!/usr/bin/env python3
"""监听浏览器的 API 请求"""
import json, subprocess, time, websocket

# Get page ID
result = subprocess.run(['curl', '-s', 'http://127.0.0.1:9222/json'], capture_output=True, text=True)
pages = json.loads(result.stdout)
page_id = pages[0]['id']
print(f"Page: {pages[0]['url']}")

ws = websocket.create_connection(f"ws://127.0.0.1:9222/devtools/page/{page_id}", timeout=60)

# Enable network monitoring
ws.send(json.dumps({"id":1,"method":"Network.enable"}))
ws.recv()
print("Monitoring API calls for 30 seconds...")

api_calls = []
start = time.time()
while time.time() - start < 30:
    try:
        ws.settimeout(1)
        msg = ws.recv()
        data = json.loads(msg)
        if data.get('method') == 'Network.requestWillBeSent':
            url = data.get('params', {}).get('request', {}).get('url', '')
            if 'api.valuescan.io' in url:
                api_calls.append(url)
                print(f"  [{time.strftime('%H:%M:%S')}] {url}")
    except websocket.WebSocketTimeoutException:
        pass
    except Exception as e:
        print(f"Error: {e}")
        break

ws.close()
print(f"\nTotal: {len(api_calls)} API calls in 30 seconds")
if 'getWarnMessage' in str(api_calls):
    print("✅ getWarnMessage was called!")
else:
    print("❌ getWarnMessage was NOT called")
