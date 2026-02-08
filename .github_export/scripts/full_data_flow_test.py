#!/usr/bin/env python3
"""Full ValuScan data flow test"""
import sys
sys.path.insert(0, str(__file__).rsplit('scripts', 1)[0])

from valuescan_api import (
    get_keyword, get_main_force, get_hold_cost,
    get_gainers, get_losers, get_main_cost_rank,
    get_opportunity_signals, get_risk_signals,
    get_whale_flow, get_token_flow,
)

def test_api(name, func, *args, **kwargs):
    try:
        result = func(*args, **kwargs)
        code = result.get("code")
        if code == 200:
            data = result.get("data", [])
            count = len(data) if isinstance(data, list) else 1
            print(f"✓ {name}: code={code}, items={count}")
            return True
        else:
            print(f"✗ {name}: code={code}, msg={result.get('msg', '')[:50]}")
            return False
    except Exception as e:
        print(f"✗ {name}: ERROR - {e}")
        return False

print("=" * 60)
print("ValuScan 完整数据调用流程检测")
print("=" * 60)

# 1. 币种ID映射
print("\n【1. 币种ID映射】")
btc_kw = get_keyword("BTC")
eth_kw = get_keyword("ETH")
sol_kw = get_keyword("SOL")
print(f"✓ BTC={btc_kw}, ETH={eth_kw}, SOL={sol_kw}")

# 2. 主力位数据
print("\n【2. 主力位数据 (绿色水平线)】")
test_api("BTC主力位", get_main_force, "BTC", 14)
test_api("ETH主力位", get_main_force, "ETH", 14)

# 3. 主力成本数据
print("\n【3. 主力成本数据】")
test_api("BTC主力成本", get_hold_cost, "BTC", 14)
test_api("ETH主力成本", get_hold_cost, "ETH", 14)

# 4. 排行榜
print("\n【4. 排行榜数据】")
test_api("涨幅榜", get_gainers, 1, 10)
test_api("跌幅榜", get_losers, 1, 10)
test_api("主力成本排行", get_main_cost_rank, 1, 10)

# 5. 信号
print("\n【5. 信号数据】")
test_api("机会信号", get_opportunity_signals, 1, 10)
test_api("风险信号", get_risk_signals, 1, 10)

# 6. 资金流
print("\n【6. 资金流数据】")
test_api("巨鲸资金流", get_whale_flow, 1, "m5", 1, 10)
test_api("代币资金流", get_token_flow, "H12", 1, 10)

print("\n" + "=" * 60)
print("检测完成")
print("=" * 60)
