#!/usr/bin/env python3
"""检查数据源是否正确"""
import sys
import os
sys.path.insert(0, '/root/valuescan')
sys.path.insert(0, '/root/valuescan/signal_monitor')
os.chdir('/root/valuescan/signal_monitor')

from ai_market_summary import (
    _fetch_binance_klines, 
    _analyze_klines, 
    _fetch_nofx_coin_data,
    _collect_major_coin_data
)

print("=" * 60)
print("测试 Binance K线数据")
print("=" * 60)

for symbol in ["BTC", "ETH"]:
    klines = _fetch_binance_klines(symbol, "1h", 5)
    if klines:
        latest = klines[-1]
        print(f"{symbol}: 最新价格 = ${latest['close']:,.2f}")
    else:
        print(f"{symbol}: 获取K线失败!")

print("\n" + "=" * 60)
print("测试 NOFX 量化数据")
print("=" * 60)

for symbol in ["BTC", "ETH"]:
    quant = _fetch_nofx_coin_data(symbol)
    if quant:
        price = quant.get("price", {})
        print(f"{symbol}: NOFX价格数据 = {price}")
    else:
        print(f"{symbol}: NOFX数据获取失败!")

print("\n" + "=" * 60)
print("测试完整数据收集")
print("=" * 60)

data = _collect_major_coin_data()
for symbol, info in data.items():
    kl_1h = info.get("klines_1h", {})
    print(f"{symbol}:")
    print(f"  1h K线: latest_price={kl_1h.get('latest_price')}, trend={kl_1h.get('trend')}")
    quant = info.get("quant", {})
    print(f"  量化数据: {quant.get('price', {})}")
