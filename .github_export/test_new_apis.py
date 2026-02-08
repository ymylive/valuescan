#!/usr/bin/env python3
"""测试新集成的 API"""
from valuescan_api import (
    get_gainers, get_losers, get_main_cost_rank, get_token_flow,
    get_whale_flow, get_ai_signals, get_opportunity_signals, get_risk_signals,
    get_main_force, get_detailed_inflow, get_kline_history,
    get_detail, get_basic, get_ai_analysis, get_keyword
)

print("=" * 60)
print("ValuScan API 测试")
print("=" * 60)

# 1. 涨幅榜
print("\n1. 涨幅榜 (get_gainers):")
g = get_gainers(page_size=5)
print(f"   Code: {g.get('code')}")
if g.get('code') == 200:
    for c in g.get('data', {}).get('list', [])[:3]:
        print(f"   - {c.get('symbol')}: {c.get('percentChange24h')}%")

# 2. 主力资金流
print("\n2. 主力资金流 (get_whale_flow):")
w = get_whale_flow(trade_type=1, time_period="m5", page_size=5)
print(f"   Code: {w.get('code')}")
if w.get('code') == 200:
    for c in w.get('data', {}).get('list', [])[:3]:
        print(f"   - {c.get('symbol')}: 净流入 ${c.get('tradeInflow', 0):,.0f}")

# 3. AI异动信号
print("\n3. AI异动信号 (get_ai_signals):")
a = get_ai_signals(trade_type=2, page_size=5)
print(f"   Code: {a.get('code')}")
if a.get('code') == 200:
    for c in a.get('data', {}).get('list', [])[:3]:
        alpha = "Alpha" if c.get('alpha') else ""
        fomo = "FOMO" if c.get('fomo') else ""
        tags = f"[{alpha}{fomo}]" if alpha or fomo else ""
        print(f"   - {c.get('symbol')} {tags}: 涨{c.get('gains', 0):.2f}%")

# 4. 机会看涨
print("\n4. 机会看涨 (get_opportunity_signals):")
o = get_opportunity_signals(page_size=5)
print(f"   Code: {o.get('code')}")
if o.get('code') == 200:
    for c in o.get('data', {}).get('list', [])[:3]:
        print(f"   - {c.get('symbol')}: 评分{c.get('score', 0)}")

# 5. 风险看跌
print("\n5. 风险看跌 (get_risk_signals):")
r = get_risk_signals(page_size=5)
print(f"   Code: {r.get('code')}")
if r.get('code') == 200:
    for c in r.get('data', {}).get('list', [])[:3]:
        print(f"   - {c.get('symbol')}: 评分{c.get('score', 0)} 等级{c.get('grade')}")

# 6. 代币流向
print("\n6. 代币流向 (get_token_flow):")
t = get_token_flow(time_period="H12", page_size=5)
print(f"   Code: {t.get('code')}")
if t.get('code') == 200:
    for c in t.get('data', {}).get('list', [])[:3]:
        print(f"   - {c.get('symbol')}: 净流入 ${float(c.get('inFlowValue', 0)):,.0f}")

# 7. 跌幅榜
print("\n7. 跌幅榜 (get_losers):")
l = get_losers(page_size=5)
print(f"   Code: {l.get('code')}")
if l.get('code') == 200:
    for c in l.get('data', {}).get('list', [])[:3]:
        print(f"   - {c.get('symbol')}: {c.get('percentChange24h')}%")

# 8. 主力成本
print("\n8. 主力成本 (get_main_cost_rank):")
m = get_main_cost_rank(page_size=5)
print(f"   Code: {m.get('code')}")
if m.get('code') == 200:
    for c in m.get('data', {}).get('list', [])[:3]:
        print(f"   - {c.get('symbol')}: 成本${c.get('cost', 'N/A')} 偏离{c.get('deviation', 'N/A')}%")

# 9. 主力位 (需要币种 keyword)
print("\n9. 主力位 (get_main_force) - BTC:")
keyword = get_keyword("BTC")
if keyword:
    mf = get_main_force("BTC", days=30)
    print(f"   Code: {mf.get('code')}")
    if mf.get('code') == 200:
        data = mf.get('data', [])
        if isinstance(data, list):
            print(f"   K线数据条数: {len(data)}")
            if len(data) > 0:
                first = data[0]
                print(f"   最新: 开{first.get('open', 'N/A')} 高{first.get('high', 'N/A')} 低{first.get('low', 'N/A')}")
        elif isinstance(data, dict):
            dense = data.get('denseAreaList', [])
            print(f"   密集区数量: {len(dense)}")
            for d in dense[:2]:
                print(f"   - 价格区间: ${d.get('lowPrice', 0):.0f} - ${d.get('highPrice', 0):.0f}")
else:
    print("   无法获取 BTC keyword")

# 10. 详细资金流入 (多周期)
print("\n10. 详细资金流入 (get_detailed_inflow) - ETH:")
di = get_detailed_inflow("ETH")
print(f"   Code: {di.get('code')}")
if di.get('code') == 200:
    data = di.get('data', {})
    if isinstance(data, dict):
        print(f"   周期数量: {len(data)}")
        for period, info in list(data.items())[:3]:
            if isinstance(info, dict):
                inflow = info.get('tradeInflow', 0)
                print(f"   - {period}: 净流入 ${float(inflow):,.0f}")
            else:
                print(f"   - {period}: {info}")
    elif isinstance(data, list):
        print(f"   数据条数: {len(data)}")
        for item in data[:3]:
            print(f"   - {item}")

# 11. 币种详情
print("\n11. 币种详情 (get_detail) - SOL:")
d = get_detail("SOL")
print(f"   Code: {d.get('code')}")
if d.get('code') == 200:
    data = d.get('data', {})
    basic = data.get('basic', {})
    print(f"   价格: ${basic.get('price', 'N/A')}")
    print(f"   市值: ${float(basic.get('marketCap', 0)):,.0f}")
    print(f"   24h涨跌: {basic.get('percentChange24h', 'N/A')}%")

# 12. AI分析
print("\n12. AI分析 (get_ai_analysis) - BTC:")
ai = get_ai_analysis("BTC")
print(f"   Code: {ai.get('code')}")
if ai.get('code') == 200:
    data = ai.get('data', {})
    if isinstance(data, list) and len(data) > 0:
        print(f"   分析条数: {len(data)}")
        print(f"   最新分析: {data[0].get('content', '')[:50]}...")
    elif isinstance(data, dict):
        print(f"   分析内容: {str(data)[:100]}...")

print("\n" + "=" * 60)
print("测试完成 - 共12项API全部测试")
print("=" * 60)
