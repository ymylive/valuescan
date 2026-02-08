#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ValuScan 币种详情查询模块
提供简洁的接口供其他组件通过币种名称获取详细数据
"""
import json
import time
from typing import Any, Dict, List, Optional
from pathlib import Path

# 导入客户端
try:
    from .client import ValuScanClient
except ImportError:
    from client import ValuScanClient


# 全局客户端实例
_client: Optional[ValuScanClient] = None

# 币种名称到 keyword 的映射缓存
_symbol_cache: Dict[str, int] = {}


def _extract_dense_points(resp: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not isinstance(resp, dict):
        return []
    data = resp.get("data")
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("list", "records", "items"):
            if isinstance(data.get(key), list):
                return data.get(key) or []
    return []


def _point_time_ms(point: Dict[str, Any]) -> int:
    for key in ("time", "ts", "timestamp", "dateTime", "date"):
        value = point.get(key) if isinstance(point, dict) else None
        if value is None:
            continue
        try:
            ts = int(float(value))
        except Exception:
            continue
        if ts <= 0:
            continue
        return ts if ts > 10**12 else ts * 1000
    return 0


def _filter_points_by_days(points: List[Dict[str, Any]], days: int) -> List[Dict[str, Any]]:
    if days <= 0:
        return points
    cutoff_ms = int(time.time() * 1000) - days * 24 * 60 * 60 * 1000
    return [p for p in points if _point_time_ms(p) >= cutoff_ms]


def _format_trade_pairs(symbol: str) -> str:
    base = symbol.upper().replace("$", "").replace("USDT", "").strip()
    return f"{base}USDT" if base else symbol.upper().strip()



def _get_client() -> ValuScanClient:
    """获取客户端实例"""
    global _client
    if _client is None:
        _client = ValuScanClient()
    return _client


def _load_symbol_cache():
    """加载币种符号缓存"""
    global _symbol_cache
    if _symbol_cache:
        return
    
    # 尝试从缓存文件加载
    cache_file = Path(__file__).parent / "data" / "symbol_cache.json"
    if cache_file.exists():
        try:
            _symbol_cache = json.loads(cache_file.read_text(encoding="utf-8"))
            return
        except Exception:
            pass
    
    # 从 API 加载
    client = _get_client()
    page = 1
    while True:
        resp = client.list_all_coins(page=page, page_size=100)
        if resp.get("code") != 200:
            break
        
        coins = resp.get("data", {}).get("list", [])
        if not coins:
            break
        
        for coin in coins:
            symbol = (coin.get("symbol") or "").upper()
            keyword = coin.get("vsTokenId") or coin.get("keyword")
            if symbol and keyword:
                _symbol_cache[symbol] = int(keyword)
        
        total = resp.get("data", {}).get("total", 0)
        if len(_symbol_cache) >= total:
            break
        page += 1
    
    # 保存缓存
    cache_file.parent.mkdir(exist_ok=True)
    cache_file.write_text(json.dumps(_symbol_cache, ensure_ascii=False), encoding="utf-8")



def get_keyword(symbol: str) -> Optional[int]:
    """???????? keyword (ID)."""
    _load_symbol_cache()
    symbol = symbol.upper().strip()

    # ?????
    if symbol in _symbol_cache:
        return _symbol_cache[symbol]

    client = _get_client()
    resp = client.search_keyword(symbol, page=1, page_size=20)
    if resp.get("code") == 200:
        data = resp.get("data") or {}
        items = []
        if isinstance(data, dict):
            items = data.get("list") or data.get("records") or data.get("items") or []
        elif isinstance(data, list):
            items = data
        for coin in items or []:
            symbol_val = (coin.get("symbol") or coin.get("tokenSymbol") or "").upper()
            if symbol_val == symbol:
                keyword = int(coin.get("vsTokenId") or coin.get("keyword") or 0)
                if keyword:
                    _symbol_cache[symbol] = keyword
                    return keyword

    # ?????????????
    resp = client._request("POST", "/api/vs-token/queryCoin", json_body={
        "search": symbol,
        "page": 1,
        "pageSize": 20
    })

    if resp.get("code") == 200:
        coins = resp.get("data", {}).get("list", [])
        for coin in coins:
            if (coin.get("symbol") or "").upper() == symbol:
                keyword = int(coin.get("vsTokenId") or coin.get("keyword") or 0)
                if keyword:
                    _symbol_cache[symbol] = keyword
                    return keyword

    return None


def get_detail(symbol: str) -> Dict[str, Any]:
    """
    通过币种符号获取完整详情
    
    Args:
        symbol: 币种符号，如 "BTC", "ETH", "SOL"
    
    Returns:
        包含完整详情的字典，结构如下:
        {
            "code": 200,
            "symbol": "ETH",
            "keyword": 1027,
            "basic": {...},       # 基础信息
            "ai_summary": {...},  # AI分析摘要
            "trade_inflow": {...},# 资金流入数据
            "exchange_info": {...}# 交易所信息
        }
    """
    keyword = get_keyword(symbol)
    if not keyword:
        return {"code": 404, "error": f"Coin '{symbol}' not found"}
    
    client = _get_client()
    result = client.get_coin_detail(keyword)
    
    if result.get("code") == 200:
        data = result.get("data", {})
        return {
            "code": 200,
            "symbol": symbol.upper(),
            "keyword": keyword,
            "basic": data.get("basic"),
            "ai_summary": data.get("ai_summary"),
            "trade_inflow": data.get("trade_inflow"),
            "exchange_info": data.get("exchange_info"),
            "exchange_flow_detail": data.get("exchange_flow_detail"),
            "fund_flow_history": data.get("fund_flow_history"),
            "fund_volume_history": data.get("fund_volume_history"),
            "holders_top": data.get("holders_top"),
            "chains": data.get("chains"),
        }
    
    return result


def get_basic(symbol: str) -> Dict[str, Any]:
    """
    获取币种基础信息（价格、市值、涨跌幅等）
    
    Args:
        symbol: 币种符号
    
    Returns:
        基础信息字典
    """
    keyword = get_keyword(symbol)
    if not keyword:
        return {"code": 404, "error": f"Coin '{symbol}' not found"}
    
    client = _get_client()
    resp = client._request("POST", "/api/vs-token/queryCoin", json_body={
        "search": symbol,
        "page": 1,
        "pageSize": 10
    })
    
    if resp.get("code") == 200:
        coins = resp.get("data", {}).get("list", [])
        for coin in coins:
            if (coin.get("symbol") or "").upper() == symbol.upper():
                return {"code": 200, "data": coin}
    
    return resp


def get_ai_analysis(symbol: str) -> Dict[str, Any]:
    """
    获取币种 AI 分析摘要
    
    Args:
        symbol: 币种符号
    
    Returns:
        AI分析摘要，包含看涨/看跌/中立情绪比例和多语言分析
    """
    keyword = get_keyword(symbol)
    if not keyword:
        return {"code": 404, "error": f"Coin '{symbol}' not found"}
    
    return _get_client().get_ai_summary(keyword)


def get_inflow(symbol: str) -> Dict[str, Any]:
    """
    获取币种资金流入数据
    
    Args:
        symbol: 币种符号
    
    Returns:
        资金流入数据
    """
    keyword = get_keyword(symbol)
    if not keyword:
        return {"code": 404, "error": f"Coin '{symbol}' not found"}
    
    return _get_client().get_trade_inflow(keyword)


def get_exchange_flow_detail(symbol: str) -> Dict[str, Any]:
    """
    Get exchange flow detail (in/out/net) for multiple time ranges.
    """
    keyword = get_keyword(symbol)
    if not keyword:
        return {"code": 404, "error": f"Coin '{symbol}' not found"}
    return _get_client().get_exchange_flow_detail(keyword)


def get_fund_trade_history_total(
    symbol: str,
    time_particle: str = "12h",
    limit_size: int = 100,
    flow: bool = True,
    trade_type: int = 2,
) -> Dict[str, Any]:
    """
    Get fund/volume history by time buckets.
    """
    keyword = get_keyword(symbol)
    if not keyword:
        return {"code": 404, "error": f"Coin '{symbol}' not found"}
    return _get_client().get_fund_trade_history_total(
        keyword,
        time_particle=time_particle,
        limit_size=limit_size,
        flow=flow,
        trade_type=trade_type,
    )


def get_holder_page(
    symbol: str,
    page: int = 1,
    page_size: int = 20,
    address: str = "",
    chain: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get top holders page for a coin.
    """
    keyword = get_keyword(symbol)
    if not keyword:
        return {"code": 404, "error": f"Coin '{symbol}' not found"}
    return _get_client().get_holder_page(
        keyword,
        page=page,
        page_size=page_size,
        address=address,
        symbol=symbol,
        chain=chain,
    )


