#!/usr/bin/env python3
"""测试主力位和主力成本数据 - 区分两个概念"""
from valuescan_api import get_main_force, get_hold_cost
from datetime import datetime

print("=" * 70)
print("【重要】主力位 vs 主力成本 - 两个不同的概念")
print("=" * 70)
print()
print("1. 主力位 = 图表上的绿色水平线")
print("   API: /api/dense/getDenseAreaKLineHistory")
print("   函数: get_main_force()")
print()
print("2. 主力成本 = 持仓成本曲线 (页面显示的 '持仓成本')")
print("   API: /api/track/judge/coin/getHoldCost")
print("   函数: get_hold_cost()")
print()

# =============== 第一部分: 主力位数据 ===============
print("=" * 70)
print("【主力位】BTC - 图表上的绿色水平线")
print("=" * 70)

mf = get_main_force("BTC", days=90)
print(f"Code: {mf.get('code')}")

data = mf.get('data', [])
print(f"数据点数量: {len(data)}")
print()

if data:
    prices = [float(d.get('price', 0)) for d in data]
    current = prices[-1]
    
    print(f"【当前主力位】: ${current:,.2f}")
    print(f"【最高主力位】: ${max(prices):,.2f}")
    print(f"【最低主力位】: ${min(prices):,.2f}")
    print(f"【平均主力位】: ${sum(prices)/len(prices):,.2f}")
    print()
    
    print("最近10个数据点:")
    print(f"{'时间':<20} {'主力位价格':>15}")
    print("-" * 40)
    for d in data[-10:]:
        ts = d.get('time', 0) / 1000
        dt = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
        price = float(d.get('price', 0))
        print(f"{dt:<20} ${price:>14,.2f}")

# ETH 主力位
print()
print("=" * 60)
print("ETH 主力位线")
print("=" * 60)

mf_eth = get_main_force("ETH", days=90)
print(f"Code: {mf_eth.get('code')}")
data_eth = mf_eth.get('data', [])
print(f"数据点数量: {len(data_eth)}")

if data_eth:
    prices_eth = [float(d.get('price', 0)) for d in data_eth]
    print(f"【当前主力位】: ${prices_eth[-1]:,.2f}")
    print(f"【最高主力位】: ${max(prices_eth):,.2f}")
    print(f"【最低主力位】: ${min(prices_eth):,.2f}")

print()
print("=" * 60)
print("数据结构说明")
print("=" * 60)
print("""
每个数据点包含:
- time:  时间戳 (毫秒)
- type:  类型 (2 = 主力位)
- price: 主力位价格 (绿色线的Y轴值)

使用示例:
>>> from valuescan_api import get_main_force
>>> mf = get_main_force("BTC", days=90)
>>> current_cost = float(mf['data'][-1]['price'])
>>> print(f"BTC当前主力位: ${current_cost:,.2f}")
""")
