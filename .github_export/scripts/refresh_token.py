#!/usr/bin/env python3
"""使用 refresh_token 刷新 account_token"""
import json
import requests

PROXIES = {'http': 'socks5://127.0.0.1:1080', 'https': 'socks5://127.0.0.1:1080'}

# 读取当前 token
with open('/opt/valuescan/signal_monitor/valuescan_localstorage.json', 'r') as f:
    ls_data = json.load(f)

refresh_token = ls_data.get('refresh_token', '')
print(f"Refresh token: {refresh_token[:50]}...")

# 尝试刷新 token
url = 'https://api.valuescan.io/api/account/refreshToken'
headers = {
    'Authorization': f'Bearer {refresh_token}',
    'Content-Type': 'application/json'
}

try:
    resp = requests.post(url, headers=headers, proxies=PROXIES, timeout=30)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text[:500]}")
    
    if resp.status_code == 200:
        data = resp.json()
        if data.get('code') == 200:
            new_token = data.get('data', {}).get('account_token') or data.get('data', {}).get('token')
            new_refresh = data.get('data', {}).get('refresh_token')
            
            if new_token:
                ls_data['account_token'] = new_token
                if new_refresh:
                    ls_data['refresh_token'] = new_refresh
                
                with open('/opt/valuescan/signal_monitor/valuescan_localstorage.json', 'w') as f:
                    json.dump(ls_data, f, indent=2)
                print("✅ Token 已刷新并保存!")
            else:
                print("❌ 响应中没有找到新 token")
        else:
            print(f"❌ API 返回错误: {data.get('msg')}")
except Exception as e:
    print(f"Error: {e}")
