#!/usr/bin/env python3
"""Test macro analysis function - no Telegram"""
import sys
import os

# Add paths
sys.path.insert(0, '/root/valuescan')
sys.path.insert(0, '/root/valuescan/signal_monitor')
os.chdir('/root/valuescan/signal_monitor')

import traceback
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

from ai_market_summary import (
    get_ai_summary_config, 
    _collect_major_coin_data,
    _fetch_oi_ranking,
    _collect_recent_signals,
    _fetch_crypto_news,
    _build_macro_analysis_prompt,
    _call_ai_api
)

try:
    config = get_ai_summary_config()
    
    print("=" * 60)
    print("收集数据中...")
    print("=" * 60)
    
    major_coin_data = _collect_major_coin_data()
    oi_ranking = _fetch_oi_ranking(limit=20, duration="1h")
    signals = _collect_recent_signals(1)
    news = _fetch_crypto_news()
    
    print(f"BTC/ETH 数据: {len(major_coin_data)} 币种")
    print(f"OI 排行: {len(oi_ranking) if isinstance(oi_ranking, list) else 0} 条")
    print(f"信号数据: {signals.get('total_count', 0)} 条")
    print(f"新闻数据: {len(news)} 条")
    
    print("\n" + "=" * 60)
    print("生成 AI 分析...")
    print("=" * 60)
    
    prompt = _build_macro_analysis_prompt(major_coin_data, oi_ranking, signals, news)
    result = _call_ai_api(prompt, config)
    
    print("\n" + "=" * 60)
    print("AI 输出结果:")
    print("=" * 60)
    
    # 保存完整输出到文件
    if result:
        with open("/tmp/ai_output.txt", "w", encoding="utf-8") as f:
            f.write(result)
        print("完整输出已保存到 /tmp/ai_output.txt")
        print("\n" + result)
    else:
        print("生成失败")
    
except Exception as e:
    print("Error:", e)
    traceback.print_exc()
