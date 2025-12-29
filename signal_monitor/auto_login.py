#!/usr/bin/env python3
"""
自动登录 valuescan.io 并保存 cookies
"""
import time
import sys
import os

def login_valuescan(email: str, password: str):
    """使用 DrissionPage 自动登录"""
    from DrissionPage import ChromiumPage, ChromiumOptions
    
    print("正在启动浏览器...")
    
    # 配置 Chrome 选项
    co = ChromiumOptions()
    co.set_browser_path('/usr/bin/chromium-browser')
    co.set_argument('--no-sandbox')
    co.set_argument('--disable-dev-shm-usage')
    co.set_argument('--disable-gpu')
    co.set_argument('--headless=new')
    co.set_user_data_path('/root/.config/chromium/valuescan')
    
    # 启动浏览器
    page = ChromiumPage(co)
    
    try:
        print("访问 valuescan.io...")
        page.get('https://www.valuescan.io/login')
        time.sleep(3)
        
        # 检查是否已登录
        if 'dashboard' in page.url or 'home' in page.url:
            print("✅ 已经登录，无需重复登录")
            return True
        
        print("正在输入登录信息...")
        
        # 查找邮箱输入框
        email_input = page.ele('xpath://input[@type="email" or @name="email" or contains(@placeholder, "mail")]')
        if email_input:
            email_input.clear()
            email_input.input(email)
            print("  ✓ 邮箱已输入")
        else:
            print("  ✗ 未找到邮箱输入框")
            return False
        
        time.sleep(1)
        
        # 查找密码输入框
        pwd_input = page.ele('xpath://input[@type="password" or @name="password"]')
        if pwd_input:
            pwd_input.clear()
            pwd_input.input(password)
            print("  ✓ 密码已输入")
        else:
            print("  ✗ 未找到密码输入框")
            return False
        
        time.sleep(1)
        
        # 查找登录按钮
        login_btn = page.ele('xpath://button[contains(text(), "登录") or contains(text(), "Login") or contains(text(), "Sign")]')
        if not login_btn:
            login_btn = page.ele('xpath://button[@type="submit"]')
        
        if login_btn:
            login_btn.click()
            print("  ✓ 点击登录按钮")
        else:
            print("  ✗ 未找到登录按钮")
            return False
        
        # 等待登录完成
        print("等待登录完成...")
        time.sleep(5)
        
        # 检查是否登录成功
        if 'login' not in page.url.lower():
            print("✅ 登录成功!")
            print(f"当前页面: {page.url}")
            
            # 保存 cookies
            cookies = page.cookies()
            print(f"已保存 {len(cookies)} 个 cookies")
            
            # 保持浏览器运行一段时间确保 cookies 被保存
            time.sleep(3)
            return True
        else:
            print("❌ 登录可能失败，请检查账号密码")
            return False
            
    except Exception as e:
        print(f"❌ 登录出错: {e}")
        return False
    finally:
        page.quit()

if __name__ == '__main__':
    email = (sys.argv[1] if len(sys.argv) > 1 else (os.getenv("VALUESCAN_EMAIL") or "")).strip()
    password = (sys.argv[2] if len(sys.argv) > 2 else (os.getenv("VALUESCAN_PASSWORD") or "")).strip()
    if not email or not password:
        print("Missing credentials. Use: python auto_login.py <email> <password> or set VALUESCAN_EMAIL/VALUESCAN_PASSWORD")
        sys.exit(2)
    
    success = login_valuescan(email, password)
    sys.exit(0 if success else 1)
