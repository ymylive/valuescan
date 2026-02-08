#!/usr/bin/env python3
"""
测试增强版关键位算法
对比原算法和增强版算法的效果
"""

import sys
import os

# 添加signal_monitor到路径
signal_monitor_path = os.path.join(os.path.dirname(__file__), '..', 'signal_monitor')
sys.path.insert(0, signal_monitor_path)

from chart_pro_v10 import generate_chart_v10, get_klines, get_orderbook
from key_levels_pro import find_key_levels_professional
from key_levels_enhanced import find_key_levels_enhanced
from ai_key_levels_cache import get_levels as get_ai_levels
import json


def test_symbol(symbol: str):
    """测试单个币种"""
    print(f"\n{'='*60}")
    print(f"测试币种: {symbol}")
    print(f"{'='*60}")

    # 获取数据
    df = get_klines(symbol, timeframe='1h', limit=200)
    if df is None or df.empty:
        print(f"❌ 无法获取 {symbol} 的K线数据")
        return

    current_price = float(df['close'].iloc[-1])
    orderbook = get_orderbook(symbol, limit=100)

    print(f"当前价格: ${current_price:,.2f}")

    # 1. 测试原算法
    print(f"\n--- 原算法 (key_levels_pro) ---")
    try:
        old_supports, old_resistances = find_key_levels_professional(df, current_price, orderbook)
        print(f"支撑位: {[f'${s:,.2f}' for s in old_supports]}")
        print(f"阻力位: {[f'${r:,.2f}' for r in old_resistances]}")
    except Exception as e:
        print(f"❌ 原算法失败: {e}")
        old_supports, old_resistances = [], []

    # 2. 测试增强版算法 (不使用AI)
    print(f"\n--- 增强版算法 (无AI) ---")
    try:
        new_supports, new_resistances, metadata = find_key_levels_enhanced(
            df, current_price, orderbook, market_cap=None, ai_levels=None
        )
        print(f"支撑位: {[f'${s:,.2f}' for s in new_supports]}")
        print(f"阻力位: {[f'${r:,.2f}' for r in new_resistances]}")
        print(f"元数据:")
        print(f"  - 数据源: {metadata.get('source')}")
        print(f"  - 合并阈值: {metadata.get('merge_threshold', 0):.2%}")
        print(f"  - 触碰容差: {metadata.get('touch_tolerance', 0):.2%}")
        print(f"  - 汇合阈值: {metadata.get('confluence_threshold', 0):.2%}")

        support_strengths = metadata.get('support_strengths', [])
        resistance_strengths = metadata.get('resistance_strengths', [])

        if support_strengths:
            print(f"  - 支撑位强度: {[f'{s:.0%}' for s in support_strengths]}")
        if resistance_strengths:
            print(f"  - 阻力位强度: {[f'{s:.0%}' for s in resistance_strengths]}")

    except Exception as e:
        print(f"❌ 增强版算法失败: {e}")
        import traceback
        traceback.print_exc()
        new_supports, new_resistances = [], []

    # 3. 测试增强版算法 (使用AI)
    print(f"\n--- 增强版算法 (使用AI) ---")
    try:
        ai_levels = get_ai_levels(symbol.replace('USDT', ''))
        if ai_levels:
            print(f"AI缓存数据: 支撑 {len(ai_levels.get('supports', []))} 个, 阻力 {len(ai_levels.get('resistances', []))} 个")

        ai_supports, ai_resistances, ai_metadata = find_key_levels_enhanced(
            df, current_price, orderbook, market_cap=None, ai_levels=ai_levels
        )
        print(f"支撑位: {[f'${s:,.2f}' for s in ai_supports]}")
        print(f"阻力位: {[f'${r:,.2f}' for r in ai_resistances]}")
        print(f"元数据:")
        print(f"  - 数据源: {ai_metadata.get('source')}")
        print(f"  - AI置信度: {ai_metadata.get('ai_confidence', 0):.0%}")

        ai_support_strengths = ai_metadata.get('support_strengths', [])
        ai_resistance_strengths = ai_metadata.get('resistance_strengths', [])

        if ai_support_strengths:
            print(f"  - 支撑位强度: {[f'{s:.0%}' for s in ai_support_strengths]}")
        if ai_resistance_strengths:
            print(f"  - 阻力位强度: {[f'{s:.0%}' for s in ai_resistance_strengths]}")

    except Exception as e:
        print(f"❌ 增强版算法(AI)失败: {e}")
        import traceback
        traceback.print_exc()

    # 4. 生成图表
    print(f"\n--- 生成图表 ---")
    try:
        img_data = generate_chart_v10(symbol, interval='1h', limit=200)
        if img_data:
            output_path = f'output/test_enhanced_{symbol}.png'
            os.makedirs('output', exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(img_data)
            print(f"✅ 图表已保存: {output_path}")
        else:
            print(f"❌ 图表生成失败")
    except Exception as e:
        print(f"❌ 图表生成失败: {e}")
        import traceback
        traceback.print_exc()


def main():
    """主函数"""
    # 测试多个币种
    test_symbols = ['BTC', 'ETH', 'SOL', 'BNB']

    print("="*60)
    print("增强版关键位算法测试")
    print("="*60)

    for symbol in test_symbols:
        try:
            test_symbol(symbol)
        except Exception as e:
            print(f"\n❌ 测试 {symbol} 时发生错误: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'='*60}")
    print("测试完成!")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
