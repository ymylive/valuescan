#!/usr/bin/env python3
"""
Clash 配置和节点存储
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional

class ClashStore:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.config_file = self.data_dir / "clash_config.json"
        self.nodes_file = self.data_dir / "clash_nodes.json"

    def get_config(self) -> Dict[str, Any]:
        """获取Clash配置"""
        if self.config_file.exists():
            try:
                return json.loads(self.config_file.read_text(encoding='utf-8'))
            except Exception:
                pass
        return self._default_config()

    def save_config(self, config: Dict[str, Any]) -> None:
        """保存Clash配置"""
        self.config_file.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding='utf-8')

    def get_nodes(self) -> List[Dict[str, Any]]:
        """获取节点列表"""
        if self.nodes_file.exists():
            try:
                return json.loads(self.nodes_file.read_text(encoding='utf-8'))
            except Exception:
                pass
        return []

    def save_nodes(self, nodes: List[Dict[str, Any]]) -> None:
        """保存节点列表"""
        self.nodes_file.write_text(json.dumps(nodes, ensure_ascii=False, indent=2), encoding='utf-8')

    def get_proxy_groups(self) -> List[Dict[str, Any]]:
        """获取策略组列表"""
        config = self.get_config()
        groups = config.get('proxyGroups')
        if groups is None:
            return self._default_proxy_groups()
        return groups

    def save_proxy_groups(self, groups: List[Dict[str, Any]]) -> None:
        """保存策略组列表"""
        config = self.get_config()
        config['proxyGroups'] = groups
        self.save_config(config)

    def _default_config(self) -> Dict[str, Any]:
        """默认配置"""
        return {
            'port': 7890,
            'socksPort': 7891,
            'allowLan': False,
            'bindAddress': '',
            'redirPort': 0,
            'mode': 'rule',
            'logLevel': 'info',
            'externalController': '127.0.0.1:9090',
            'secret': '',
            'subscriptions': [],
            'proxyGroups': self._default_proxy_groups(),
            'autoTest': True,
            'autoTestInterval': 30,
            'testUrl': 'http://www.gstatic.com/generate_204',
            'testTimeout': 5
        }

    def _default_proxy_groups(self) -> List[Dict[str, Any]]:
        """默认策略组"""
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
