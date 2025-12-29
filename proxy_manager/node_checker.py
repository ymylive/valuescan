#!/usr/bin/env python3
"""
代理节点检测和自动切换程序
- 定期检测当前节点是否可用
- 检测币安 API 是否可访问
- 自动切换到下一个可用节点
"""
import os
import sys
import json
import time
import base64
import urllib.request
import urllib.parse
import subprocess
import logging
from pathlib import Path
from typing import List, Dict, Optional

# 配置
SUBSCRIBE_URL_FILE = os.getenv("PROXY_SUBSCRIBE_URL_FILE", "/etc/valuescan/proxy_subscribe_url")
SUBSCRIBE_URL = (
    os.getenv("PROXY_SUBSCRIBE_URL")
    or os.getenv("VALUESCAN_PROXY_SUBSCRIBE_URL")
    or ""
).strip()
XRAY_CONFIG_PATH = "/etc/xray/config.json"
CHECK_INTERVAL = 60  # 检测间隔（秒）
BINANCE_TEST_URL = "https://api.binance.com/api/v3/ping"
SOCKS_PROXY = "socks5://127.0.0.1:1080"

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('/var/log/proxy_checker.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def _load_subscribe_url() -> str:
    if SUBSCRIBE_URL:
        return SUBSCRIBE_URL
    try:
        p = Path(SUBSCRIBE_URL_FILE)
        if p.exists():
            return (p.read_text(encoding="utf-8", errors="ignore") or "").strip()
    except Exception:
        return ""
    return ""

def fetch_subscribe() -> str:
    """获取订阅内容"""
    subscribe_url = _load_subscribe_url()
    if not subscribe_url:
        logger.error("未配置订阅地址：请设置 PROXY_SUBSCRIBE_URL 或写入 %s", SUBSCRIBE_URL_FILE)
        return ""
    try:
        req = urllib.request.Request(subscribe_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode('utf-8')
    except Exception as e:
        logger.error(f"获取订阅失败: {e}")
        return ""

def parse_vless_nodes(subscribe_content: str) -> List[Dict]:
    """解析 VLESS 节点"""
    nodes = []
    try:
        decoded = base64.b64decode(subscribe_content).decode('utf-8')
        lines = decoded.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line.startswith('vless://'):
                continue
            
            try:
                node = parse_vless_url(line)
                if node:
                    nodes.append(node)
            except Exception as e:
                logger.debug(f"解析节点失败: {e}")
                continue
    except Exception as e:
        logger.error(f"解析订阅内容失败: {e}")
    
    return nodes

def parse_vless_url(url: str) -> Optional[Dict]:
    """解析单个 VLESS URL"""
    try:
        url = url.replace('vless://', '')
        if '#' in url:
            url, name = url.rsplit('#', 1)
            name = urllib.parse.unquote(name)
        else:
            name = "Unknown"
        
        if '@' in url:
            uuid, rest = url.split('@', 1)
        else:
            return None
        
        if '?' in rest:
            addr_port, params_str = rest.split('?', 1)
        else:
            addr_port = rest
            params_str = ""
        
        # 处理 IPv6 地址
        if addr_port.startswith('['):
            addr_end = addr_port.index(']')
            address = addr_port[1:addr_end]
            port = int(addr_port[addr_end+2:])
        else:
            if ':' in addr_port:
                address, port_str = addr_port.rsplit(':', 1)
                port = int(port_str)
            else:
                return None
        
        params = dict(urllib.parse.parse_qsl(params_str))
        
        return {
            'name': name,
            'uuid': uuid,
            'address': address,
            'port': port,
            'type': params.get('type', 'tcp'),
            'security': params.get('security', 'none'),
            'sni': params.get('sni', ''),
            'flow': params.get('flow', ''),
            'fp': params.get('fp', 'chrome'),
            'host': params.get('host', ''),
            'path': params.get('path', ''),
        }
    except Exception as e:
        logger.debug(f"解析 VLESS URL 失败: {e}")
        return None

def generate_xray_config(node: Dict) -> Dict:
    """生成 Xray 配置"""
    config = {
        "inbounds": [{
            "port": 1080,
            "listen": "127.0.0.1",
            "protocol": "socks",
            "settings": {"udp": True}
        }],
        "outbounds": [{
            "protocol": "vless",
            "settings": {
                "vnext": [{
                    "address": node['address'],
                    "port": node['port'],
                    "users": [{
                        "id": node['uuid'],
                        "encryption": "none",
                        "flow": node['flow'] if node['flow'] else ""
                    }]
                }]
            },
            "streamSettings": {
                "network": node['type'],
                "security": node['security']
            }
        }]
    }
    
    # TLS 设置
    if node['security'] == 'tls':
        config['outbounds'][0]['streamSettings']['tlsSettings'] = {
            "serverName": node['sni'],
            "fingerprint": node['fp']
        }
    
    # WebSocket 设置
    if node['type'] == 'ws':
        config['outbounds'][0]['streamSettings']['wsSettings'] = {
            "path": node['path'] or "/",
            "headers": {"Host": node['host']} if node['host'] else {}
        }
    
    return config

def save_xray_config(config: Dict) -> bool:
    """保存 Xray 配置"""
    try:
        with open(XRAY_CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"保存配置失败: {e}")
        return False

def restart_xray() -> bool:
    """重启 Xray 服务"""
    try:
        subprocess.run(['systemctl', 'restart', 'xray'], check=True, timeout=30)
        time.sleep(3)  # 等待服务启动
        return True
    except Exception as e:
        logger.error(f"重启 Xray 失败: {e}")
        return False

def check_proxy() -> bool:
    """检测代理是否可用"""
    try:
        import socks
        import socket
        
        socks.set_default_proxy(socks.SOCKS5, "127.0.0.1", 1080)
        socket.socket = socks.socksocket
        
        req = urllib.request.Request(BINANCE_TEST_URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status == 200
    except ImportError:
        # 使用 curl 作为备选方案
        return check_proxy_curl()
    except Exception as e:
        logger.warning(f"代理检测失败: {e}")
        return False

def check_proxy_curl() -> bool:
    """使用 curl 检测代理"""
    try:
        result = subprocess.run(
            ['curl', '-x', 'socks5://127.0.0.1:1080', '-s', '-o', '/dev/null', 
             '-w', '%{http_code}', '--connect-timeout', '10', BINANCE_TEST_URL],
            capture_output=True, text=True, timeout=20
        )
        return result.stdout.strip() == '200'
    except Exception as e:
        logger.warning(f"Curl 检测失败: {e}")
        return False

def get_current_node_info() -> Optional[Dict]:
    """获取当前节点信息"""
    try:
        with open(XRAY_CONFIG_PATH, 'r') as f:
            config = json.load(f)
        vnext = config['outbounds'][0]['settings']['vnext'][0]
        return {
            'address': vnext['address'],
            'port': vnext['port']
        }
    except Exception:
        return None

class ProxyManager:
    def __init__(self):
        self.nodes: List[Dict] = []
        self.current_index = 0
        self.state_file = Path('/var/lib/proxy_manager/state.json')
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.load_state()
    
    def load_state(self):
        """加载状态"""
        try:
            if self.state_file.exists():
                with open(self.state_file) as f:
                    state = json.load(f)
                    self.current_index = state.get('current_index', 0)
        except Exception:
            pass
    
    def save_state(self):
        """保存状态"""
        try:
            with open(self.state_file, 'w') as f:
                json.dump({'current_index': self.current_index}, f)
        except Exception as e:
            logger.error(f"保存状态失败: {e}")
    
    def refresh_nodes(self) -> bool:
        """刷新节点列表"""
        content = fetch_subscribe()
        if not content:
            return False
        
        nodes = parse_vless_nodes(content)
        if not nodes:
            logger.error("没有解析到有效节点")
            return False
        
        # 过滤掉 IPv6 节点和 CF 节点，优先使用直连节点
        priority_nodes = []
        cf_nodes = []
        
        for node in nodes:
            if '[' in str(node.get('address', '')):  # 跳过 IPv6
                continue
            if 'CF' in node.get('name', ''):
                cf_nodes.append(node)
            else:
                priority_nodes.append(node)
        
        self.nodes = priority_nodes + cf_nodes
        logger.info(f"加载了 {len(self.nodes)} 个节点")
        return True
    
    def switch_node(self, index: Optional[int] = None) -> bool:
        """切换到指定节点"""
        if not self.nodes:
            if not self.refresh_nodes():
                return False
        
        if index is not None:
            self.current_index = index % len(self.nodes)
        
        node = self.nodes[self.current_index]
        logger.info(f"切换到节点: {node['name']} ({node['address']}:{node['port']})")
        
        config = generate_xray_config(node)
        if not save_xray_config(config):
            return False
        
        if not restart_xray():
            return False
        
        self.save_state()
        return True
    
    def switch_next(self) -> bool:
        """切换到下一个节点"""
        if not self.nodes:
            if not self.refresh_nodes():
                return False
        
        self.current_index = (self.current_index + 1) % len(self.nodes)
        return self.switch_node(self.current_index)
    
    def find_working_node(self, max_tries: int = 10) -> bool:
        """查找可用节点"""
        if not self.nodes:
            if not self.refresh_nodes():
                return False
        
        start_index = self.current_index
        tried = 0
        
        while tried < min(max_tries, len(self.nodes)):
            if self.switch_node():
                time.sleep(3)  # 等待连接建立
                if check_proxy_curl():
                    logger.info(f"找到可用节点: {self.nodes[self.current_index]['name']}")
                    return True
                else:
                    logger.warning(f"节点不可用: {self.nodes[self.current_index]['name']}")
            
            self.current_index = (self.current_index + 1) % len(self.nodes)
            tried += 1
        
        logger.error(f"尝试了 {tried} 个节点，都不可用")
        return False
    
    def run(self):
        """主循环"""
        logger.info("代理管理器启动")
        
        # 初始加载节点
        self.refresh_nodes()
        
        # 检查当前代理是否可用，不可用则切换
        if not check_proxy_curl():
            logger.warning("当前代理不可用，尝试切换节点")
            self.find_working_node()
        
        fail_count = 0
        
        while True:
            try:
                time.sleep(CHECK_INTERVAL)
                
                if check_proxy_curl():
                    fail_count = 0
                    logger.debug("代理正常")
                else:
                    fail_count += 1
                    logger.warning(f"代理检测失败 ({fail_count}/3)")
                    
                    if fail_count >= 3:
                        logger.warning("连续3次检测失败，切换节点")
                        if self.find_working_node():
                            fail_count = 0
                        else:
                            # 刷新节点列表重试
                            self.refresh_nodes()
                            self.find_working_node()
                            fail_count = 0
                
            except KeyboardInterrupt:
                logger.info("收到中断信号，退出")
                break
            except Exception as e:
                logger.error(f"主循环错误: {e}")
                time.sleep(10)

def main():
    import argparse
    parser = argparse.ArgumentParser(description='代理节点管理器')
    parser.add_argument('--daemon', '-d', action='store_true', help='后台运行')
    parser.add_argument('--switch', '-s', action='store_true', help='切换到下一个节点')
    parser.add_argument('--check', '-c', action='store_true', help='检测当前代理')
    parser.add_argument('--list', '-l', action='store_true', help='列出所有节点')
    parser.add_argument('--index', '-i', type=int, help='切换到指定索引的节点')
    args = parser.parse_args()
    
    manager = ProxyManager()
    
    if args.list:
        manager.refresh_nodes()
        for i, node in enumerate(manager.nodes):
            marker = "→" if i == manager.current_index else " "
            print(f"{marker} [{i}] {node['name']} - {node['address']}:{node['port']}")
        return
    
    if args.check:
        if check_proxy_curl():
            print("✅ 代理正常，币安 API 可访问")
            sys.exit(0)
        else:
            print("❌ 代理不可用或币安 API 无法访问")
            sys.exit(1)
    
    if args.switch:
        if manager.switch_next():
            print(f"✅ 已切换到: {manager.nodes[manager.current_index]['name']}")
        else:
            print("❌ 切换失败")
            sys.exit(1)
        return
    
    if args.index is not None:
        manager.refresh_nodes()
        if args.index < 0 or args.index >= len(manager.nodes):
            print(f"❌ 无效索引，有效范围: 0-{len(manager.nodes)-1}")
            sys.exit(1)
        if manager.switch_node(args.index):
            print(f"✅ 已切换到: {manager.nodes[args.index]['name']}")
        else:
            print("❌ 切换失败")
            sys.exit(1)
        return
    
    # 默认：运行守护进程
    manager.run()

if __name__ == '__main__':
    main()
