#!/usr/bin/env python3
"""
使用 Selenium 自动登录 valuescan.io
"""
import time
import sys
import os

def login_valuescan(email: str, password: str):
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    
    print("正在启动浏览器...")
    
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.binary_location = '/usr/bin/chromium-browser'
    
    # 设置用户数据目录保存 cookies
    user_data_dir = '/root/.config/chromium/valuescan_selenium'
    os.makedirs(user_data_dir, exist_ok=True)
    options.add_argument(f'--user-data-dir={user_data_dir}')
    
    service = Service('/usr/bin/chromedriver')
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        print("访问 valuescan.io...")
        driver.get('https://www.valuescan.io/login')
        time.sleep(3)
        
        # 检查是否已登录
        if 'dashboard' in driver.current_url or 'home' in driver.current_url:
            print("✅ 已经登录")
            return True
        
        print(f"当前页面: {driver.current_url}")
        print("正在输入登录信息...")
        
        # 等待页面加载
        wait = WebDriverWait(driver, 15)
        
        # 查找邮箱输入框
        try:
            email_input = wait.until(EC.presence_of_element_located((
                By.XPATH, "//input[@type='email' or @name='email' or contains(@placeholder, 'mail') or contains(@placeholder, 'Email')]"
            )))
            email_input.clear()
            email_input.send_keys(email)
            print("  ✓ 邮箱已输入")
        except Exception as e:
            print(f"  ✗ 未找到邮箱输入框: {e}")
            # 尝试截图调试
            driver.save_screenshot('/tmp/login_page.png')
            print("  已保存截图到 /tmp/login_page.png")
            return False
        
        time.sleep(1)
        
        # 查找密码输入框
        try:
            pwd_input = driver.find_element(By.XPATH, "//input[@type='password']")
            pwd_input.clear()
            pwd_input.send_keys(password)
            print("  ✓ 密码已输入")
        except Exception as e:
            print(f"  ✗ 未找到密码输入框: {e}")
            return False
        
        time.sleep(1)
        
        # 查找登录按钮
        try:
            login_btn = driver.find_element(By.XPATH, 
                "//button[contains(text(), '登录') or contains(text(), 'Login') or contains(text(), 'Sign') or @type='submit']")
            login_btn.click()
            print("  ✓ 点击登录按钮")
        except Exception as e:
            print(f"  ✗ 未找到登录按钮: {e}")
            return False
        
        # 等待登录完成
        print("等待登录完成...")
        time.sleep(8)
        
        print(f"登录后页面: {driver.current_url}")
        
        # 检查是否登录成功
        if 'login' not in driver.current_url.lower():
            print("✅ 登录成功!")
            # 保存 cookies
            cookies = driver.get_cookies()
            print(f"已保存 {len(cookies)} 个 cookies")
            time.sleep(2)
            return True
        else:
            print("❌ 登录可能失败")
            driver.save_screenshot('/tmp/login_failed.png')
            return False
            
    except Exception as e:
        print(f"❌ 登录出错: {e}")
        driver.save_screenshot('/tmp/login_error.png')
        return False
    finally:
        driver.quit()

if __name__ == '__main__':
    # 安装 selenium
    import subprocess
    subprocess.run([sys.executable, '-m', 'pip', 'install', 'selenium', '-q'])
    
    email = (sys.argv[1] if len(sys.argv) > 1 else (os.getenv("VALUESCAN_EMAIL") or "")).strip()
    password = (sys.argv[2] if len(sys.argv) > 2 else (os.getenv("VALUESCAN_PASSWORD") or "")).strip()
    if not email or not password:
        print("Missing credentials. Use: python selenium_login.py <email> <password> or set VALUESCAN_EMAIL/VALUESCAN_PASSWORD")
        sys.exit(2)
    
    success = login_valuescan(email, password)
    sys.exit(0 if success else 1)
