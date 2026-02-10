#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整信息流测试
模拟从信号接收到图表生成的完整流程
"""

import sys
import os
import json
import time
from datetime import datetime

# 设置UTF-8编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加signal_monitor到路径
signal_monitor_path = os.path.join(os.path.dirname(__file__), '..', 'signal_monitor')
sys.path.insert(0, signal_monitor_path)


def print_section(title):
    """打印分节标题"""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}\n")


def test_configuration():
    """测试配置"""
    print_section("1. 配置检查")

    try:
        import config as signal_config

        print("✓ 配置文件加载成功")
        print(f"  - 语言: {signal_config.LANGUAGE}")
        print(f"  - 启用Telegram: {signal_config.ENABLE_TELEGRAM}")
        print(f"  - 启用Pro图表: {signal_config.ENABLE_PRO_CHART}")
        print(f"  - 启用AI主力位: {signal_config.ENABLE_AI_KEY_LEVELS}")
        print(f"  - 启用AI辅助线: {signal_config.ENABLE_AI_OVERLAYS}")
        print(f"  - 启用AI简评: {signal_config.ENABLE_AI_SIGNAL_ANALYSIS}")

        # 检查AI配置
        try:
            config_path = os.path.join(signal_monitor_path, 'ai_summary_config.json')
            with open(config_path, 'r', encoding='utf-8') as f:
                ai_config = json.load(f)
            print(f"\n✓ AI配置加载成功")
            print(f"  - API URL: {ai_config.get('api_url')}")
            print(f"  - Model: {ai_config.get('model')}")
            print(f"  - API Key: {ai_config.get('api_key')[:10]}...")
        except Exception as e:
            print(f"\n✗ AI配置加载失败: {e}")

        return True

    except Exception as e:
        print(f"✗ 配置加载失败: {e}")
        return False


def test_data_fetching(symbol='BTC'):
    """测试数据获取"""
    print_section("2. 数据获取测试")

    try:
        from chart_pro_v10 import get_klines, get_orderbook

        # 获取K线数据
        print(f"获取 {symbol} K线数据...")
        df = get_klines(symbol, timeframe='1h', limit=200)

        if df is None or df.empty:
            print(f"✗ 无法获取K线数据")
            return False

        current_price = float(df['close'].iloc[-1])
        print(f"✓ K线数据获取成功")
        print(f"  - 数据量: {len(df)} 根K线")
        print(f"  - 当前价格: ${current_price:,.2f}")
        print(f"  - 时间范围: {df['timestamp'].iloc[0]} ~ {df['timestamp'].iloc[-1]}")

        # 获取订单簿
        print(f"\n获取 {symbol} 订单簿...")
        orderbook = get_orderbook(symbol, limit=100)

        if orderbook:
            print(f"✓ 订单簿获取成功")
            print(f"  - 买单数量: {len(orderbook.get('bids', []))}")
            print(f"  - 卖单数量: {len(orderbook.get('asks', []))}")
        else:
            print(f"⚠ 订单簿获取失败（不影响主流程）")

        return True, df, current_price, orderbook

    except Exception as e:
        print(f"✗ 数据获取失败: {e}")
        import traceback
        traceback.print_exc()
        return False, None, None, None


def test_key_levels(df, current_price, orderbook):
    """测试关键位检测"""
    print_section("3. 关键位检测测试")

    try:
        from key_levels_enhanced import find_key_levels_enhanced
        from ai_key_levels_cache import get_levels as get_ai_levels

        # 检查AI缓存
        print("检查AI关键位缓存...")
        ai_levels = get_ai_levels('BTC')
        if ai_levels:
            print(f"✓ 找到AI缓存")
            print(f"  - 支撑位: {len(ai_levels.get('supports', []))} 个")
            print(f"  - 阻力位: {len(ai_levels.get('resistances', []))} 个")
        else:
            print(f"⚠ 无AI缓存（将使用本地算法）")

        # 使用增强版算法
        print(f"\n使用增强版算法检测关键位...")
        supports, resistances, metadata = find_key_levels_enhanced(
            df, current_price, orderbook, market_cap=None, ai_levels=ai_levels
        )

        print(f"✓ 关键位检测完成")
        print(f"  - 数据源: {metadata.get('source')}")
        print(f"  - AI置信度: {metadata.get('ai_confidence', 0):.2%}")
        print(f"  - 合并阈值: {metadata.get('merge_threshold', 0):.2%}")
        print(f"  - 触碰容差: {metadata.get('touch_tolerance', 0):.2%}")

        print(f"\n支撑位 ({len(supports)} 个):")
        for i, (s, strength) in enumerate(zip(supports, metadata.get('support_strengths', [])), 1):
            print(f"  {i}. ${s:,.2f} (强度: {strength:.0%})")

        print(f"\n阻力位 ({len(resistances)} 个):")
        for i, (r, strength) in enumerate(zip(resistances, metadata.get('resistance_strengths', [])), 1):
            print(f"  {i}. ${r:,.2f} (强度: {strength:.0%})")

        return True

    except Exception as e:
        print(f"✗ 关键位检测失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_pattern_detection(df, current_price):
    """测试形态检测"""
    print_section("4. 形态检测测试")

    try:
        from pattern_detection_enhanced import detect_patterns_enhanced

        print("使用增强版算法检测形态...")
        patterns = detect_patterns_enhanced(df, current_price)

        detected_count = sum(1 for p in patterns.values() if p)
        print(f"✓ 形态检测完成，检测到 {detected_count} 个形态\n")

        for pattern_name, pattern_data in patterns.items():
            if not pattern_data:
                print(f"  {pattern_name}: 未检测到")
                continue

            print(f"  {pattern_name.upper()}:")
            print(f"    - 类型: {pattern_data.get('type')}")
            print(f"    - 得分: {pattern_data.get('score', 0):.2%}")
            print(f"    - 强度: {pattern_data.get('strength', 0):.2%}")
            print(f"    - 窗口: {pattern_data.get('window')} 根K线")

            # 突破预测
            breakout = pattern_data.get('breakout', {})
            if breakout:
                print(f"    - 突破预测: {breakout.get('direction')}, "
                      f"目标${breakout.get('target', 0):,.2f}, "
                      f"置信度{breakout.get('confidence', 0):.0%}")

        return True, patterns

    except Exception as e:
        print(f"✗ 形态检测失败: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def test_ai_pattern_drawing(symbol, df, current_price, local_patterns):
    """测试AI辅助线绘制"""
    print_section("5. AI辅助线绘制测试")

    try:
        from ai_pattern_drawer import draw_ai_patterns
        from ai_market_summary import get_ai_summary_config

        # 获取AI配置
        ai_config = get_ai_summary_config()
        if not ai_config or not ai_config.get('api_key'):
            print("⚠ AI配置未找到，跳过AI辅助线测试")
            return True, []

        print("调用AI API识别形态...")
        start_time = time.time()

        pattern_lines = draw_ai_patterns(
            symbol, df, current_price, local_patterns, ai_config, 'zh'
        )

        elapsed = time.time() - start_time

        if not pattern_lines:
            print(f"⚠ AI未返回形态线条（耗时: {elapsed:.2f}秒）")
            return True, []

        print(f"✓ AI识别完成（耗时: {elapsed:.2f}秒）")
        print(f"  - 识别了 {len(pattern_lines)} 条线\n")

        for i, line in enumerate(pattern_lines, 1):
            source = line.get('source', 'UNKNOWN')
            pattern_type = line.get('pattern_type', 'unknown')
            confidence = line.get('confidence', 0)
            role = line.get('role', 'unknown')
            label = line.get('label', '')

            print(f"  线条 {i}:")
            print(f"    - 来源: {source}")
            print(f"    - 形态: {pattern_type}")
            print(f"    - 角色: {role}")
            print(f"    - 标签: {label}")
            print(f"    - 置信度: {confidence:.0%}")

            if 'touch_count' in line:
                print(f"    - 触碰次数: {line['touch_count']}")

        return True, pattern_lines

    except Exception as e:
        print(f"✗ AI辅助线绘制失败: {e}")
        import traceback
        traceback.print_exc()
        return False, []


def test_chart_generation(symbol):
    """测试图表生成"""
    print_section("6. 图表生成测试")

    try:
        from chart_pro_v10 import generate_chart_v10

        print(f"生成 {symbol} 图表...")
        start_time = time.time()

        img_data = generate_chart_v10(symbol, interval='1h', limit=200)

        elapsed = time.time() - start_time

        if not img_data:
            print(f"✗ 图表生成失败")
            return False

        # 保存图表
        output_path = f'output/test_complete_flow_{symbol}.png'
        os.makedirs('output', exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(img_data)

        size_kb = len(img_data) / 1024
        print(f"✓ 图表生成成功")
        print(f"  - 文件大小: {size_kb:.1f} KB")
        print(f"  - 生成耗时: {elapsed:.2f} 秒")
        print(f"  - 保存路径: {output_path}")

        return True

    except Exception as e:
        print(f"✗ 图表生成失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_message_handler():
    """测试消息处理"""
    print_section("7. 消息处理测试")

    try:
        from message_handler import MessageHandler
        from database import Database

        # 初始化
        db = Database()
        handler = MessageHandler(db)

        print("✓ 消息处理器初始化成功")

        # 模拟一个信号
        mock_signal = {
            'id': f'test_{int(time.time())}',
            'symbol': 'BTC',
            'type': 'LONG',
            'title': '测试信号 - BTC多单',
            'content': '这是一个测试信号',
            'timestamp': datetime.now().isoformat(),
            'price': 87415.50,
        }

        print(f"\n模拟信号:")
        print(f"  - 币种: {mock_signal['symbol']}")
        print(f"  - 类型: {mock_signal['type']}")
        print(f"  - 标题: {mock_signal['title']}")
        print(f"  - 价格: ${mock_signal['price']:,.2f}")

        print(f"\n⚠ 注意: 实际的Telegram发送需要配置Bot Token")

        return True

    except Exception as e:
        print(f"✗ 消息处理测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试流程"""
    print("="*60)
    print("完整信息流测试")
    print("="*60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    results = {}

    # 1. 配置检查
    results['config'] = test_configuration()
    if not results['config']:
        print("\n❌ 配置检查失败，终止测试")
        return

    # 2. 数据获取
    symbol = 'BTC'
    result = test_data_fetching(symbol)
    if isinstance(result, tuple):
        results['data'], df, current_price, orderbook = result
    else:
        results['data'] = result
        df, current_price, orderbook = None, None, None

    if not results['data']:
        print("\n❌ 数据获取失败，终止测试")
        return

    # 3. 关键位检测
    results['key_levels'] = test_key_levels(df, current_price, orderbook)

    # 4. 形态检测
    result = test_pattern_detection(df, current_price)
    if isinstance(result, tuple):
        results['patterns'], local_patterns = result
    else:
        results['patterns'] = result
        local_patterns = None

    # 5. AI辅助线绘制
    result = test_ai_pattern_drawing(symbol, df, current_price, local_patterns or {})
    if isinstance(result, tuple):
        results['ai_patterns'], pattern_lines = result
    else:
        results['ai_patterns'] = result

    # 6. 图表生成
    results['chart'] = test_chart_generation(symbol)

    # 7. 消息处理
    results['message'] = test_message_handler()

    # 总结
    print_section("测试总结")

    total = len(results)
    passed = sum(1 for v in results.values() if v)

    print(f"测试项目: {total}")
    print(f"通过: {passed}")
    print(f"失败: {total - passed}")
    print(f"成功率: {passed/total*100:.1f}%\n")

    for name, result in results.items():
        status = "✓" if result else "✗"
        print(f"  {status} {name}")

    if passed == total:
        print(f"\n🎉 所有测试通过！")
    else:
        print(f"\n⚠ 部分测试失败，请检查日志")

    print(f"\n{'='*60}")


if __name__ == '__main__':
    main()
