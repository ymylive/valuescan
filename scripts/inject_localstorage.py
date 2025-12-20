#!/usr/bin/env python3
"""将 localStorage 注入到 Chrome profile"""
import json
import os

# 读取 localStorage 数据
ls_file = "/opt/valuescan/signal_monitor/valuescan_localstorage.json"
with open(ls_file, 'r') as f:
    ls_data = json.load(f)

# 提取 token
account_token = ls_data.get('account_token', '')
refresh_token = ls_data.get('refresh_token', '')

print(f"account_token: {account_token[:50]}...")
print(f"refresh_token: {refresh_token[:50]}...")

# 创建注入脚本，在 Chrome 启动后注入 localStorage
inject_script = f'''
// 注入 localStorage
localStorage.setItem('account_token', '{account_token}');
localStorage.setItem('refresh_token', '{refresh_token}');
localStorage.setItem('language', 'en-US');
console.log('localStorage injected!');
'''

# 保存注入脚本
with open('/opt/valuescan/signal_monitor/inject_storage.js', 'w') as f:
    f.write(inject_script)

print("✅ 注入脚本已创建: inject_storage.js")
