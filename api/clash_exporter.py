#!/usr/bin/env python3
"""
Clash 配置导出器
"""
from typing import List, Dict, Any


def generate_clash_yaml(config: Dict[str, Any], nodes: List[Dict[str, Any]]) -> str:
    """生成 Clash YAML 配置"""
    lines = []

    # 基础配置
    lines.append(f"port: {config.get('port', 7890)}")
    lines.append(f"socks-port: {config.get('socksPort', 7891)}")
    lines.append(f"allow-lan: {str(config.get('allowLan', False)).lower()}")
    lines.append(f"mode: {config.get('mode', 'rule')}")
    lines.append(f"log-level: {config.get('logLevel', 'info')}")
    lines.append(f"external-controller: {config.get('externalController', '127.0.0.1:9090')}")

    if config.get('secret'):
        lines.append(f"secret: {config['secret']}")

    lines.append("")

    # 代理节点
    lines.append("proxies:")
    if not nodes:
        lines.append("  # No proxies configured")
    else:
        for node in nodes:
            lines.extend(_generate_proxy_yaml(node))

    lines.append("")

    # 策略组
    lines.append("proxy-groups:")
    proxy_groups = config.get('proxyGroups', [])
    if not proxy_groups:
        proxy_groups = _get_default_proxy_groups()

    for group in proxy_groups:
        lines.extend(_generate_proxy_group_yaml(group))

    lines.append("")

    # 规则
    lines.extend(_generate_default_rules())

    return "\n".join(lines)


def _generate_proxy_yaml(node: Dict[str, Any]) -> List[str]:
    """生成单个代理节点的 YAML"""
    lines = []
    lines.append(f"  - name: {node.get('name', 'Proxy')}")
    lines.append(f"    type: {node.get('type', 'ss')}")
    lines.append(f"    server: {node.get('server', '')}")
    lines.append(f"    port: {node.get('port', 0)}")

    # 类型特定字段
    node_type = node.get('type', 'ss')
    if node_type in ['ss', 'shadowsocks']:
        if node.get('cipher'):
            lines.append(f"    cipher: {node['cipher']}")
        if node.get('password'):
            lines.append(f"    password: {node['password']}")
    elif node_type == 'vmess':
        if node.get('uuid'):
            lines.append(f"    uuid: {node['uuid']}")
        if node.get('alterId') is not None:
            lines.append(f"    alterId: {node['alterId']}")
        if node.get('network'):
            lines.append(f"    network: {node['network']}")
    elif node_type == 'trojan':
        if node.get('password'):
            lines.append(f"    password: {node['password']}")

    # 通用可选字段
    if node.get('tls'):
        lines.append("    tls: true")
    if node.get('skipCertVerify'):
        lines.append("    skip-cert-verify: true")
    if node.get('udp'):
        lines.append("    udp: true")

    return lines


def _generate_proxy_group_yaml(group: Dict[str, Any]) -> List[str]:
    """生成策略组的 YAML"""
    lines = []
    lines.append(f"  - name: {group.get('name', 'Proxy Group')}")
    lines.append(f"    type: {group.get('type', 'select')}")

    # 代理列表
    lines.append("    proxies:")
    for proxy in group.get('proxies', ['DIRECT']):
        lines.append(f"      - {proxy}")

    # 类型特定字段
    group_type = group.get('type', 'select')
    if group_type in ['url-test', 'fallback', 'load-balance']:
        if group.get('url'):
            lines.append(f"    url: {group['url']}")
        if group.get('interval'):
            lines.append(f"    interval: {group['interval']}")

    # 额外字段
    if group_type == 'url-test' and group.get('tolerance'):
        lines.append(f"    tolerance: {group['tolerance']}")

    if group_type == 'load-balance' and group.get('strategy'):
        lines.append(f"    strategy: {group['strategy']}")

    return lines


def _generate_default_rules() -> List[str]:
    """生成默认规则"""
    lines = []
    lines.append("rules:")
    lines.append("  # LAN")
    lines.append("  - DOMAIN-SUFFIX,local,DIRECT")
    lines.append("  - IP-CIDR,127.0.0.0/8,DIRECT")
    lines.append("  - IP-CIDR,172.16.0.0/12,DIRECT")
    lines.append("  - IP-CIDR,192.168.0.0/16,DIRECT")
    lines.append("  - IP-CIDR,10.0.0.0/8,DIRECT")
    lines.append("  - IP-CIDR,17.0.0.0/8,DIRECT")
    lines.append("  - IP-CIDR,100.64.0.0/10,DIRECT")
    lines.append("")
    lines.append("  # China")
    lines.append("  - GEOIP,CN,DIRECT")
    lines.append("")
    lines.append("  # Final")
    lines.append("  - MATCH,Manual Select")
    return lines


def _get_default_proxy_groups() -> List[Dict[str, Any]]:
    """获取默认策略组"""
    return [
        {
            'id': 'auto',
            'name': 'Auto Select',
            'type': 'url-test',
            'proxies': ['DIRECT'],
            'url': 'http://www.gstatic.com/generate_204',
            'interval': 300
        },
        {
            'id': 'fallback',
            'name': 'Fallback',
            'type': 'fallback',
            'proxies': ['DIRECT'],
            'url': 'http://www.gstatic.com/generate_204',
            'interval': 300
        },
        {
            'id': 'select',
            'name': 'Manual Select',
            'type': 'select',
            'proxies': ['DIRECT', 'Auto Select', 'Fallback']
        },
        {
            'id': 'loadbalance',
            'name': 'Load Balance',
            'type': 'load-balance',
            'proxies': ['DIRECT'],
            'url': 'http://www.gstatic.com/generate_204',
            'interval': 300,
            'strategy': 'consistent-hashing'
        }
    ]


def generate_proxy_groups_from_nodes(nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """根据节点列表生成策略组"""
    if not nodes:
        return _get_default_proxy_groups()

    # 收集所有节点名称
    node_names = [node.get('name', 'Proxy') for node in nodes]

    # 创建策略组
    groups = [
        {
            'id': 'auto',
            'name': 'Auto Select',
            'type': 'url-test',
            'proxies': ['DIRECT'] + node_names,
            'url': 'http://www.gstatic.com/generate_204',
            'interval': 300
        },
        {
            'id': 'fallback',
            'name': 'Fallback',
            'type': 'fallback',
            'proxies': ['DIRECT'] + node_names,
            'url': 'http://www.gstatic.com/generate_204',
            'interval': 300
        },
        {
            'id': 'select',
            'name': 'Manual Select',
            'type': 'select',
            'proxies': ['DIRECT', 'Auto Select', 'Fallback'] + node_names
        },
        {
            'id': 'loadbalance',
            'name': 'Load Balance',
            'type': 'load-balance',
            'proxies': node_names,
            'url': 'http://www.gstatic.com/generate_204',
            'interval': 300,
            'strategy': 'consistent-hashing'
        }
    ]

    return groups

