#!/usr/bin/env python3
"""测试不同的测试网端点"""
from binance.client import Client
from binance.um_futures import UMFutures

api_key = "PbZaRLjAtZhiUXt1VjxvAt4eP4yz8cq08yTaYv2anVjJPXB5kd4fRremBHhk1D4k"
api_secret = "7mbAxjCLRit87SMfSuDVOh80B3wIU2cpoJVXgzHfT5faxmlaE3T3ADxgFXIdUIN8"

proxies = {
    'http': 'socks5://127.0.0.1:1080',
    'https': 'socks5://127.0.0.1:1080'
}

print("Testing with UMFutures (testnet)...")
try:
    um_client = UMFutures(
        key=api_key, 
        secret=api_secret,
        base_url="https://testnet.binancefuture.com",
        proxies=proxies
    )
    balance = um_client.balance()
    print("Success!")
    for b in balance:
        if float(b.get('balance', 0)) > 0:
            print(f"  {b['asset']}: {b['balance']}")
except Exception as e:
    print(f"UMFutures Error: {e}")

print("\nTesting with regular Client...")
try:
    client = Client(api_key, api_secret, testnet=True, requests_params={'proxies': proxies})
    # Try spot testnet
    account = client.get_account()
    print("Spot testnet success!")
except Exception as e:
    print(f"Spot Error: {e}")
