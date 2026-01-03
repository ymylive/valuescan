#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ValuScan 数据 API 服务器
简单的 Flask API，提供 ValuScan 数据访问接口
"""
import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from client import ValuScanClient, get_client

app = Flask(__name__)
CORS(app)

# API 端口
API_PORT = int(os.getenv("VALUESCAN_DATA_API_PORT", "5100"))


def _resolve_keyword(symbol: str):
    result = get_client().get_coin_by_symbol(symbol)
    if result.get("code") == 200:
        data = result.get("data") or {}
        keyword = data.get("keyword")
        if keyword:
            try:
                return int(keyword), result
            except Exception:
                return None, result
    return None, result


@app.route('/health', methods=['GET'])
def health():
    """健康检查"""
    return jsonify({"status": "ok"})


# ==================== 信号相关 ====================

@app.route('/api/signals', methods=['GET'])
def get_signals():
    """获取所有信号"""
    return jsonify(get_client().get_all_signals())


@app.route('/api/signals/warn', methods=['GET'])
def get_warn_signals():
    """获取预警信号"""
    return jsonify(get_client().get_warn_messages())


@app.route('/api/signals/ai', methods=['GET', 'POST'])
def get_ai_signals():
    """获取 AI 信号"""
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('pageSize', 50))
    return jsonify(get_client().get_ai_messages(page, page_size))


# ==================== 资金异动 ====================

@app.route('/api/funds/movement', methods=['GET', 'POST'])
def get_funds_movement():
    """获取资金异动"""
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('pageSize', 20))
    chain = request.args.get('chain')
    movement_type = request.args.get('type')
    if movement_type:
        movement_type = int(movement_type)
    return jsonify(get_client().get_funds_movement(page, page_size, chain, movement_type))


@app.route('/api/funds/update', methods=['GET'])
def get_funds_update():
    """获取资金异动更新"""
    last_id = request.args.get('lastId')
    if last_id:
        last_id = int(last_id)
    return jsonify(get_client().get_funds_update(last_id))


# ==================== 涨跌榜 ====================

@app.route('/api/rank/gainers', methods=['GET'])
def get_gainers():
    """获取涨幅榜"""
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('pageSize', 20))
    time_range = request.args.get('range', '24h')
    return jsonify(get_client().get_gainers(page, page_size, time_range))


@app.route('/api/rank/losers', methods=['GET'])
def get_losers():
    """获取跌幅榜"""
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('pageSize', 20))
    time_range = request.args.get('range', '24h')
    return jsonify(get_client().get_losers(page, page_size, time_range))


# ==================== 代币信息 ====================

@app.route('/api/token/<symbol>', methods=['GET'])
def get_token_detail(symbol: str):
    """获取代币完整详情（通过符号）"""
    return jsonify(get_client().get_coin_by_symbol(symbol))


@app.route('/api/token/id/<int:keyword>', methods=['GET'])
def get_token_by_id(keyword: int):
    """获取代币完整详情（通过ID）"""
    return jsonify(get_client().get_coin_detail(keyword))


@app.route('/api/token/<symbol>/ai', methods=['GET'])
def get_token_ai_summary(symbol: str):
    """获取代币AI分析摘要"""
    # 先获取 keyword
    result = get_client().get_coin_by_symbol(symbol)
    if result.get("code") == 200:
        keyword = result.get("data", {}).get("keyword")
        if keyword:
            return jsonify(get_client().get_ai_summary(keyword))
    return jsonify(result)


@app.route('/api/token/<symbol>/exchange-flow-detail', methods=['GET'])
def get_token_exchange_flow_detail(symbol: str):
    """Get exchange flow detail for a coin."""
    keyword, result = _resolve_keyword(symbol)
    if not keyword:
        return jsonify(result)
    return jsonify(get_client().get_exchange_flow_detail(keyword))


@app.route('/api/token/<symbol>/fund-history', methods=['GET'])
def get_token_fund_history(symbol: str):
    """Get fund flow/volume history for a coin."""
    keyword, result = _resolve_keyword(symbol)
    if not keyword:
        return jsonify(result)
    time_particle = request.args.get('timeParticle', '12h')
    limit_size = int(request.args.get('limitSize', 60))
    flow_raw = request.args.get('flow', 'true').lower()
    flow = flow_raw not in {'0', 'false', 'no'}
    trade_type = int(request.args.get('type', 2))
    return jsonify(get_client().get_fund_trade_history_total(
        keyword,
        time_particle=time_particle,
        limit_size=limit_size,
        flow=flow,
        trade_type=trade_type,
    ))


@app.route('/api/token/<symbol>/holders', methods=['GET'])
def get_token_holders(symbol: str):
    """Get holder page for a coin."""
    keyword, result = _resolve_keyword(symbol)
    if not keyword:
        return jsonify(result)
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('pageSize', 20))
    address = request.args.get('address', '')
    chain = request.args.get('chain')
    return jsonify(get_client().get_holder_page(
        keyword,
        page=page,
        page_size=page_size,
        address=address,
        symbol=symbol,
        chain=chain,
    ))


@app.route('/api/token/chains', methods=['GET'])
def get_token_chains():
    """Get chain list for tokens."""
    symbol = request.args.get('symbol', '')
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('pageSize', 20))
    return jsonify(get_client().get_chain_page(symbol=symbol, page=page, page_size=page_size))


@app.route('/api/token/<symbol>/inflow', methods=['GET'])
def get_token_inflow(symbol: str):
    """获取代币资金流入"""
    result = get_client().get_coin_by_symbol(symbol)
    if result.get("code") == 200:
        keyword = result.get("data", {}).get("keyword")
        if keyword:
            return jsonify(get_client().get_trade_inflow(keyword))
    return jsonify(result)


@app.route('/api/coins', methods=['GET'])
def list_coins():
    """获取所有币种列表"""
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('pageSize', 100))
    is_binance = request.args.get('binance', '').lower() == 'true'
    return jsonify(get_client().list_all_coins(page, page_size, is_binance))


@app.route('/api/token/search', methods=['GET'])
def search_token():
    """搜索代币"""
    keyword = request.args.get('q', '')
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('pageSize', 20))
    return jsonify(get_client().search_token(keyword, page, page_size))


# ==================== K线数据 ====================

@app.route('/api/kline/<symbol>', methods=['GET'])
def get_kline(symbol: str):
    """获取K线数据"""
    interval = request.args.get('interval', '1h')
    limit = int(request.args.get('limit', 100))
    return jsonify(get_client().get_kline(symbol, interval, limit))


# ==================== 链上数据 ====================

@app.route('/api/analysis/holders/<symbol>', methods=['GET'])
def get_holder_analysis(symbol: str):
    """获取持仓分析"""
    chain = request.args.get('chain')
    return jsonify(get_client().get_holder_analysis(symbol, chain))


@app.route('/api/analysis/exchange-flow/<symbol>', methods=['GET'])
def get_exchange_flow(symbol: str):
    """获取交易所资金流向"""
    days = int(request.args.get('days', 7))
    return jsonify(get_client().get_exchange_flow(symbol, days))


@app.route('/api/analysis/onchain/<symbol>', methods=['GET'])
def get_onchain_activity(symbol: str):
    """获取链上活动"""
    return jsonify(get_client().get_onchain_activity(symbol))


# ==================== 热门和新币 ====================

@app.route('/api/trending', methods=['GET'])
def get_trending():
    """获取热门代币"""
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('pageSize', 20))
    return jsonify(get_client().get_trending(page, page_size))


@app.route('/api/new-listings', methods=['GET'])
def get_new_listings():
    """获取新上线代币"""
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('pageSize', 20))
    return jsonify(get_client().get_new_listings(page, page_size))


# ==================== 综合数据 ====================

@app.route('/api/overview', methods=['GET'])
def get_market_overview():
    """获取市场概览"""
    return jsonify(get_client().get_market_overview())


# ==================== API 文档 ====================

@app.route('/', methods=['GET'])
def index():
    """API 文档"""
    endpoints = {
        "信号": {
            "GET /api/signals": "获取所有信号",
            "GET /api/signals/warn": "获取预警信号",
            "GET /api/signals/ai": "获取AI信号 (page, pageSize)",
        },
        "资金异动": {
            "GET /api/funds/movement": "获取资金异动 (page, pageSize, chain, type)",
            "GET /api/funds/update": "获取资金异动更新 (lastId)",
        },
        "涨跌榜": {
            "GET /api/rank/gainers": "获取涨幅榜 (page, pageSize, range)",
            "GET /api/rank/losers": "获取跌幅榜 (page, pageSize, range)",
        },
        "代币信息": {
            "GET /api/token/<symbol>": "获取代币详情 (chain)",
            "GET /api/token/search": "搜索代币 (q, page, pageSize)",
        },
        "K线数据": {
            "GET /api/kline/<symbol>": "获取K线 (interval, limit)",
        },
        "链上分析": {
            "GET /api/analysis/holders/<symbol>": "持仓分析 (chain)",
            "GET /api/analysis/exchange-flow/<symbol>": "交易所流向 (days)",
            "GET /api/analysis/onchain/<symbol>": "链上活动",
        },
        "其他": {
            "GET /api/trending": "热门代币 (page, pageSize)",
            "GET /api/new-listings": "新上线代币 (page, pageSize)",
            "GET /api/overview": "市场概览",
        },
    }
    return jsonify({
        "name": "ValuScan Data API",
        "version": "1.0.0",
        "endpoints": endpoints,
    })


if __name__ == '__main__':
    print(f"Starting ValuScan Data API on port {API_PORT}")
    app.run(host='0.0.0.0', port=API_PORT, debug=True)
