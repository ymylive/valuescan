#!/usr/bin/env python3
import json, websocket, subprocess

# Get current page ID
result = subprocess.run(['curl', '-s', 'http://127.0.0.1:9222/json'], capture_output=True, text=True)
pages = json.loads(result.stdout)
page_id = pages[0]['id']
print(f"Page: {pages[0]['url']}")

ws = websocket.create_connection(f"ws://127.0.0.1:9222/devtools/page/{page_id}", timeout=10)
ws.send(json.dumps({"id":1,"method":"Runtime.evaluate","params":{"expression":"JSON.stringify({token:localStorage.getItem('account_token'),refresh:localStorage.getItem('refresh_token')})"}}))
r = json.loads(ws.recv())
data = json.loads(r["result"]["result"].get("value","{}"))
ws.close()

if data.get('token'):
    print("LOGIN STATUS: LOGGED IN ✅")
    print(f"Token: {data['token'][:50]}...")
else:
    print("LOGIN STATUS: NOT LOGGED IN ❌")
    print("Need to inject localStorage tokens")
