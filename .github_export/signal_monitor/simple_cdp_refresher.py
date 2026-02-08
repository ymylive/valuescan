#!/usr/bin/env python3
"""
简化版 CDP Token 刷新器 - 集成组件内存管理
Simple CDP-based token refresher with component memory management
"""
import json
import time
import os
import sys
import logging
import subprocess
import requests
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
CDP_PORT = 9222


class ComponentManager:
    """组件内存管理器 - 在刷新前停止组件，刷新后重启"""

    @staticmethod
    def stop_components():
        """停止监测和交易组件，释放内存"""
        logger.info("停止组件以释放内存...")

        # 要停止的组件进程名
        components = [
            "signal_monitor.py",
            "auto_trader.py"
        ]

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
                    logger.info(f"已停止: {component}")
                except Exception as e:
                    logger.warning(f"停止 {component} 失败: {e}")
            except Exception as e:
                logger.warning(f"停止 {component} 失败: {e}")

        time.sleep(2)
        logger.info("组件已停止")

    @staticmethod
    def start_components():
        """重启监测和交易组件"""
        logger.info("重启组件...")

        # 检查是否有 systemd 服务
        try:
            result = subprocess.run(
                ["systemctl", "is-active", "valuescan-monitor"],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0 or b"inactive" in result.stdout:
                # 使用 systemd 重启
                subprocess.run(["systemctl", "restart", "valuescan-monitor"], timeout=10)
                subprocess.run(["systemctl", "restart", "valuescan-trader"], timeout=10)
                logger.info("通过 systemd 重启组件")
                return
        except:
            pass

        # 如果没有 systemd，可以在这里添加其他启动方式
        # 例如：直接启动 Python 脚本
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


def find_chrome():
    """查找 Chrome/Chromium 可执行文件"""
    import platform

    if platform.system() == "Windows":
        paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ]
    else:
        paths = [
            "/usr/bin/chromium-browser",
            "/usr/bin/chromium",
            "/usr/bin/google-chrome",
        ]

    for path in paths:
        if os.path.exists(path):
            return path
    return None


def start_chrome():
    """启动 Chrome 浏览器（headless 模式）"""
    chrome_path = find_chrome()
    if not chrome_path:
        logger.error("未找到 Chrome/Chromium")
        return None

    # 创建临时用户数据目录
    import tempfile
    user_data_dir = tempfile.mkdtemp(prefix="chrome_cdp_")

    cmd = [
        chrome_path,
        "--headless=new",
        f"--remote-debugging-port={CDP_PORT}",
        "--remote-allow-origins=*",
        f"--user-data-dir={user_data_dir}",
        "--no-sandbox",
        "--disable-gpu",
        "--disable-dev-shm-usage",
        "--disable-web-security",
        "--disable-features=IsolateOrigins,site-per-process",
    ]

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        logger.info(f"Chrome 已启动 (PID: {proc.pid})")
        time.sleep(3)
        return proc
    except Exception as e:
        logger.error(f"启动 Chrome 失败: {e}")
        return None


def stop_chrome(proc):
    """停止 Chrome 进程"""
    if proc:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except:
            try:
                proc.kill()
            except:
                pass


