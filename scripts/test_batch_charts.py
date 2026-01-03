#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量测试新系统
测试多个币种，验证系统稳定性和准确性
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


def test_symbol(symbol: str):
    """测试单个币种"""
    print(f"\n{'='*60}")
    print(f"测试: {symbol}")
    print(f"{'='*60}")

    from chart_pro_v10 import generate_chart_v10

    try:
        start_time = time.time()
        img = generate_chart_v10(symbol, interval='1h', limit=200)
        elapsed = time.time() - start_time

        if img:
            output_path = f'output/final_test_{symbol}.png'
            os.makedirs('output', exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(img)

            size_kb = len(img) / 1024
            print(f"✓ 成功")
            print(f"  - 大小: {size_kb:.1f} KB")
            print(f"  - 耗时: {elapsed:.2f} 秒")
            print(f"  - 路径: {output_path}")
            return True
        else:
            print(f"✗ 失败: 无图表数据")
            return False

    except Exception as e:
        print(f"✗ 失败: {e}")
        return False


def main():
    """主函数"""
    print("="*60)
    print("新系统批量测试")
    print("="*60)
    print(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    # 测试币种列表
    test_symbols = ['BTC', 'ETH', 'SOL', 'BNB']

    results = {}
    total_time = 0

    for symbol in test_symbols:
        start = time.time()
        success = test_symbol(symbol)
        elapsed = time.time() - start

        results[symbol] = success
        total_time += elapsed

    # 总结
    print(f"\n{'='*60}")
    print("测试总结")
    print(f"{'='*60}")

    total = len(results)
    passed = sum(1 for v in results.values() if v)

    print(f"测试币种: {total}")
    print(f"成功: {passed}")
    print(f"失败: {total - passed}")
    print(f"成功率: {passed/total*100:.1f}%")
    print(f"总耗时: {total_time:.2f} 秒")
    print(f"平均耗时: {total_time/total:.2f} 秒/币种")

    print(f"\n详细结果:")
    for symbol, success in results.items():
        status = "✓" if success else "✗"
        print(f"  {status} {symbol}")

    if passed == total:
        print(f"\n🎉 所有测试通过！")
    else:
        print(f"\n⚠ 部分测试失败")

    print(f"\n{'='*60}")


if __name__ == '__main__':
    main()
