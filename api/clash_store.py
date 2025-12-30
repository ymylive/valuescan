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

    def _default_config(self) -> Dict[str, Any]:
        """默认配置"""
        return {
            'port': 7890,
            'socksPort': 7891,
            'allowLan': False,
            'mode': 'rule',
            'logLevel': 'info',
            'externalController': '127.0.0.1:9090',
            'secret': '',
            'subscriptions': [],
            'autoTest': True,
            'autoTestInterval': 30,
            'testUrl': 'http://www.gstatic.com/generate_204',
            'testTimeout': 5
        }
