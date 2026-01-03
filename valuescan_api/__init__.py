#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ValuScan API 模块
提供 ValuScan 数据获取和币种详情查询功能

使用示例:
    from valuescan_api import get_detail, get_basic, search
    
    # 通过币种名称获取完整详情
    eth = get_detail("ETH")
    
    # 获取基础信息
    btc = get_basic("BTC")
    
    # 搜索币种
    results = search("SOL")
"""

from .client import ValuScanClient, get_client
from .coin_detail import (
    get_detail,
    get_basic,
    get_ai_analysis,
    get_inflow,
    get_exchange_flow_detail,
    get_fund_trade_history_total,
    get_holder_page,
    get_chain_page,
    get_kline_time,
    get_trade_kline_history,
    get_trade_kline_miss,
    get_kline,
    get_keyword,
    search,
    list_all,
    get_all_coins,
    save_all_coins,
    get_main_force,
    get_detailed_inflow,
    get_kline_history,
    get_gainers,
    get_losers,
    get_main_cost_rank,
    get_hold_cost,
    get_token_flow,
    get_whale_flow,
    get_ai_signals,
    get_opportunity_signals,
    get_risk_signals,
    detail,
    basic,
    ai,
    inflow,
    kline,
)

__all__ = [
    "ValuScanClient",
    "get_client",
    "get_detail",
    "get_basic", 
    "get_ai_analysis",
    "get_inflow",
    "get_exchange_flow_detail",
    "get_fund_trade_history_total",
    "get_holder_page",
    "get_chain_page",
    "get_kline_time",
    "get_trade_kline_history",
    "get_trade_kline_miss",
    "get_kline",
    "get_keyword",
    "search",
    "list_all",
    "get_all_coins",
    "save_all_coins",
    "get_main_force",
    "get_detailed_inflow",
    "get_kline_history",
    "get_gainers",
    "get_losers",
    "get_main_cost_rank",
    "get_hold_cost",
    "get_token_flow",
    "get_whale_flow",
    "get_ai_signals",
    "get_opportunity_signals",
    "get_risk_signals",
    "detail",
    "basic",
    "ai",
    "inflow",
    "kline",
]
