#!/usr/bin/env python3
"""
自动登录 ValueScan 并获取 token
使用 DrissionPage 控制 Chrome
"""
import os
import sys
import json
import time

try:
    from DrissionPage import ChromiumPage, ChromiumOptions
except ImportError:
    print("Installing DrissionPage...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "DrissionPage"], check=True)
    from DrissionPage import ChromiumPage, ChromiumOptions

# 登录信息
EMAIL = "ymy_live@outlook.com"
PASSWORD = "Qq159741."

def login_and_get_token():
    print("启动 Chrome...")
    
    # 配置 Chrome
    co = ChromiumOptions()
    co.set_argument('--start-maximized')
    
    # 创建页面
    page = ChromiumPage(co)
    
    try:
        # 访问 ValueScan 登录页面
        print("访问 ValueScan...")
        page.get('https://www.valuescan.io/')
        time.sleep(3)
        
        # 检查是否已登录
        print("检查登录状态...")
        
        # 尝试找到登录按钮
        login_btn = page.ele('text:登录', timeout=5)
        if not login_btn:
            login_btn = page.ele('text:Login', timeout=3)
        if not login_btn:
            login_btn = page.ele('text:Sign in', timeout=3)
        
        if login_btn:
            print("点击登录按钮...")
            login_btn.click()
            time.sleep(2)
        
        # 查找邮箱输入框
        print("查找邮箱输入框...")
        email_input = page.ele('tag:input@type=email', timeout=10)
        if not email_input:
            email_input = page.ele('tag:input@placeholder:email', timeout=5)
        if not email_input:
            email_input = page.ele('tag:input@name=email', timeout=5)
        
        if email_input:
            print(f"输入邮箱: {EMAIL}")
            email_input.clear()
            email_input.input(EMAIL)
            time.sleep(1)
        else:
            print("未找到邮箱输入框，尝试其他方式...")
            # 打印页面内容帮助调试
            print("页面标题:", page.title)
            
        # 查找密码输入框
        print("查找密码输入框...")
        pwd_input = page.ele('tag:input@type=password', timeout=5)
        
        if pwd_input:
            print("输入密码...")
            pwd_input.clear()
            pwd_input.input(PASSWORD)
            time.sleep(1)
        
        # 查找并点击登录/提交按钮
        print("查找提交按钮...")
        submit_btn = page.ele('tag:button@type=submit', timeout=5)
        if not submit_btn:
            submit_btn = page.ele('text:登录', timeout=3)
        if not submit_btn:
            submit_btn = page.ele('text:Login', timeout=3)
        if not submit_btn:
            submit_btn = page.ele('text:Sign in', timeout=3)
        
        if submit_btn:
            print("点击提交按钮...")
            submit_btn.click()
            time.sleep(5)
        
        # 等待登录完成
        print("等待登录完成...")
        time.sleep(5)
        
        # 获取 localStorage
        print("获取 localStorage...")
        local_storage = page.run_js('return JSON.stringify(localStorage)')
        local_storage_data = json.loads(local_storage) if local_storage else {}
        
        # 获取 sessionStorage
        print("获取 sessionStorage...")
        session_storage = page.run_js('return JSON.stringify(sessionStorage)')
        session_storage_data = json.loads(session_storage) if session_storage else {}
        
        # 获取 cookies
        print("获取 cookies...")
        cookies = page.cookies()
        
        # 查找 account_token
        account_token = None
        for key, value in local_storage_data.items():
            if 'token' in key.lower() or 'account' in key.lower():
                print(f"Found in localStorage: {key} = {value[:50] if len(str(value)) > 50 else value}...")
                if 'account_token' in key.lower() or key == 'account_token':
                    account_token = value
        
        for key, value in session_storage_data.items():
            if 'token' in key.lower() or 'account' in key.lower():
                print(f"Found in sessionStorage: {key} = {value[:50] if len(str(value)) > 50 else value}...")
        
        # 保存数据
        print("\n保存数据...")
        
        # 保存 localStorage
        with open('valuescan_localstorage.json', 'w', encoding='utf-8') as f:
            json.dump(local_storage_data, f, ensure_ascii=False, indent=2)
        print("已保存 valuescan_localstorage.json")
        
        # 保存 sessionStorage
        with open('valuescan_sessionstorage.json', 'w', encoding='utf-8') as f:
            json.dump(session_storage_data, f, ensure_ascii=False, indent=2)
        print("已保存 valuescan_sessionstorage.json")
        
        # 保存 cookies
        cookies_list = []
        for cookie in cookies:
            cookies_list.append({
                'name': cookie.get('name'),
                'value': cookie.get('value'),
                'domain': cookie.get('domain'),
                'path': cookie.get('path', '/'),
            })
        with open('valuescan_cookies.json', 'w', encoding='utf-8') as f:
            json.dump(cookies_list, f, ensure_ascii=False, indent=2)
        print("已保存 valuescan_cookies.json")
        
        if account_token:
            print(f"\n✅ 成功获取 account_token!")
            print(f"Token: {account_token[:50]}...")
        else:
            print("\n⚠️ 未找到 account_token，请检查登录是否成功")
            print("localStorage keys:", list(local_storage_data.keys()))
        
        # 保持浏览器打开一会儿以便检查
        print("\n浏览器将在 10 秒后关闭...")
        time.sleep(10)
        
        return account_token
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        page.quit()

if __name__ == "__main__":
    token = login_and_get_token()
    if token:
        print(f"\n最终 Token: {token}")
