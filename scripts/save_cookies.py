#!/usr/bin/env python3
"""直接从运行中的 Chrome 获取 cookies"""
import json
import os

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
except ImportError:
    print("安装 selenium...")
    os.system('pip install selenium')
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options

print("连接到已打开的浏览器...")

# 连接到已有的 Chrome 调试端口
options = Options()
options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")

try:
    driver = webdriver.Chrome(options=options)
    print(f"当前页面: {driver.current_url}")
    
    # 获取 cookies
    cookies = driver.get_cookies()
    
    cookies_file = os.path.join(os.path.dirname(__file__), 'valuescan_cookies.json')
    with open(cookies_file, 'w', encoding='utf-8') as f:
        json.dump(cookies, f, indent=2)
    
    print(f"\n✅ 已保存 {len(cookies)} 个 cookies 到: {cookies_file}")
    
    # 显示 valuescan 相关的 cookies
    vs_cookies = [c for c in cookies if 'valuescan' in c.get('domain', '')]
    print(f"其中 valuescan.io 的 cookies: {len(vs_cookies)} 个")
    for c in vs_cookies:
        print(f"  - {c['name']}")
        
except Exception as e:
    print(f"❌ 错误: {e}")
    print("\n如果浏览器已关闭，请重新运行 local_login.py")
