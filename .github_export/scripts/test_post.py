#!/usr/bin/env python3
"""Test POST to AI summary API."""

import requests

url = "https://cornna.abrdns.com/api/valuescan/ai-summary/config"

# POST to disable
print("POST disable:")
r = requests.post(url, json={"config": {"enabled": False}}, timeout=10)
print(f"Status: {r.status_code}")
print(f"Response: {r.text}")

# GET to verify
print("\nGET verify:")
r = requests.get(url, timeout=10)
print(f"Status: {r.status_code}")
print(f"Response: {r.text}")

# POST to enable
print("\nPOST enable:")
r = requests.post(url, json={"config": {"enabled": True}}, timeout=10)
print(f"Status: {r.status_code}")
print(f"Response: {r.text}")

# GET to verify
print("\nGET final:")
r = requests.get(url, timeout=10)
print(f"Status: {r.status_code}")
print(f"Response: {r.text}")
