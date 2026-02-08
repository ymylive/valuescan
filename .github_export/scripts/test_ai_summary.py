#!/usr/bin/env python3
"""
测试 AI 市场简评功能
"""

import sys
import time
from pathlib import Path

# Add signal_monitor to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'signal_monitor'))

def test_ai_summary():
    """测试 AI 简评生成"""
    print("=" * 80)
    print("测试 AI 市场简评功能")
    print("=" * 80)

    try:
        from ai_market_summary import generate_market_summary, get_ai_summary_config

        # 1. 检查配置
        print("\n[1/3] 检查配置...")
        config = get_ai_summary_config()
        print(f"   启用状态: {config.get('enabled')}")
        print(f"   API URL: {config.get('api_url', 'N/A')}")
        print(f"   模型: {config.get('model', 'N/A')}")
        print(f"   API Key: {'已配置' if config.get('api_key') else '未配置'}")
        print(f"   间隔时间: {config.get('interval_hours', 1)} 小时")
        print(f"   回溯时间: {config.get('lookback_hours', 1)} 小时")

        if not config.get('api_key'):
            print("\n❌ 错误: API Key 未配置")
            print("   请在 signal_monitor/ai_summary_config.json 中配置 api_key")
            return False

        # 2. 生成简评
        print("\n[2/3] 生成 AI 简评...")
        print("   这可能需要 30-60 秒，请耐心等待...")

        start_time = time.time()
        summary = generate_market_summary(force=True)
        elapsed = time.time() - start_time

        if summary:
            print(f"\n   ✅ 生成成功！耗时: {elapsed:.1f} 秒")
            print(f"   简评长度: {len(summary)} 字符")
            print("\n" + "=" * 80)
            print("生成的简评内容:")
            print("=" * 80)
            print(summary)
            print("=" * 80)
        else:
            print(f"\n   ❌ 生成失败！耗时: {elapsed:.1f} 秒")
            return False

        # 3. 验证 Telegram 发送
        print("\n[3/3] 验证 Telegram 发送...")
        print("   请检查 Telegram 群组是否收到消息")

        print("\n" + "=" * 80)
        print("✅ 测试完成！")
        print("=" * 80)
        return True

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_api_trigger():
    """测试 API 触发"""
    print("\n" + "=" * 80)
    print("测试 API 触发")
    print("=" * 80)

    try:
        import requests

        print("\n发送 POST 请求到 /api/valuescan/ai-summary/trigger...")
        response = requests.post('http://localhost:5000/api/valuescan/ai-summary/trigger', timeout=5)

        if response.status_code == 200:
            data = response.json()
            print(f"✅ API 响应成功:")
            print(f"   Status: {data.get('status')}")
            print(f"   Message: {data.get('message')}")
            print("\n   AI 简评正在后台生成，请等待 30-60 秒后检查 Telegram")
            return True
        else:
            print(f"❌ API 响应失败: {response.status_code}")
            print(f"   {response.text}")
            return False

    except Exception as e:
        print(f"❌ API 测试失败: {e}")
        return False

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='测试 AI 市场简评功能')
    parser.add_argument('--api', action='store_true', help='测试 API 触发（需要 API 服务器运行）')
    args = parser.parse_args()

    if args.api:
        success = test_api_trigger()
    else:
        success = test_ai_summary()

    sys.exit(0 if success else 1)
