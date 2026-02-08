#!/usr/bin/env python3
"""直接测试币安合约测试网API"""
import requests
import time
import hmac
import hashlib

api_key = "PbZaRLjAtZhiUXt1VjxvAt4eP4yz8cq08yTaYv2anVjJPXB5kd4fRremBHhk1D4k"
api_secret = "7mbAxjCLRit87SMfSuDVOh80B3wIU2cpoJVXgzHfT5faxmlaE3T3ADxgFXIdUIN8"
base_url = "https://testnet.binancefuture.com"

proxies = {
    'http': 'socks5://127.0.0.1:1080',
    'https': 'socks5://127.0.0.1:1080'
}

# Get server time first
try:
    resp = requests.get(f"{base_url}/fapi/v1/time", proxies=proxies, timeout=10)
    server_time = resp.json()['serverTime']
    local_time = int(time.time() * 1000)
    print(f"Server time: {server_time}")
    print(f"Local time:  {local_time}")
    print(f"Diff: {server_time - local_time}ms")
except Exception as e:
    print(f"Time check error: {e}")
    server_time = int(time.time() * 1000)

# Try to get account balance
timestamp = server_time
query_string = f"timestamp={timestamp}"
signature = hmac.new(api_secret.encode(), query_string.encode(), hashlib.sha256).hexdigest()

headers = {'X-MBX-APIKEY': api_key}
url = f"{base_url}/fapi/v2/balance?{query_string}&signature={signature}"

print(f"\nRequesting: {url[:80]}...")
try:
    resp = requests.get(url, headers=headers, proxies=proxies, timeout=10)
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print("Success!")
        for b in data:
            if float(b.get('balance', 0)) > 0:
                print(f"  {b['asset']}: {b['balance']}")
    else:
        print(f"Error: {resp.text}")
except Exception as e:
    print(f"Request error: {e}")
