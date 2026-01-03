#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试新的AI分析和辅助线绘制系统
"""

import sys
import os
import time

# 设置UTF-8编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加signal_monitor到路径
signal_monitor_path = os.path.join(os.path.dirname(__file__), '..', 'signal_monitor')
sys.path.insert(0, signal_monitor_path)


def test_ai_analysis(symbol='BTC'):
    """测试AI市场分析"""
    print(f"\n{'='*60}")
    print(f"测试AI市场分析: {symbol}")
    print(f"{'='*60}\n")

    from chart_pro_v10 import get_klines, get_orderbook
    from ai_market_analysis import get_ai_market_analysis
    from ai_market_summary import get_ai_summary_config

    # 获取数据
    print("1. 获取市场数据...")
    df = get_klines(symbol, timeframe='1h', limit=200)
    if df is None or df.empty:
        print("❌ 无法获取K线数据")
        return False

    current_price = float(df['close'].iloc[-1])
    orderbook = get_orderbook(symbol, limit=100)

    print(f"✓ 当前价格: ${current_price:,.2f}")
    print(f"✓ K线数量: {len(df)}")
    print(f"✓ 订单簿: {len(orderbook.get('bids', []))} 买单, {len(orderbook.get('asks', []))} 卖单")

    # 获取AI配置
    ai_config = get_ai_summary_config()
    if not ai_config or not ai_config.get('api_key'):
        print("\n⚠ AI配置未找到，跳过AI分析测试")
        return True

    # 调用AI分析
    print(f"\n2. 调用AI进行全面分析...")
    print("   (这会把所有数据发送给AI，让AI做深度分析)")

    start_time = time.time()
    analysis = get_ai_market_analysis(
        symbol, df, current_price, orderbook, None, ai_config, 'zh'
    )
    elapsed = time.time() - start_time

    if not analysis:
        print(f"❌ AI分析失败")
        return False

    print(f"✓ AI分析完成 (耗时: {elapsed:.2f}秒)\n")

    # 显示分析结果
    print("="*60)
    print("AI分析结果")
    print("="*60)

    # 趋势
    if 'trend' in analysis:
        trend = analysis['trend']
        print(f"\n【趋势分析】")
        print(f"  方向: {trend.get('direction')}")
        print(f"  强度: {trend.get('strength')}/100")
        print(f"  描述: {trend.get('description')}")

    # 关键位
    if 'key_levels' in analysis:
        levels = analysis['key_levels']

        if 'supports' in levels and levels['supports']:
            print(f"\n【支撑位】")
            for i, item in enumerate(levels['supports'], 1):
                price = item.get('price')
                strength = item.get('strength')
                reason = item.get('reason')
                print(f"  {i}. ${price:,.2f} (强度: {strength}/100)")
                print(f"     理由: {reason}")

        if 'resistances' in levels and levels['resistances']:
            print(f"\n【阻力位】")
            for i, item in enumerate(levels['resistances'], 1):
                price = item.get('price')
                strength = item.get('strength')
                reason = item.get('reason')
                print(f"  {i}. ${price:,.2f} (强度: {strength}/100)")
                print(f"     理由: {reason}")

    # 形态
    if 'patterns' in analysis:
        patterns = analysis['patterns']
        print(f"\n【形态识别】")
        print(f"  检测到: {', '.join(patterns.get('detected', []))}")
        print(f"  主要形态: {patterns.get('primary', 'None')}")
        print(f"  描述: {patterns.get('description', '')}")

    # 情绪
    if 'sentiment' in analysis:
        sentiment = analysis['sentiment']
        print(f"\n【市场情绪】")
        print(f"  得分: {sentiment.get('score')}/100")
        print(f"  描述: {sentiment.get('description')}")

    # 动量
    if 'momentum' in analysis:
        momentum = analysis['momentum']
        print(f"\n【动量分析】")
        print(f"  得分: {momentum.get('score')}/100")
        print(f"  描述: {momentum.get('description')}")

    # 风险评估
    if 'risk_assessment' in analysis:
        risk = analysis['risk_assessment']
        print(f"\n【风险评估】")
        print(f"  等级: {risk.get('level')}")
        print(f"  因素: {', '.join(risk.get('factors', []))}")

    # 交易建议
    if 'trading_suggestion' in analysis:
        suggestion = analysis['trading_suggestion']
        print(f"\n【交易建议】")
        print(f"  操作: {suggestion.get('action')}")
        if 'entry_zone' in suggestion:
            entry = suggestion['entry_zone']
            print(f"  入场区间: ${entry[0]:,.2f} - ${entry[1]:,.2f}")
        if 'stop_loss' in suggestion:
            print(f"  止损: ${suggestion['stop_loss']:,.2f}")
        if 'take_profit' in suggestion:
            tp = suggestion['take_profit']
            print(f"  止盈: {', '.join([f'${p:,.2f}' for p in tp])}")
        print(f"  理由: {suggestion.get('reasoning')}")

    # 总结
    if 'summary' in analysis:
        print(f"\n【市场总结】")
        print(f"  {analysis['summary']}")

    print(f"\n{'='*60}\n")

    return True, analysis


def test_auxiliary_lines(symbol='BTC'):
    """测试辅助线绘制"""
    print(f"\n{'='*60}")
    print(f"测试辅助线绘制: {symbol}")
    print(f"{'='*60}\n")

    from chart_pro_v10 import get_klines
    from auxiliary_line_drawer import draw_auxiliary_lines_optimized

    # 获取数据
    df = get_klines(symbol, timeframe='1h', limit=200)
    if df is None or df.empty:
        print("❌ 无法获取K线数据")
        return False

    current_price = float(df['close'].iloc[-1])

    # 计算ATR
    high = df['high']
    low = df['low']
    close = df['close'].shift(1)
    import pandas as pd
    tr = pd.concat([high - low, (high - close).abs(), (low - close).abs()], axis=1).max(axis=1)
    atr = tr.rolling(14).mean().iloc[-1]

    print(f"当前价格: ${current_price:,.2f}")
    print(f"ATR: ${atr:.2f}\n")

    # 绘制辅助线（不使用AI分析）
    print("1. 本地算法绘制辅助线...")
    lines = draw_auxiliary_lines_optimized(df, current_price, atr, ai_analysis=None)

    # 显示结果
    print(f"\n✓ 辅助线绘制完成\n")

    if lines['trendlines']:
        print(f"【趋势线】 ({len(lines['trendlines'])} 条)")
        for i, line in enumerate(lines['trendlines'], 1):
            print(f"  {i}. {line['type']}")
            print(f"     坐标: ({line['x1']:.0f}, ${line['y1']:.2f}) → ({line['x2']:.0f}, ${line['y2']:.2f})")
            print(f"     触碰: {line['touches']} 次")
            print(f"     得分: {line['score']:.1f}")

    if lines['channels']:
        print(f"\n【通道】 ({len(lines['channels'])} 个)")
        for i, channel in enumerate(lines['channels'], 1):
            print(f"  {i}. {channel['subtype']} channel")
            print(f"     上轨触碰: {channel['upper']['touches']} 次")
            print(f"     下轨触碰: {channel['lower']['touches']} 次")
            print(f"     总得分: {channel['score']:.1f}")

    if lines['zones']:
        print(f"\n【支撑/阻力区域】 ({len(lines['zones'])} 个)")
        for i, zone in enumerate(lines['zones'], 1):
            print(f"  {i}. {zone['subtype']}")
            print(f"     价格: ${zone['price_mid']:,.2f}")
            print(f"     范围: ${zone['price_min']:,.2f} - ${zone['price_max']:,.2f}")
            print(f"     强度: {zone['strength']:.1f}%")
            if 'source' in zone:
                print(f"     来源: {zone['source']}")
            if 'reason' in zone:
                print(f"     理由: {zone['reason']}")

    return True, lines


def main():
    """主函数"""
    print("="*60)
    print("新AI分析和辅助线绘制系统测试")
    print("="*60)

    symbol = 'BTC'

    # 测试AI分析
    result = test_ai_analysis(symbol)
    if isinstance(result, tuple):
        ai_success, ai_analysis = result
    else:
        ai_success = result
        ai_analysis = None

    # 测试辅助线绘制
    result = test_auxiliary_lines(symbol)
    if isinstance(result, tuple):
        lines_success, lines_data = result
    else:
        lines_success = result
        lines_data = None

    # 如果有AI分析，测试结合AI的辅助线绘制
    if ai_analysis and lines_data is not None:
        print(f"\n{'='*60}")
        print(f"测试结合AI分析的辅助线绘制")
        print(f"{'='*60}\n")

        from chart_pro_v10 import get_klines
        from auxiliary_line_drawer import draw_auxiliary_lines_optimized

        df = get_klines(symbol, timeframe='1h', limit=200)
        current_price = float(df['close'].iloc[-1])

        import pandas as pd
        high = df['high']
        low = df['low']
        close = df['close'].shift(1)
        tr = pd.concat([high - low, (high - close).abs(), (low - close).abs()], axis=1).max(axis=1)
        atr = tr.rolling(14).mean().iloc[-1]

        print("使用AI分析结果增强辅助线...")
        enhanced_lines = draw_auxiliary_lines_optimized(df, current_price, atr, ai_analysis=ai_analysis)

        print(f"\n✓ 增强版辅助线绘制完成")
        print(f"  - 趋势线: {len(enhanced_lines['trendlines'])} 条")
        print(f"  - 通道: {len(enhanced_lines['channels'])} 个")
        print(f"  - 区域: {len(enhanced_lines['zones'])} 个 (包含AI关键位)")

    # 总结
    print(f"\n{'='*60}")
    print("测试总结")
    print(f"{'='*60}")
    print(f"AI分析: {'✓ 通过' if ai_success else '✗ 失败'}")
    print(f"辅助线绘制: {'✓ 通过' if lines_success else '✗ 失败'}")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    main()
