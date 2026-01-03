#!/usr/bin/env python3
"""检查浏览器登录状态"""
import json
import websocket

# 连接到 Chrome DevTools
ws_url = "ws://127.0.0.1:9222/devtools/page/136BBB08D3FC0BA969534BFF67A131C6"

try:
    ws = websocket.create_connection(ws_url, timeout=10)
    
    # 执行 JavaScript 获取 localStorage
    cmd = {
        "id": 1,
        "method": "Runtime.evaluate",
        "params": {
            "expression": "JSON.stringify({account_token: localStorage.getItem('account_token'), url: location.href, hasSignals: document.querySelectorAll('[class*=signal]').length})"
        }
    }
    ws.send(json.dumps(cmd))
    result = json.loads(ws.recv())
    
    if 'result' in result and 'result' in result['result']:
        value = result['result']['result'].get('value', '{}')
        data = json.loads(value)
        print("Current URL:", data.get('url', 'unknown'))
        token = data.get('account_token')
        if token:
            print("Login Status: LOGGED IN ✅")
            print("Token:", token[:50] + "...")
        else:
            print("Login Status: NOT LOGGED IN ❌")
        print("Signal elements found:", data.get('hasSignals', 0))
    else:
        print("Error:", result)
    
    ws.close()
except Exception as e:
    print(f"Error: {e}")
