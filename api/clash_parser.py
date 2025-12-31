#!/usr/bin/env python3
"""
Clash 订阅解析器
"""
import base64
import json
import yaml
from typing import List, Dict, Any, Tuple, Optional

def parse_clash_subscription(
    content: str,
) -> Tuple[
    List[Dict[str, Any]],
    List[Dict[str, Any]],
    Optional[List[Any]],
    Optional[Dict[str, Any]],
    Optional[Dict[str, Any]],
]:
    """解析 Clash 订阅，返回 (节点列表, 策略组列表)"""
    try:
        config = yaml.safe_load(content)
        nodes = config.get('proxies', []) if config else []
        groups = config.get('proxy-groups', []) if config else []
        rules = None
        proxy_providers = None
        rule_providers = None
        if config and 'rules' in config:
            raw_rules = config.get('rules')
            if isinstance(raw_rules, list):
                rules = raw_rules
            elif raw_rules is None:
                rules = []
            else:
                rules = [str(raw_rules)]
        if config:
            proxy_providers = config.get('proxy-providers')
            rule_providers = config.get('rule-providers')
        return nodes, groups, rules, proxy_providers, rule_providers
    except Exception:
        pass
    return [], [], None, None, None

def parse_base64_subscription(content: str) -> List[Dict[str, Any]]:
    """解析 Base64 订阅（V2Ray/Shadowsocks）"""
    nodes = []
    try:
        decoded = base64.b64decode(content).decode('utf-8')
        lines = decoded.strip().split('\n')

        for line in lines:
            line = line.strip()
            if line.startswith('ss://'):
                node = parse_shadowsocks_url(line)
                if node:
                    nodes.append(node)
            elif line.startswith('vmess://'):
                node = parse_vmess_url(line)
                if node:
                    nodes.append(node)
    except Exception:
        pass
    return nodes

def parse_shadowsocks_url(url: str) -> Dict[str, Any]:
    """解析 Shadowsocks URL"""
    try:
        content = url[5:]  # 移除 'ss://'
        parts = content.split('#')
        decoded = base64.b64decode(parts[0]).decode('utf-8')

        method, rest = decoded.split(':', 1)
        password, server_port = rest.split('@')
        server, port = server_port.split(':')
        name = parts[1] if len(parts) > 1 else f'SS-{server}'

        return {
            'name': name,
            'type': 'ss',
            'server': server,
            'port': int(port),
            'cipher': method,
            'password': password
        }
    except Exception:
        return None

def parse_vmess_url(url: str) -> Dict[str, Any]:
    """解析 VMess URL"""
    try:
        content = url[8:]  # 移除 'vmess://'
        decoded = base64.b64decode(content).decode('utf-8')
        config = json.loads(decoded)

        return {
            'name': config.get('ps', 'VMess'),
            'type': 'vmess',
            'server': config.get('add'),
            'port': int(config.get('port')),
            'uuid': config.get('id'),
            'alterId': int(config.get('aid', 0)),
            'cipher': 'auto',
            'network': config.get('net', 'tcp'),
            'tls': config.get('tls') == 'tls'
        }
    except Exception:
        return None
