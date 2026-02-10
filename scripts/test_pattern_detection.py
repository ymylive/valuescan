#!/usr/bin/env python3
"""
测试增强版形态检测和AI辅助线绘制
"""

import sys
import os

# 添加signal_monitor到路径
signal_monitor_path = os.path.join(os.path.dirname(__file__), '..', 'signal_monitor')
sys.path.insert(0, signal_monitor_path)

from chart_pro_v10 import generate_chart_v10, get_klines
from pattern_detection_enhanced import detect_patterns_enhanced, PatternDetector
import json


def test_pattern_detection(symbol: str):
    """测试形态检测"""
    print(f"\n{'='*60}")
    print(f"测试币种: {symbol}")
    print(f"{'='*60}")

    # 获取数据
    df = get_klines(symbol, timeframe='1h', limit=200)
    if df is None or df.empty:
        print(f"❌ 无法获取 {symbol} 的K线数据")
        return

    current_price = float(df['close'].iloc[-1])
    print(f"当前价格: ${current_price:,.2f}")

    # 测试增强版形态检测
    print(f"\n--- 增强版形态检测 ---")
    try:
        patterns = detect_patterns_enhanced(df, current_price)

        for pattern_name, pattern_data in patterns.items():
            if not pattern_data:
                print(f"{pattern_name}: 未检测到")
                continue

            print(f"\n{pattern_name.upper()}:")
            print(f"  类型: {pattern_data.get('type')}")
            print(f"  得分: {pattern_data.get('score', 0):.2%}")
            print(f"  强度: {pattern_data.get('strength', 0):.2%}")
            print(f"  窗口: {pattern_data.get('window')} 根K线")

            # 触碰信息
            touch_upper = pattern_data.get('touch_count_upper', 0)
            touch_lower = pattern_data.get('touch_count_lower', 0)
            print(f"  触碰次数: 上轨 {touch_upper}, 下轨 {touch_lower}")

            # 突破预测
            breakout = pattern_data.get('breakout', {})
            if breakout:
                print(f"  突破预测:")
                print(f"    方向: {breakout.get('direction')}")
                print(f"    目标: ${breakout.get('target', 0):,.2f}")
                print(f"    置信度: {breakout.get('confidence', 0):.2%}")

            # 其他特征
            if 'parallel_score' in pattern_data:
                print(f"  平行度: {pattern_data['parallel_score']:.2%}")
            if 'convergence' in pattern_data:
                print(f"  收敛度: {pattern_data['convergence']:.2%}")
            if 'impulse_pct' in pattern_data:
                print(f"  冲动波: {pattern_data['impulse_pct']:.2%}")

    except Exception as e:
        print(f"❌ 形态检测失败: {e}")
        import traceback
        traceback.print_exc()

    # 生成图表
    print(f"\n--- 生成图表 ---")
    try:
        img_data = generate_chart_v10(symbol, interval='1h', limit=200)
        if img_data:
            output_path = f'output/test_patterns_{symbol}.png'
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


def compare_detectors(symbol: str):
    """对比原算法和增强版算法"""
    print(f"\n{'='*60}")
    print(f"对比测试: {symbol}")
    print(f"{'='*60}")

    df = get_klines(symbol, timeframe='1h', limit=200)
    if df is None or df.empty:
        print(f"❌ 无法获取数据")
        return

    current_price = float(df['close'].iloc[-1])
    atr = (df['high'] - df['low']).rolling(14).mean().iloc[-1]

    print(f"当前价格: ${current_price:,.2f}")
    print(f"ATR: ${atr:,.2f}")

    # 原算法
    print(f"\n--- 原算法 ---")
    try:
        from chart_pro_v10 import detect_channel, detect_best_wedge, detect_best_triangle, detect_best_flag

        old_channel = detect_channel(df, atr=atr)
        old_wedge = detect_best_wedge(df, atr=atr)
        old_triangle = detect_best_triangle(df, atr=atr)
        old_flag = detect_best_flag(df, atr=atr)

        print(f"通道: {'✓' if old_channel else '✗'} {old_channel.get('score', 0):.2%}" if old_channel else "通道: ✗")
        print(f"楔形: {'✓' if old_wedge else '✗'} {old_wedge.get('score', 0):.2%}" if old_wedge else "楔形: ✗")
        print(f"三角形: {'✓' if old_triangle else '✗'} {old_triangle.get('score', 0):.2%}" if old_triangle else "三角形: ✗")
        print(f"旗形: {'✓' if old_flag else '✗'} {old_flag.get('score', 0):.2%}" if old_flag else "旗形: ✗")

    except Exception as e:
        print(f"❌ 原算法失败: {e}")

    # 增强版算法
    print(f"\n--- 增强版算法 ---")
    try:
        new_patterns = detect_patterns_enhanced(df, current_price, atr)

        for name, pattern in new_patterns.items():
            if pattern:
                score = pattern.get('score', 0)
                strength = pattern.get('strength', 0)
                print(f"{name}: ✓ 得分={score:.2%}, 强度={strength:.2%}")
            else:
                print(f"{name}: ✗")

    except Exception as e:
        print(f"❌ 增强版算法失败: {e}")
        import traceback
        traceback.print_exc()


def main():
    """主函数"""
    test_symbols = ['BTC', 'ETH', 'SOL', 'BNB']

    print("="*60)
    print("增强版形态检测测试")
    print("="*60)

    # 详细测试
    for symbol in test_symbols:
        try:
            test_pattern_detection(symbol)
        except Exception as e:
            print(f"\n❌ 测试 {symbol} 时发生错误: {e}")
            import traceback
            traceback.print_exc()

    # 对比测试
    print(f"\n\n{'='*60}")
    print("算法对比测试")
    print(f"{'='*60}")

    for symbol in test_symbols[:2]:  # 只对比前两个
        try:
            compare_detectors(symbol)
        except Exception as e:
            print(f"\n❌ 对比 {symbol} 时发生错误: {e}")

    print(f"\n{'='*60}")
    print("测试完成!")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
