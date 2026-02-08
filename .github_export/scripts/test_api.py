#!/usr/bin/env python3
from binance.client import Client

api_key = "PbZaRLjAtZhiUXt1VjxvAt4eP4yz8cq08yTaYv2anVjJPXB5kd4fRremBHhk1D4k"
api_secret = "7mbAxjCLRit87SMfSuDVOh80B3wIU2cpoJVXgzHfT5faxmlaE3T3ADxgFXIdUIN8"

# Test with proxy
import os
os.environ['HTTP_PROXY'] = 'socks5://127.0.0.1:1080'
os.environ['HTTPS_PROXY'] = 'socks5://127.0.0.1:1080'

client = Client(api_key, api_secret, testnet=True, requests_params={
    'proxies': {
        'http': 'socks5://127.0.0.1:1080',
        'https': 'socks5://127.0.0.1:1080'
    }
})
client.FUTURES_URL = 'https://testnet.binancefuture.com/fapi'

try:
    balance = client.futures_account_balance()
    print("Success!")
    for b in balance:
        if float(b.get('balance', 0)) > 0:
            print(f"  {b['asset']}: {b['balance']}")
except Exception as e:
    print(f"Error: {e}")
