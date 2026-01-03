#!/usr/bin/env python3
"""
简化版 CDP Token 刷新器 V2 - 使用 HTTP API 替代 WebSocket
Simple CDP-based token refresher using HTTP API instead of WebSocket
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

    cmd = [
        chrome_path,
        "--headless=new",
        f"--remote-debugging-port={CDP_PORT}",
        "--remote-allow-origins=*",
        "--no-sandbox",
        "--disable-gpu",
        "--disable-dev-shm-usage",
        "--disable-web-security",
        "--user-data-dir=/tmp/chrome_cdp_profile",
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


class CDPClient:
    """CDP HTTP 客户端"""

    def __init__(self, port=9222):
        self.port = port
        self.base_url = f"http://127.0.0.1:{port}"
        self.ws_url = None
        self.msg_id = 0

    def get_targets(self):
        """获取所有 CDP 目标"""
        try:
            resp = requests.get(f"{self.base_url}/json", timeout=5)
            return resp.json()
        except Exception as e:
            logger.error(f"获取目标失败: {e}")
            return []

    def create_target(self, url):
        """创建新的页面目标"""
        try:
            resp = requests.put(f"{self.base_url}/json/new?{url}", timeout=5)
            return resp.json()
        except Exception as e:
            logger.error(f"创建目标失败: {e}")
            return None

    def send_command(self, target_id, method, params=None):
        """发送 CDP 命令（通过 HTTP）"""
        self.msg_id += 1
        url = f"{self.base_url}/json"

        payload = {
            "id": self.msg_id,
            "method": method
        }
        if params:
            payload["params"] = params

        try:
            # 使用 WebSocket URL 发送命令
            import websocket
            ws_url = self.ws_url or self._get_ws_url(target_id)
            if not ws_url:
                return None

            ws = websocket.create_connection(
                ws_url,
                timeout=10,
                origin="http://127.0.0.1:9222"
            )
            ws.send(json.dumps(payload))

            # 等待响应
            while True:
                result = json.loads(ws.recv())
                if result.get('id') == self.msg_id:
                    ws.close()
                    return result

        except Exception as e:
            logger.error(f"发送命令失败: {e}")
            return None

    def _get_ws_url(self, target_id):
        """获取目标的 WebSocket URL"""
        targets = self.get_targets()
        for target in targets:
            if target.get('id') == target_id:
                return target.get('webSocketDebuggerUrl')
        return None


def cdp_login_v2(email, password):
    """使用 CDP HTTP API 登录并获取 token"""
    try:
        client = CDPClient(CDP_PORT)

        # 获取或创建页面目标
        targets = client.get_targets()
        page_target = None

        for target in targets:
            if target.get('type') == 'page':
                page_target = target
                break

        if not page_target:
            logger.info("创建新页面...")
            page_target = client.create_target("https://valuescan.io/login")
            time.sleep(2)

            if not page_target:
                targets = client.get_targets()
                for target in targets:
                    if target.get('type') == 'page':
                        page_target = target
                        break

        if not page_target:
            logger.error("无法创建页面")
            return False

        target_id = page_target.get('id')
        client.ws_url = page_target.get('webSocketDebuggerUrl')
        logger.info(f"连接到页面: {page_target.get('url')}")

        # 使用 WebSocket 连接
        import websocket
        ws = websocket.create_connection(
            client.ws_url,
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