def get_chain_page(symbol: str = "", page: int = 1, page_size: int = 20) -> Dict[str, Any]:
    """
    Get chain list for tokens (CMC chain page).
    """
    return _get_client().get_chain_page(symbol=symbol, page=page, page_size=page_size)


def get_kline_time() -> Dict[str, Any]:
    """Get ValueScan kline time reference."""
    return _get_client().get_kline_time()


def get_trade_kline_history(
    symbol: str,
    kline_type: str = "01",
    bucket_type: str = "1s",
    size: int = 300,
) -> Dict[str, Any]:
    """
    Get tradePairs kline history (ValueScan).
    """
    trade_pairs = _format_trade_pairs(symbol)
    return _get_client().get_trade_kline_history(
        trade_pairs,
        kline_type=kline_type,
        bucket_type=bucket_type,
        size=size,
    )


def get_trade_kline_miss(
    symbol: str,
    kline_type: str = "01",
    start: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Get missing ranges for tradePairs kline history.
    """
    trade_pairs = _format_trade_pairs(symbol)
    return _get_client().get_trade_kline_miss(
        trade_pairs,
        kline_type=kline_type,
        start=start,
    )


def get_kline(symbol: str) -> Dict[str, Any]:
    """
    获取币种K线数据
    
    Args:
        symbol: 币种符号
    
    Returns:
        K线数据
    """
    keyword = get_keyword(symbol)
    if not keyword:
        return {"code": 404, "error": f"Coin '{symbol}' not found"}
    
    return _get_client().get_coin_kline(keyword)



def get_main_force(symbol: str, days: int = 90) -> Dict[str, Any]:
    """??????????."""
    keyword = get_keyword(symbol)
    if not keyword:
        return {"code": 404, "error": f"Coin '{symbol}' not found"}

    client = _get_client()
    last_resp: Dict[str, Any] = {"code": 500, "error": "No dense area data"}
    last_points: List[Dict[str, Any]] = []

    candidate_days = [days, max(days * 2, 30), 60, 90]
    seen = set()
    for window in candidate_days:
        if window in seen:
            continue
        seen.add(window)
        resp = client.get_dense_area(keyword, window)
        last_resp = resp
        if resp.get("code") != 200:
            continue
        points = _extract_dense_points(resp)
        if not points:
            continue
        points_sorted = sorted(points, key=_point_time_ms)
        last_points = points_sorted
        has_timestamp = any(_point_time_ms(point) > 0 for point in points_sorted)
        if not has_timestamp and len(points_sorted) >= 2:
            return {"code": 200, "data": points_sorted}

        filtered = _filter_points_by_days(points_sorted, days)
        if len(filtered) >= 2:
            return {"code": 200, "data": filtered}

        widened = _filter_points_by_days(points_sorted, window)
        if len(widened) >= 2:
            return {"code": 200, "data": widened}

    if len(last_points) >= 2:
        return {"code": 200, "data": last_points[-2:]}
    if isinstance(last_resp, dict):
        return last_resp
    return {"code": 500, "error": "No dense area data"}


def get_detailed_inflow(symbol: str) -> Dict[str, Any]:
    """
    获取详细资金流入数据（含多个时间周期）
    
    Args:
        symbol: 币种符号
    
    Returns:
        包含多个时间周期(5m/15m/30m/1h/4h/8h/12h/24h/2d/3d/5d/7d等)的资金流入数据:
        - stopTradeInflow: 现货资金流入
        - contractTradeInflow: 合约资金流入
        - stopTradeAmount: 现货交易量
        - contractTradeAmount: 合约交易量
        - stopTradeInflowChange: 现货流入变化率
        - contractTradeInflowChange: 合约流入变化率
    """
    keyword = get_keyword(symbol)
    if not keyword:
        return {"code": 404, "error": f"Coin '{symbol}' not found"}
    
    return _get_client().get_detailed_inflow(keyword)


def get_kline_history(symbol: str, interval: str = "1h", limit: int = 500) -> Dict[str, Any]:
    """
    获取K线历史数据
    
    Args:
        symbol: 币种符号
        interval: K线间隔 (1m/5m/15m/30m/1h/4h/1d等)
        limit: 返回数量
    
    Returns:
        K线历史数据
    """
    keyword = get_keyword(symbol)
    if not keyword:
        return {"code": 404, "error": f"Coin '{symbol}' not found"}
    
    return _get_client().get_kline_history(keyword, interval, limit)


def search(query: str, limit: int = 20) -> List[Dict[str, Any]]:
    """
    搜索币种
    
    Args:
        query: 搜索关键词
        limit: 返回数量限制
    
    Returns:
        匹配的币种列表
    """
    client = _get_client()
    resp = client._request("POST", "/api/vs-token/queryCoin", json_body={
        "search": query,
        "page": 1,
        "pageSize": limit
    })
    
    if resp.get("code") == 200:
        return resp.get("data", {}).get("list", [])
    return []


def list_all(page: int = 1, page_size: int = 100) -> Dict[str, Any]:
    """
    获取所有币种列表
    
    Args:
        page: 页码
        page_size: 每页数量
    
    Returns:
        币种列表
    """
    return _get_client().list_all_coins(page, page_size)


def get_gainers(page: int = 1, page_size: int = 20) -> Dict[str, Any]:
    """获取涨幅榜"""
    return _get_client().get_coin_rank(rank_type=1, page=page, page_size=page_size)


def get_losers(page: int = 1, page_size: int = 20) -> Dict[str, Any]:
    """获取跌幅榜"""
    return _get_client().get_coin_rank(rank_type=1, page=page, page_size=page_size, asc=True)


def get_main_cost_rank(page: int = 1, page_size: int = 20) -> Dict[str, Any]:
    """
    获取主力成本排行榜
    
    Returns:
        包含 cost(主力成本), deviation(偏离度), costChange(成本变化) 等字段
    """
    return _get_client().get_quality_rank(page=page, page_size=page_size)


def get_hold_cost(symbol: str, days: int = 90) -> Dict[str, Any]:
    """
    获取主力成本数据（持仓成本曲线）
    
    API: /api/track/judge/coin/getHoldCost
    
    Args:
        symbol: 币种符号 (如 BTC, ETH)
        days: 查询天数，默认90天
    
    Returns:
        主力成本数据，包含:
        - holdingPrice: 每日主力成本价格 (如 BTC 的 $58,551.74)
        - price: 每日收盘价
        - balance: 每日余额
    """
    keyword = get_keyword(symbol)
    if not keyword:
        return {"code": 404, "msg": f"Symbol {symbol} not found"}
    return _get_client().get_hold_cost(keyword, days)


def get_token_flow(time_period: str = "H12", page: int = 1, page_size: int = 20) -> Dict[str, Any]:
    """
    获取代币流向数据
    
    Args:
        time_period: 时间周期 (H1/H4/H8/H12/D1/D2/D3/D7/D10/D15/D30/D60/D90/D120/D150/D180)
        page: 页码
        page_size: 每页数量
    
    Returns:
        代币流入流出数据
    """
    return _get_client().get_token_flow(time_period=time_period, page=page, page_size=page_size)


def get_whale_flow(trade_type: int = 1, time_period: str = "m5", page: int = 1, page_size: int = 20) -> Dict[str, Any]:
    """
    获取主力资金流榜单
    
    Args:
        trade_type: 1=现货, 2=合约
        time_period: 时间周期 (m5/m15/m30/h1/h4/h8/h12/h24等)
        page: 页码
        page_size: 每页数量
    
    Returns:
        主力资金流数据
    """
    return _get_client().get_whale_flow(trade_type=trade_type, time_period=time_period, page=page, page_size=page_size)


def get_ai_signals(trade_type: int = 2, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
    """
    获取AI智能选币信号（异动看涨监控）
    
    Args:
        trade_type: 1=现货, 2=合约
        page: 页码
        page_size: 每页数量
    
    Returns:
        AI选币信号列表
    """
    return _get_client().get_ai_signals(trade_type=trade_type, page=page, page_size=page_size)


def get_opportunity_signals(page: int = 1, page_size: int = 20) -> Dict[str, Any]:
    """
    获取机会看涨监控信号（AI评分系统）
    
    Returns:
        机会代币列表，包含AI评分、情绪、涨跌幅等
    """
    return _get_client().get_opportunity_signals(page=page, page_size=page_size)


def get_risk_signals(page: int = 1, page_size: int = 20) -> Dict[str, Any]:
    """
    获取风险看跌监控信号
    
    Returns:
        风险代币列表，包含AI评分、风险等级、回撤等
    """
    return _get_client().get_risk_signals(page=page, page_size=page_size)


def get_all_coins() -> List[Dict[str, Any]]:
    """
    获取所有币种完整列表（自动分页）
    
    Returns:
        所有币种列表
    """
    all_coins = []
    page = 1
    page_size = 100
    
    while True:
        resp = _get_client().list_all_coins(page, page_size)
        if resp.get("code") != 200:
            break
        
        coins = resp.get("data", {}).get("list", [])
        if not coins:
            break
        
        all_coins.extend(coins)
        total = resp.get("data", {}).get("total", 0)
        
        if len(all_coins) >= total:
            break
        
        page += 1
    
    return all_coins


def save_all_coins(filepath: Optional[str] = None) -> str:
    """
    获取并保存所有币种信息到文件
    
    Args:
        filepath: 保存路径，默认为 data/all_coins.json
    
    Returns:
        保存的文件路径
    """
    import json
    from datetime import datetime
    
    coins = get_all_coins()
    
    if not filepath:
        data_dir = Path(__file__).parent / "data"
        data_dir.mkdir(exist_ok=True)
        filepath = str(data_dir / "all_coins.json")
    
    result = {
        "timestamp": datetime.now().isoformat(),
        "total": len(coins),
        "coins": coins
    }
    
    Path(filepath).write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    
    return filepath


# 便捷别名
detail = get_detail
basic = get_basic
ai = get_ai_analysis
inflow = get_inflow
kline = get_kline


# 使用示例
if __name__ == "__main__":
    print("=" * 60)
    print("ValuScan 币种详情查询测试")
    print("=" * 60)
    
    # 测试获取 ETH 详情
    print("\n1. 获取 ETH 详情:")
    eth = get_detail("ETH")
    if eth.get("code") == 200:
        print(f"   ✓ 符号: {eth.get('symbol')}")
        print(f"   ✓ Keyword: {eth.get('keyword')}")
        print(f"   ✓ 基础信息: {'OK' if eth.get('basic') else 'None'}")
        print(f"   ✓ AI摘要: {'OK' if eth.get('ai_summary') else 'None'}")
        print(f"   ✓ 资金流入: {'OK' if eth.get('trade_inflow') else 'None'}")
    else:
        print(f"   ✗ 错误: {eth.get('error')}")
    
    # 测试获取 BTC 基础信息
    print("\n2. 获取 BTC 基础信息:")
    btc = get_basic("BTC")
    if btc.get("code") == 200:
        data = btc.get("data", {})
        print(f"   ✓ 名称: {data.get('name')}")
        print(f"   ✓ 价格: ${data.get('price')}")
        print(f"   ✓ 24h涨跌: {data.get('percentChange24h')}%")
    
    # 测试搜索
    print("\n3. 搜索 'SOL':")
    results = search("SOL", limit=5)
    for r in results[:3]:
        print(f"   - {r.get('symbol')}: {r.get('name')}")
    
    print("\n" + "=" * 60)
    print("测试完成")
