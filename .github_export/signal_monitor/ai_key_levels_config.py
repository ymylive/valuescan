#!/usr/bin/env python3
"""
AI 主力位分析配置模块

功能：
1. 管理 AI 主力位分析的独立配置
2. 支持 JSON 配置文件和环境变量
3. 提供配置加载/保存接口
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

# 默认配置
AI_LEVELS_ENABLED = os.getenv("VALUESCAN_AI_LEVELS_ENABLED", "1") == "1"
AI_LEVELS_API_KEY = os.getenv("VALUESCAN_AI_LEVELS_API_KEY", "Qq159741").strip()
AI_LEVELS_API_URL = os.getenv(
    "VALUESCAN_AI_LEVELS_API_URL",
    "https://chat.cornna.xyz/gemini/v1/chat/completions"
).strip()
AI_LEVELS_MODEL = os.getenv("VALUESCAN_AI_LEVELS_MODEL", "gemini-3-flash-preview-search").strip()


def _load_config() -> Dict[str, Any]:
    """从配置文件加载 AI 主力位配置"""
    config_path = Path(__file__).parent / "ai_key_levels_config.json"
    if config_path.exists():
        try:
            return json.loads(config_path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(f"加载 AI 主力位配置失败: {e}")
    return {}


def _save_config(config: Dict[str, Any]) -> bool:
    """保存 AI 主力位配置"""
    config_path = Path(__file__).parent / "ai_key_levels_config.json"
    try:
        config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(f"AI 主力位配置已保存: {config_path}")
        return True
    except Exception as e:
        logger.error(f"保存 AI 主力位配置失败: {e}")
        return False


def get_ai_levels_config() -> Dict[str, Any]:
    """
    获取 AI 主力位配置

    优先级：JSON 文件 > 环境变量 > 默认值

    Returns:
        配置字典，包含 enabled, api_key, api_url, model
    """
    file_config = _load_config()

    # 如果 JSON 配置不存在，尝试从 ai_summary_config.json 迁移
    if not file_config:
        try:
            from ai_market_summary import _load_config as load_summary_config
            summary_config = load_summary_config()
            if summary_config:
                logger.info("从 ai_summary_config.json 迁移配置到 AI 主力位")
                file_config = {
                    "enabled": summary_config.get("enabled", True),
                    "api_key": summary_config.get("api_key", ""),
                    "api_url": summary_config.get("api_url", ""),
                    "model": summary_config.get("model", ""),
                }
                # 保存迁移后的配置
                _save_config(file_config)
        except Exception as e:
            logger.debug(f"配置迁移失败: {e}")

    return {
        "enabled": file_config.get("enabled", AI_LEVELS_ENABLED),
        "api_key": file_config.get("api_key", AI_LEVELS_API_KEY),
        "api_url": file_config.get("api_url", AI_LEVELS_API_URL),
        "model": file_config.get("model", AI_LEVELS_MODEL),
    }


def update_ai_levels_config(config: Dict[str, Any]) -> bool:
    """
    更新 AI 主力位配置

    Args:
        config: 配置字典

    Returns:
        bool: 保存成功返回 True，否则返回 False
    """
    return _save_config(config)


def main():
    """测试入口"""
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    parser = argparse.ArgumentParser(description="AI 主力位配置管理")
    parser.add_argument("--show", action="store_true", help="显示当前配置")
    parser.add_argument("--set-key", type=str, help="设置 API Key")
    parser.add_argument("--set-url", type=str, help="设置 API URL")
    parser.add_argument("--set-model", type=str, help="设置模型名称")
    parser.add_argument("--enable", action="store_true", help="启用 AI 主力位")
    parser.add_argument("--disable", action="store_true", help="禁用 AI 主力位")
    args = parser.parse_args()

    if args.show:
        config = get_ai_levels_config()
        print("当前配置:")
        print(json.dumps(config, ensure_ascii=False, indent=2))
    elif args.set_key or args.set_url or args.set_model or args.enable or args.disable:
        config = get_ai_levels_config()
        if args.set_key:
            config["api_key"] = args.set_key
        if args.set_url:
            config["api_url"] = args.set_url
        if args.set_model:
            config["model"] = args.set_model
        if args.enable:
            config["enabled"] = True
        if args.disable:
            config["enabled"] = False

        if update_ai_levels_config(config):
            print("配置已更新:")
            print(json.dumps(config, ensure_ascii=False, indent=2))
        else:
            print("配置更新失败")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
