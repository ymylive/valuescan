#!/usr/bin/env python3
"""
基于 Selenium 的 Token 刷新器 - 更可靠的跨平台方案
Selenium-based token refresher - More reliable cross-platform solution
"""
import json
import time
import os
import sys
import logging
import subprocess
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# 配置
BASE_DIR = Path(__file__).resolve().parent
CREDENTIALS_FILE = BASE_DIR / "valuescan_credentials.json"
TOKEN_FILE = BASE_DIR / "valuescan_localstorage.json"


class ComponentManager:
    """组件内存管理器"""

    @staticmethod
    def stop_components():
        """停止监测和交易组件，释放内存"""
        logger.info("停止组件以释放内存...")
        components = ["signal_monitor.py", "auto_trader.py"]

        for component in components:
            try:
                # Linux/Mac: 使用 pkill
                result = subprocess.run(
                    ["pkill", "-f", component],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0:
                    logger.info(f"已停止: {component}")
            except FileNotFoundError:
                # Windows: 使用 taskkill
                try:
                    subprocess.run(
                        ["taskkill", "/F", "/FI", f"WINDOWTITLE eq *{component}*"],
                        capture_output=True,
                        timeout=5
                    )
                except:
                    pass
            except:
                pass

        time.sleep(2)
        logger.info("组件已停止")

    @staticmethod
    def start_components():
        """重启监测和交易组件"""
        logger.info("重启组件...")
        try:
            result = subprocess.run(
                ["systemctl", "is-active", "valuescan-monitor"],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0 or b"inactive" in result.stdout:
                subprocess.run(["systemctl", "restart", "valuescan-monitor"], timeout=10)
                subprocess.run(["systemctl", "restart", "valuescan-trader"], timeout=10)
                logger.info("通过 systemd 重启组件")
                return
        except:
            pass
        logger.info("组件重启完成（需要手动配置启动方式）")


def load_credentials():
    """加载登录凭证"""
    # 优先从环境变量读取
    email = os.getenv('VALUESCAN_EMAIL')
    password = os.getenv('VALUESCAN_PASSWORD')

    if email and password:
        logger.info(f"从环境变量加载凭证: {email}")
        return email, password

    # 从文件读取
    if CREDENTIALS_FILE.exists():
        try:
            with open(CREDENTIALS_FILE, 'r', encoding='utf-8') as f:
                creds = json.load(f)
                return creds.get('email'), creds.get('password')
        except Exception as e:
            logger.error(f"加载凭证失败: {e}")

    return None, None


def selenium_login(email, password):
    """使用 Selenium 登录并获取 token"""
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
    except ImportError:
        logger.error("未安装 selenium，请运行: pip install selenium")
        return False

    driver = None
    try:
        # 配置 Chrome 选项
        chrome_options = Options()

        # 检查是否使用 headless 模式（默认使用 headless 模式）
        use_headless = os.getenv('SELENIUM_HEADLESS', 'true').lower() == 'true'

        if use_headless:
            logger.info("使用 headless 模式")
            chrome_options.add_argument('--headless=new')
        else:
            logger.info("使用有头模式（需要 DISPLAY 环境变量）")

        # 创建临时用户数据目录，避免冲突
        import tempfile
        user_data_dir = tempfile.mkdtemp(prefix="chrome_selenium_")
        logger.info(f"使用临时用户数据目录: {user_data_dir}")

        chrome_options.add_argument(f'--user-data-dir={user_data_dir}')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')

        # 启动浏览器
        logger.info("启动 Chrome...")
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(60)

        # 导航到登录页
        logger.info("导航到登录页...")
        driver.get("https://valuescan.io/login")
        time.sleep(10)  # 增加等待时间到 10 秒

        # 打印页面标题和 URL 用于调试
        logger.info(f"页面标题: {driver.title}")
        logger.info(f"当前 URL: {driver.current_url}")

        # 等待并填写邮箱 - 使用多种选择器尝试
        logger.info("填写邮箱...")
        email_input = None
        try:
            # 尝试 1: placeholder 包含 "邮箱"
            email_input = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[placeholder*="邮箱"]'))
            )
        except:
            try:
                # 尝试 2: placeholder 包含 "email"
                email_input = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'input[placeholder*="email" i]'))
                )
            except:
                # 尝试 3: type="email"
                email_input = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="email"]'))
                )

        email_input.clear()
        email_input.send_keys(email)
        time.sleep(2)

        # 填写密码 - 使用多种选择器尝试
        logger.info("填写密码...")
        password_input = None
        try:
            # 尝试 1: placeholder 包含 "密码"
            password_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[placeholder*="密码"]'))
            )
        except:
            try:
                # 尝试 2: placeholder 包含 "password"
                password_input = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'input[placeholder*="password" i]'))
                )
            except:
                # 尝试 3: type="password"
                password_input = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="password"]'))
                )

        password_input.clear()
        password_input.send_keys(password)
        time.sleep(2)

        # 点击登录按钮 - 使用多种方式尝试
        logger.info("点击登录...")
        try:
            # 方式1: 通过按钮文本
            login_button = driver.find_element(By.XPATH, '//button[text()="登录"]')
        except:
            try:
                # 方式2: 通过包含文本
                login_button = driver.find_element(By.XPATH, '//button[contains(., "登录")]')
            except:
                # 方式3: 通过表单中的按钮（通常登录按钮是表单中的第一个按钮）
                login_button = driver.find_element(By.CSS_SELECTOR, 'form button')

        login_button.click()

        # 等待登录完成（等待 URL 变化）
        logger.info("等待登录完成...")
        WebDriverWait(driver, 10).until(
            lambda d: "login" not in d.current_url
        )
        time.sleep(3)

        # 获取 localStorage
        logger.info("获取 token...")
        storage_data = driver.execute_script("return JSON.parse(JSON.stringify(localStorage));")

        # 保存 token
        if storage_data:
            with open(TOKEN_FILE, 'w', encoding='utf-8') as f:
                json.dump(storage_data, f, ensure_ascii=False, indent=2)
            logger.info(f"Token 已保存: {list(storage_data.keys())}")
            return True
        else:
            logger.error("未获取到 token")
            return False

    except Exception as e:
        logger.error(f"Selenium 登录失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if driver:
            driver.quit()
            logger.info("浏览器已关闭")


def refresh_token():
    """刷新 token 的完整流程"""
    try:
        # 1. 停止组件
        ComponentManager.stop_components()

        # 2. 加载凭证
        email, password = load_credentials()
        if not email or not password:
            logger.error("未找到登录凭证")
            return False

        # 3. 执行登录
        logger.info("开始 Selenium 登录...")
        success = selenium_login(email, password)

        return success

    finally:
        # 4. 重启组件
        ComponentManager.start_components()


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='Selenium Token 刷新器')
    parser.add_argument('--once', action='store_true', help='运行一次后退出')
    parser.add_argument('--interval', type=float, default=0.8, help='刷新间隔（小时）')
    args = parser.parse_args()

    if args.once:
        logger.info("运行一次刷新...")
        success = refresh_token()
        sys.exit(0 if success else 1)

    # 循环刷新
    logger.info(f"启动 Token 刷新循环，间隔: {args.interval} 小时")
    while True:
        try:
            success = refresh_token()
            if success:
                logger.info(f"刷新成功，等待 {args.interval} 小时")
                time.sleep(args.interval * 3600)
            else:
                logger.error("刷新失败，5分钟后重试")
                time.sleep(300)
        except KeyboardInterrupt:
            logger.info("用户中断")
            break
        except Exception as e:
            logger.error(f"错误: {e}")
            time.sleep(300)


if __name__ == "__main__":
    main()
