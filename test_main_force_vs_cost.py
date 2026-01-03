#!/usr/bin/env python3
"""测试主力位 vs 主力成本 - 区分两个不同概念"""
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

if data:
    prices = [float(d.get('price', 0)) for d in data]
    current = prices[-1]
    
    print()
    print(f"【当前主力位】: ${current:,.2f}")
    print(f"【最高主力位】: ${max(prices):,.2f}")
    print(f"【最低主力位】: ${min(prices):,.2f}")
    print()
    
    print("最近5个数据点:")
    print(f"{'时间':<20} {'主力位价格':>15}")
    print("-" * 40)
    for d in data[-5:]:
        ts = d.get('time', 0) / 1000
        dt = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
        price = float(d.get('price', 0))
        print(f"{dt:<20} ${price:>14,.2f}")

# =============== 第二部分: 主力成本数据 ===============
print()
print("=" * 70)
print("【主力成本】BTC - 持仓成本曲线")
print("=" * 70)

hc = get_hold_cost("BTC", days=90)
print(f"Code: {hc.get('code')}")

if hc.get('code') == 200:
    hc_data = hc.get('data', {})
    holding = hc_data.get('holdingPrice', [])
    price_data = hc_data.get('price', [])
    
    print(f"数据天数: {len(holding)}")
    
    if holding:
        costs = [float(h.get('val', 0)) for h in holding]
        current_cost = costs[-1]
        
        print()
        print(f"【当前主力成本】: ${current_cost:,.2f}")
        print(f"【最高主力成本】: ${max(costs):,.2f}")
        print(f"【最低主力成本】: ${min(costs):,.2f}")
        print()
        
        print("最近5天主力成本:")
        print(f"{'日期':<15} {'主力成本':>15} {'当日价格':>15}")
        print("-" * 50)
        for i, h in enumerate(holding[-5:]):
            date = h.get('key', 'N/A')
            cost = float(h.get('val', 0))
            # 获取对应日期的价格
            if i < len(price_data[-5:]):
                p = float(price_data[-5:][i].get('val', 0))
                print(f"{date:<15} ${cost:>14,.2f} ${p:>14,.2f}")
            else:
                print(f"{date:<15} ${cost:>14,.2f}")

# =============== 总结 ===============
print()
print("=" * 70)
print("总结对比")
print("=" * 70)
if data and hc.get('code') == 200:
    print()
    print(f"BTC 当前主力位 (绿色线): ${float(data[-1].get('price', 0)):,.2f}")
    print(f"BTC 当前主力成本 (持仓成本): ${float(holding[-1].get('val', 0)):,.2f}")
    print()
    print("主力位: 每隔一段时间更新的关键价位线")
    print("主力成本: 每日更新的平均持仓成本")
