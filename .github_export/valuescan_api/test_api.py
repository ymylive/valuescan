#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ValuScan API 测试脚本
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from client import ValuScanClient


def test_api():
    """测试 API 客户端"""
    client = ValuScanClient()
    
    print("=" * 60)
    print("ValuScan API 测试")
    print("=" * 60)
    
    # 测试信号
    print("\n1. 获取预警信号...")
    warn = client.get_warn_messages()
    if warn.get("code") == 200:
        data = warn.get("data") or []
        print(f"   ✓ 获取到 {len(data)} 条预警信号")
    else:
        print(f"   ✗ 失败: {warn.get('error') or warn.get('msg')}")
    
    # 测试 AI 信号
    print("\n2. 获取 AI 信号...")
    ai = client.get_ai_messages()
    if ai.get("code") == 200:
        data = ai.get("data") or {}
        records = data.get("records") or data.get("list") or []
        print(f"   ✓ 获取到 {len(records)} 条 AI 信号")
    else:
        print(f"   ✗ 失败: {ai.get('error') or ai.get('msg')}")
    
    # 测试涨幅榜
    print("\n3. 获取涨幅榜...")
    gainers = client.get_gainers(page_size=5)
    if gainers.get("code") == 200:
        data = gainers.get("data") or {}
        records = data.get("records") or []
        print(f"   ✓ 获取到 {len(records)} 条涨幅榜数据")
        for r in records[:3]:
            symbol = r.get("symbol", "?")
            change = r.get("percentChange24h", 0)
            print(f"      - {symbol}: {change:+.2f}%")
    else:
        print(f"   ✗ 失败: {gainers.get('error') or gainers.get('msg')}")
    
    # 测试跌幅榜
    print("\n4. 获取跌幅榜...")
    losers = client.get_losers(page_size=5)
    if losers.get("code") == 200:
        data = losers.get("data") or {}
        records = data.get("records") or []
        print(f"   ✓ 获取到 {len(records)} 条跌幅榜数据")
        for r in records[:3]:
            symbol = r.get("symbol", "?")
            change = r.get("percentChange24h", 0)
            print(f"      - {symbol}: {change:+.2f}%")
    else:
        print(f"   ✗ 失败: {losers.get('error') or losers.get('msg')}")
    
    # 测试资金异动
    print("\n5. 获取资金异动...")
    movement = client.get_funds_movement(page_size=5)
    if movement.get("code") == 200:
        data = movement.get("data") or {}
        records = data.get("records") or data.get("list") or []
        print(f"   ✓ 获取到 {len(records)} 条资金异动")
    else:
        print(f"   ✗ 失败: {movement.get('error') or movement.get('msg')}")
    
    # 测试市场概览
    print("\n6. 获取市场概览...")
    overview = client.get_market_overview()
    if overview.get("code") == 200:
        data = overview.get("data") or {}
        print(f"   ✓ 市场概览获取成功")
        print(f"      - 信号: {len(data.get('signals', []))} 条")
        print(f"      - 涨幅榜: {len(data.get('gainers', []))} 条")
        print(f"      - 跌幅榜: {len(data.get('losers', []))} 条")
        print(f"      - 资金异动: {len(data.get('funds_movement', []))} 条")
    else:
        print(f"   ✗ 失败: {overview.get('error')}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    test_api()
