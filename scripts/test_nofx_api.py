#!/usr/bin/env python3
"""测试 NOFX API"""
import requests

url = "http://nofxaios.com:30006/api/coin/BTC?include=netflow,oi,price&auth=cm_568c67eae410d912c54c"
try:
    resp = requests.get(url, timeout=10)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text[:500]}")
except Exception as e:
    print(f"Error: {e}")
