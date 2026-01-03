#!/usr/bin/env python3
"""
Clash 配置导出器
"""
from typing import List, Dict, Any
import yaml


def _safe_dump(data: Any) -> str:
    """PyYAML compatibility: sort_keys isn't available on older versions."""
    try:
        return yaml.safe_dump(data, allow_unicode=True, sort_keys=False)
    except TypeError:
        return yaml.safe_dump(data, allow_unicode=True)


def generate_clash_yaml(config: Dict[str, Any], nodes: List[Dict[str, Any]]) -> str:
    """生成 Clash YAML 配置"""
    lines = []

    # 基础配置
    lines.append(f"port: {config.get('port', 7890)}")
    lines.append(f"socks-port: {config.get('socksPort', 7891)}")
    lines.append(f"allow-lan: {str(config.get('allowLan', False)).lower()}")
    bind_address = config.get('bindAddress')
    if isinstance(bind_address, str):
        bind_address = bind_address.strip()
    if bind_address:
        lines.append(f"bind-address: {bind_address}")
    redir_port = config.get('redirPort', config.get('redir-port'))
    if isinstance(redir_port, str):
        redir_port = redir_port.strip()
        if redir_port.isdigit():
            redir_port = int(redir_port)
    if isinstance(redir_port, int) and redir_port > 0:
        lines.append(f"redir-port: {redir_port}")
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
    proxy_providers = config.get('proxyProviders')
    if proxy_providers is not None:
        lines.extend(_dump_yaml_mapping("proxy-providers", proxy_providers))
        lines.append("")

    lines.append("proxy-groups:")
    proxy_groups = config.get('proxyGroups')
    if proxy_groups is None:
        proxy_groups = _get_default_proxy_groups()

    for group in proxy_groups:
        lines.extend(_generate_proxy_group_yaml(group))

    lines.append("")

    # 规则
    rule_providers = config.get('ruleProviders')
    if rule_providers is not None:
        lines.extend(_dump_yaml_mapping("rule-providers", rule_providers))
        lines.append("")

    rules = config.get('rules')
    if rules is None:
        lines.extend(_generate_default_rules())
    else:
        lines.extend(_dump_yaml_list_with_key("rules", rules))

    return "\n".join(lines)


def _generate_proxy_yaml(node: Dict[str, Any]) -> List[str]:
    """Generate proxy YAML lines."""
    dumped = _safe_dump([node])
    return [f"  {line}" if line.strip() else line for line in dumped.splitlines()]


def _generate_proxy_group_yaml(group: Dict[str, Any]) -> List[str]:
    """Generate proxy group YAML lines."""
    dumped = _safe_dump([group])
    return [f"  {line}" if line.strip() else line for line in dumped.splitlines()]


def _dump_yaml_mapping(name: str, mapping: Any) -> List[str]:
    if mapping == {}:
        return [f"{name}: {{}}"]
    dumped = _safe_dump(mapping)
    lines = [f"{name}:"]
    lines.extend([f"  {line}" if line.strip() else line for line in dumped.splitlines()])
    return lines


def _dump_yaml_list_with_key(name: str, items: Any) -> List[str]:
    if items == []:
        return [f"{name}: []"]
    dumped = _safe_dump(items)
    lines = [f"{name}:"]
    lines.extend([f"  {line}" if line.strip() else line for line in dumped.splitlines()])
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

