#!/usr/bin/env python3
"""
测试AI辅助线绘制功能
需要配置AI API才能运行
"""

import sys
import os

# 添加signal_monitor到路径
signal_monitor_path = os.path.join(os.path.dirname(__file__), '..', 'signal_monitor')
sys.path.insert(0, signal_monitor_path)

from chart_pro_v10 import get_klines
from pattern_detection_enhanced import detect_patterns_enhanced
from ai_pattern_drawer import draw_ai_patterns
from ai_market_summary import get_ai_summary_config
import json


def test_ai_pattern_drawing(symbol: str = 'BTC'):
    """测试AI辅助线绘制"""
    print(f"\n{'='*60}")
    print(f"测试AI辅助线绘制: {symbol}")
    print(f"{'='*60}")

    # 1. 检查AI配置
    print("\n--- 检查AI配置 ---")
    ai_config = get_ai_summary_config()
    if not ai_config or not ai_config.get('api_key'):
        print("❌ AI配置未找到")
        print("请在 signal_monitor/ai_summary_config.json 中配置:")
        print(json.dumps({
            "api_key": "your-api-key",
            "api_url": "https://api.openai.com/v1/chat/completions",
            "model": "gpt-4"
        }, indent=2))
        return

    print(f"✓ API URL: {ai_config.get('api_url')}")
    print(f"✓ Model: {ai_config.get('model')}")
    print(f"✓ API Key: {ai_config.get('api_key')[:10]}...")

    # 2. 获取数据
    print(f"\n--- 获取数据 ---")
    df = get_klines(symbol, timeframe='1h', limit=200)
    if df is None or df.empty:
        print(f"❌ 无法获取 {symbol} 的K线数据")
        return

    current_price = float(df['close'].iloc[-1])
    print(f"✓ 当前价格: ${current_price:,.2f}")
    print(f"✓ K线数量: {len(df)}")

    # 3. 本地形态检测
    print(f"\n--- 本地形态检测 ---")
    local_patterns = detect_patterns_enhanced(df, current_price)

    detected_count = sum(1 for p in local_patterns.values() if p)
    print(f"检测到 {detected_count} 个形态:")

    for name, pattern in local_patterns.items():
        if pattern:
            print(f"  - {name}: {pattern.get('type')}, 得分={pattern.get('score', 0):.2%}")

    # 4. AI辅助线绘制
    print(f"\n--- AI辅助线绘制 ---")
    try:
        language = os.getenv('VALUESCAN_LANGUAGE', 'zh').lower()
        pattern_lines = draw_ai_patterns(
            symbol, df, current_price, local_patterns, ai_config, language
        )

        if not pattern_lines:
            print("⚠ AI未返回形态线条，使用本地形态")
        else:
            print(f"✓ AI识别了 {len(pattern_lines)} 条线:")

            for i, line in enumerate(pattern_lines, 1):
                source = line.get('source', 'UNKNOWN')
                pattern_type = line.get('pattern_type', 'unknown')
                confidence = line.get('confidence', 0)
                role = line.get('role', 'unknown')
                label = line.get('label', '')

                print(f"\n  线条 {i}:")
                print(f"    来源: {source}")
                print(f"    形态: {pattern_type}")
                print(f"    角色: {role}")
                print(f"    标签: {label}")
                print(f"    置信度: {confidence:.2%}")

                if 'touch_count' in line:
                    print(f"    触碰次数: {line['touch_count']}")

                x1, y1 = line.get('x1'), line.get('y1')
                x2, y2 = line.get('x2'), line.get('y2')
                print(f"    坐标: ({x1:.0f}, ${y1:.2f}) -> ({x2:.0f}, ${y2:.2f})")

    except Exception as e:
        print(f"❌ AI辅助线绘制失败: {e}")
        import traceback
        traceback.print_exc()

    # 5. 生成图表
    print(f"\n--- 生成图表 ---")
    try:
        from chart_pro_v10 import generate_chart_v10

        # 临时启用AI overlays
        import config as signal_config
        original_value = getattr(signal_config, 'ENABLE_AI_OVERLAYS', False)
        signal_config.ENABLE_AI_OVERLAYS = True

        img_data = generate_chart_v10(symbol, interval='1h', limit=200)

        # 恢复原值
        signal_config.ENABLE_AI_OVERLAYS = original_value

        if img_data:
            output_path = f'output/test_ai_patterns_{symbol}.png'
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
    print("="*60)
    print("AI辅助线绘制测试")
    print("="*60)

    # 测试多个币种
    test_symbols = ['BTC', 'ETH']

    for symbol in test_symbols:
        try:
            test_ai_pattern_drawing(symbol)
        except Exception as e:
            print(f"\n❌ 测试 {symbol} 时发生错误: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'='*60}")
    print("测试完成!")
    print(f"{'='*60}")
    print("\n提示:")
    print("- 如果AI配置正确，应该能看到AI识别的形态线条")
    print("- 如果AI未配置或失败，会自动使用本地形态检测")
    print("- 生成的图表会显示所有识别的形态")


if __name__ == '__main__':
    main()
