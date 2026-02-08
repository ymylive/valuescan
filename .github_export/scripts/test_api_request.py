#!/usr/bin/env python3
"""直接请求 getWarnMessage API"""
import json
import requests

# 读取 token
with open('/opt/valuescan/signal_monitor/valuescan_localstorage.json', 'r') as f:
    ls_data = json.load(f)

token = ls_data.get('account_token', '')
print(f"Token: {token[:50]}...")

# 设置代理
proxies = {
    'http': 'socks5://127.0.0.1:1080',
    'https': 'socks5://127.0.0.1:1080'
}

# 请求 API
headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}

url = 'https://api.valuescan.io/api/account/message/getWarnMessage'
print(f"Requesting: {url}")

try:
    resp = requests.get(url, headers=headers, proxies=proxies, timeout=30)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text[:2000]}")
except Exception as e:
    print(f"Error: {e}")
