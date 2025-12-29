#!/usr/bin/env python3
"""Test AI API connectivity"""
import requests
import json
import sys
from pathlib import Path

# 直接读取 AI Signal 配置文件
config_path = Path('/root/valuescan/signal_monitor/ai_signal_config.json')
if config_path.exists():
    with open(config_path) as f:
        config = json.load(f)
else:
    config = {}

print("Config:", json.dumps(config, indent=2, ensure_ascii=False))

api_url = config.get('api_url', 'https://chat.cornna.xyz/gemini/v1/chat/completions')
api_key = config.get('api_key', '')
model = config.get('model', 'gemini-2.0-flash-exp')

print(f"\nAPI URL: {api_url}")
print(f"Model: {model}")
print(f"API Key: {'Set (' + api_key[:10] + '...)' if api_key else 'Not set'}")

if not api_key:
    print("ERROR: No API key configured!")
    sys.exit(1)

# 测试 API 调用
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}"
}

payload = {
    "model": model,
    "messages": [
        {"role": "user", "content": "Say 'Hello World' in Chinese, just the translation."}
    ],
    "max_tokens": 100
}

print("\nTesting AI API call...")
try:
    resp = requests.post(api_url, headers=headers, json=payload, timeout=60)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text[:500]}")
except Exception as e:
    print(f"Error: {e}")