def cdp_login(email, password):
    """使用 CDP 协议登录并获取 token"""
    try:
        # 获取 CDP 目标
        resp = requests.get(f"http://127.0.0.1:{CDP_PORT}/json", timeout=5)
        targets = resp.json()

        # 找到页面目标
        page_target = None
        for target in targets:
            if target.get('type') == 'page':
                page_target = target
                break

        if not page_target:
            # 创建新页面
            requests.put(f"http://127.0.0.1:{CDP_PORT}/json/new?https://valuescan.io/login", timeout=5)
            time.sleep(2)
            resp = requests.get(f"http://127.0.0.1:{CDP_PORT}/json", timeout=5)
            targets = resp.json()
            for target in targets:
                if target.get('type') == 'page':
                    page_target = target
                    break

        if not page_target:
            logger.error("无法创建页面")
            return False

        ws_url = page_target.get('webSocketDebuggerUrl')
        logger.info(f"连接到页面: {page_target.get('url')}")

        # 使用 websocket 连接
        import websocket
        ws = websocket.create_connection(
            ws_url,
            timeout=10,
            origin="http://127.0.0.1:9222",
            host="127.0.0.1:9222"
        )

        msg_id = 0

        def send_cdp(method, params=None):
            nonlocal msg_id
            msg_id += 1
            msg = {"id": msg_id, "method": method}
            if params:
                msg["params"] = params
            ws.send(json.dumps(msg))

            # 等待响应
            while True:
                result = json.loads(ws.recv())
                if result.get('id') == msg_id:
                    return result

        # 启用必要的域
        send_cdp("Page.enable")
        send_cdp("Runtime.enable")

        # 导航到登录页
        logger.info("导航到登录页...")
        send_cdp("Page.navigate", {"url": "https://valuescan.io/login"})
        time.sleep(3)

        # 填写邮箱
        logger.info("填写邮箱...")
        js_email = f"""
        const input = document.querySelector('input[type="email"]');
        if (input) {{
            input.value = {json.dumps(email)};
            input.dispatchEvent(new Event('input', {{bubbles: true}}));
            'ok';
        }} else {{
            'not_found';
        }}
        """
        send_cdp("Runtime.evaluate", {"expression": js_email})
        time.sleep(1)

        # 填写密码
        logger.info("填写密码...")
        js_password = f"""
        const input = document.querySelector('input[type="password"]');
        if (input) {{
            input.value = {json.dumps(password)};
            input.dispatchEvent(new Event('input', {{bubbles: true}}));
            'ok';
        }} else {{
            'not_found';
        }}
        """
        send_cdp("Runtime.evaluate", {"expression": js_password})
        time.sleep(1)

        # 点击登录按钮
        logger.info("点击登录...")
        js_click = """
        const btn = document.querySelector('button[type="submit"]');
        if (btn) {
            btn.click();
            'ok';
        } else {
            'not_found';
        }
        """
        send_cdp("Runtime.evaluate", {"expression": js_click})

        # 等待登录完成
        logger.info("等待登录完成...")
        time.sleep(5)

        # 获取 localStorage
        logger.info("获取 token...")
        js_storage = "JSON.stringify(localStorage)"
        result = send_cdp("Runtime.evaluate", {"expression": js_storage})
        storage_str = result.get('result', {}).get('result', {}).get('value', '{}')
        storage_data = json.loads(storage_str)

        # 保存 token
        if storage_data:
            with open(TOKEN_FILE, 'w', encoding='utf-8') as f:
                json.dump(storage_data, f, ensure_ascii=False, indent=2)
            logger.info(f"Token 已保存: {list(storage_data.keys())}")
            ws.close()
            return True
        else:
            logger.error("未获取到 token")
            ws.close()
            return False

    except Exception as e:
        logger.error(f"CDP 登录失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def refresh_token():
    """刷新 token 的完整流程（包含组件管理）"""
    chrome_proc = None

    try:
        # 1. 停止组件，释放内存
        ComponentManager.stop_components()

        # 2. 加载凭证
        email, password = load_credentials()
        if not email or not password:
            logger.error("未找到登录凭证")
            return False

        # 3. 启动 Chrome
        logger.info("启动 Chrome...")
        chrome_proc = start_chrome()
        if not chrome_proc:
            return False

        # 4. 执行 CDP 登录
        logger.info("开始 CDP 登录...")
        success = cdp_login(email, password)

        return success

    finally:
        # 5. 清理 Chrome 进程
        if chrome_proc:
            logger.info("停止 Chrome...")
            stop_chrome(chrome_proc)

        # 6. 重启组件
        ComponentManager.start_components()


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='简化版 CDP Token 刷新器')
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
