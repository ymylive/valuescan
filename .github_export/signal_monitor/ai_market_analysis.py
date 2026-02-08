"""
AI市场分析模块（重新设计）
AI只负责分析，不负责绘制
优先使用 ValuScan 数据作为主力位和主力成本参考
"""

import json
import os
import requests
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
import pandas as pd
from logger import logger

# ValuScan 数据有效期配置
def _read_int_env_or_config(env_key: str, config_key: str, default: int) -> int:
    raw = os.getenv(env_key)
    if raw is not None and str(raw).strip() != "":
        try:
            return int(float(raw))
        except Exception:
            return default
    try:
        import config as signal_config
        value = getattr(signal_config, config_key, None)
        if value is None:
            return default
        return int(float(value))
    except Exception:
        return default


def _extract_valuescan_list(payload: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    data = payload.get("data")
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ("list", "records", "items", "data"):
            items = data.get(key)
            if isinstance(items, list):
                return [item for item in items if isinstance(item, dict)]
    return []


def _normalize_flow_period(value: Any) -> str:
    if value is None:
        return ""
    key = str(value).strip().lower().replace(" ", "")
    aliases = {
        "h1": "1h",
        "h4": "4h",
        "h12": "12h",
        "h24": "24h",
        "1d": "24h",
        "d1": "24h",
        "d": "24h",
        "m15": "15m",
    }
    return aliases.get(key, key)


def _first_float(item: Dict[str, Any], keys: Tuple[str, ...]) -> Optional[float]:
    for key in keys:
        value = item.get(key)
        if value is None:
            continue
        try:
            return float(value)
        except Exception:
            continue
    return None


def _extract_flow_items(data: Any) -> List[Dict[str, Any]]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ("list", "records", "items"):
            items = data.get(key)
            if isinstance(items, list):
                return [item for item in items if isinstance(item, dict)]
        items: List[Dict[str, Any]] = []
        for key, value in data.items():
            if isinstance(value, dict):
                item = dict(value)
                item.setdefault("timeType", key)
                items.append(item)
        return items
    return []


def _normalize_exchange_flow_detail(resp: Optional[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    if not isinstance(resp, dict) or resp.get("code") != 200:
        return {}
    items = _extract_flow_items(resp.get("data"))
    result: Dict[str, Dict[str, float]] = {}
    for item in items:
        period = _normalize_flow_period(
            item.get("timeType")
            or item.get("period")
            or item.get("time")
            or item.get("timeParticle")
        )
        if not period:
            continue
        in_val = _first_float(item, ("inFlowValue", "inFlow", "tradeIn", "stopTradeIn", "contractTradeIn"))
        out_val = _first_float(item, ("outFlowValue", "outFlow", "tradeOut", "stopTradeOut", "contractTradeOut"))
        net_val = _first_float(
            item,
            ("netFlowValue", "netFlow", "tradeInflow", "stopTradeInflow", "contractTradeInflow"),
        )
        if net_val is None and in_val is not None and out_val is not None:
            net_val = in_val - out_val
        if in_val is None and out_val is None and net_val is None:
            continue
        total = (in_val or 0.0) + (out_val or 0.0)
        ratio = (in_val or 0.0) / total if total > 0 else 0.5
        result[period] = {
            "in": float(in_val or 0.0),
            "out": float(out_val or 0.0),
            "net": float(net_val or 0.0),
            "ratio": float(ratio),
        }
    return result


def _compact_valuescan_history(resp: Optional[Dict[str, Any]], limit: int = 60) -> List[Dict[str, Any]]:
    items = _extract_valuescan_list(resp)
    if not items:
        return []
    return items[:limit]


def _compact_holder_items(resp: Optional[Dict[str, Any]], limit: int = 5) -> List[Dict[str, Any]]:
    items = _extract_valuescan_list(resp)
    if not items:
        return []
    trimmed: List[Dict[str, Any]] = []
    for item in items[:limit]:
        trimmed.append({
            "address": item.get("address"),
            "balance": item.get("balance"),
            "balancePercent": item.get("balancePercent"),
            "price": item.get("price"),
            "profit": item.get("profit"),
            "cost": item.get("cost"),
            "chainName": item.get("chainName"),
            "labelName": item.get("labelName") or item.get("label"),
        })
    return trimmed


def _compact_chain_items(resp: Optional[Dict[str, Any]], limit: int = 10) -> List[Dict[str, Any]]:
    items = _extract_valuescan_list(resp)
    if not items:
        return []
    trimmed: List[Dict[str, Any]] = []
    for item in items[:limit]:
        trimmed.append({
            "chainName": item.get("chainName"),
            "contractAddress": item.get("contractAddress"),
            "coinKey": item.get("coinKey"),
            "holderCount": item.get("holderCount"),
        })
    return trimmed


VALUESCAN_KEY_LEVELS_DAYS = _read_int_env_or_config(
    "VALUESCAN_KEY_LEVELS_CHART_DAYS",
    "VALUESCAN_KEY_LEVELS_DAYS",
    7,
)
VALUESCAN_AI_ANALYSIS_DAYS = _read_int_env_or_config(
    "VALUESCAN_AI_ANALYSIS_DAYS",
    "VALUESCAN_AI_ANALYSIS_DAYS",
    15,
)


def get_supplementary_data(symbol: str) -> Optional[Dict[str, Any]]:
    """获取补充数据（资金费率、持仓量、多空比、恐惧贪婪指数）"""
    try:
        from supplementary_data import get_all_supplementary_data
        return get_all_supplementary_data(symbol)
    except Exception as e:
        logger.debug(f"Failed to get supplementary data: {e}")
        return None


def get_valuescan_data(symbol: str, days: int = None) -> Optional[Dict[str, Any]]:
    """
    获取 ValuScan 所有数据（主力位、主力成本、资金流、信号等）
    这是 AI 分析系统的主要数据源，具有最高优先级
    
    返回数据包括：
    - main_force_levels: 主力位（阻力位参考）
    - main_cost: 主力成本（支撑位参考）
    - token_flow: 代币资金流向
    - whale_flow: 巨鲸资金流向
    - opportunity_signals: 机会信号
    - risk_signals: 风险信号
    """
    if days is None:
        days = VALUESCAN_AI_ANALYSIS_DAYS
    
    try:
        import sys
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if base_dir not in sys.path:
            sys.path.insert(0, base_dir)
        
        from valuescan_api import (
            get_main_force, get_hold_cost, get_keyword,
            get_token_flow, get_whale_flow,
            get_inflow, get_detailed_inflow,
            get_opportunity_signals, get_risk_signals,
            get_exchange_flow_detail, get_fund_trade_history_total,
            get_holder_page, get_chain_page,
        )
        
        clean_symbol = symbol.upper().replace("USDT", "").replace("$", "").strip()
        keyword = get_keyword(clean_symbol)
        if not keyword:
            logger.warning(f"ValuScan: No keyword found for {symbol}")
            return None
        
        result = {"symbol": clean_symbol, "days": days, "keyword": keyword}
        
        # 1. 主力位（阻力位）- 最重要
        mf = get_main_force(clean_symbol, days)
        if mf.get("code") == 200:
            mf_data = mf.get("data", [])
            if mf_data:
                levels = []
                for item in mf_data:
                    price = item.get("price")
                    if price is None:
                        continue
                    try:
                        levels.append(float(price))
                    except Exception:
                        continue
                if levels:
                    result["main_force_levels"] = levels
                    result["current_main_force"] = levels[-1]
                    logger.info(f"ValuScan: {clean_symbol} 主力位 ${result['current_main_force']:,.2f}")
        
        # 2. 主力成本（支撑位）- 最重要
        hc = get_hold_cost(clean_symbol, days)
        if hc.get("code") == 200:
            hc_data = hc.get("data", {}).get("holdingPrice", [])
            if hc_data:
                result["main_cost"] = float(hc_data[-1]["val"])
                logger.info(f"ValuScan: {clean_symbol} 主力成本 ${result['main_cost']:,.2f}")
        
        # 3. 代币资金流向
        try:
            tf = get_token_flow("H12", 1, 20)
            if tf.get("code") == 200:
                result["token_flow"] = tf.get("data", {})
        except Exception:
            pass

        # 3.1 交易资金流向（币种级）
        try:
            inflow = get_inflow(clean_symbol)
            if inflow.get("code") == 200:
                result["trade_inflow"] = inflow.get("data", {})
        except Exception:
            pass

        # 3.2 详细资金流向（多周期）
        try:
            detailed = get_detailed_inflow(clean_symbol)
            if detailed.get("code") == 200:
                result["detailed_inflow"] = detailed.get("data", {})
        except Exception:
            pass
        
        # 4. 巨鲸资金流向
        try:
            wf = get_whale_flow(1, "m5", 1, 20)
            if wf.get("code") == 200:
                result["whale_flow"] = wf.get("data", {})
        except Exception:
            pass
        
        # 5. 机会信号
        try:
            os_data = get_opportunity_signals(1, 10)
            if os_data.get("code") == 200:
                result["opportunity_signals"] = os_data.get("data", {})
        except Exception:
            pass
        
        # 6. 风险信号
        try:
            rs_data = get_risk_signals(1, 10)
            if rs_data.get("code") == 200:
                result["risk_signals"] = rs_data.get("data", {})
        except Exception:
            pass

        # 6. Exchange flow detail (multi-period)
        try:
            flow_detail = _normalize_exchange_flow_detail(get_exchange_flow_detail(clean_symbol))
            if flow_detail:
                result["exchange_flow_detail"] = flow_detail
        except Exception:
            pass

        # 7. Fund flow/volume history
        try:
            flow_history = _compact_valuescan_history(
                get_fund_trade_history_total(
                    clean_symbol,
                    time_particle="12h",
                    limit_size=60,
                    flow=True,
                    trade_type=2,
                ),
                limit=60,
            )
            if flow_history:
                result["fund_flow_history"] = flow_history
        except Exception:
            pass

        try:
            volume_history = _compact_valuescan_history(
                get_fund_trade_history_total(
                    clean_symbol,
                    time_particle="12h",
                    limit_size=60,
                    flow=False,
                    trade_type=2,
                ),
                limit=60,
            )
            if volume_history:
                result["fund_volume_history"] = volume_history
        except Exception:
            pass

        # 8. Holder and chain data
        try:
            holders = _compact_holder_items(get_holder_page(clean_symbol, page=1, page_size=10), limit=5)
            if holders:
                result["holders_top"] = holders
        except Exception:
            pass

        try:
            chains = _compact_chain_items(get_chain_page(clean_symbol, page=1, page_size=10), limit=10)
            if chains:
                result["chains"] = chains
        except Exception:
            pass

        return result if len(result) > 3 else None
        
    except Exception as e:
        logger.warning(f"ValuScan data fetch failed for {symbol}: {e}")
        return None


def build_comprehensive_analysis_prompt(
    symbol: str,
    df: pd.DataFrame,
    current_price: float,
    orderbook: Optional[Dict] = None,
    market_data: Optional[Dict] = None,
    language: str = "zh",
    valuescan_data: Optional[Dict] = None
) -> str:
    """
    构建全面的市场分析Prompt
    包含所有数据，让AI做深度分析
    增强版：优先使用 ValuScan 主力位和主力成本数据
    """
    # 获取 ValuScan 数据（如果未提供）
    if valuescan_data is None:
        valuescan_data = get_valuescan_data(symbol)
    # 准备K线数据（完整200根）
    klines = []
    if 'timestamp' in df.columns:
        ts_ms = (df['timestamp'].astype('int64') // 10**6).astype('int64')
        for i, row in df.reset_index(drop=True).iterrows():
            klines.append({
                'index': i,
                'ts': int(ts_ms.iloc[i]),
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
                'volume': float(row['volume']),
            })

    # 计算技术指标
    ema20 = df['close'].ewm(span=20, adjust=False).mean()
    ema50 = df['close'].ewm(span=50, adjust=False).mean()
    ema200 = df['close'].ewm(span=200, adjust=False).mean() if len(df) >= 200 else None

    # VWAP
    typical_price = (df['high'] + df['low'] + df['close']) / 3
    vwap = (typical_price * df['volume']).cumsum() / df['volume'].cumsum()

    # ATR
    high = df['high']
    low = df['low']
    close = df['close'].shift(1)
    tr = pd.concat([high - low, (high - close).abs(), (low - close).abs()], axis=1).max(axis=1)
    atr = tr.rolling(14).mean()

    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    # MACD
    ema12 = df['close'].ewm(span=12, adjust=False).mean()
    ema26 = df['close'].ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    histogram = macd - signal

    # 准备技术指标数据
    indicators = {
        'ema20': float(ema20.iloc[-1]),
        'ema50': float(ema50.iloc[-1]),
        'ema200': float(ema200.iloc[-1]) if ema200 is not None else None,
        'vwap': float(vwap.iloc[-1]),
        'atr': float(atr.iloc[-1]),
        'atr_percent': float(atr.iloc[-1] / current_price * 100),
        'rsi': float(rsi.iloc[-1]),
        'macd': float(macd.iloc[-1]),
        'macd_signal': float(signal.iloc[-1]),
        'macd_histogram': float(histogram.iloc[-1]),
    }

    # 准备订单簿数据
    orderbook_summary = {}
    if orderbook and isinstance(orderbook, dict):
        bids = orderbook.get('bids', [])[:20]
        asks = orderbook.get('asks', [])[:20]

        bid_notional = sum(p * a for p, a in bids)
        ask_notional = sum(p * a for p, a in asks)

        orderbook_summary = {
            'bid_depth': len(bids),
            'ask_depth': len(asks),
            'bid_notional': bid_notional,
            'ask_notional': ask_notional,
            'bid_ask_ratio': bid_notional / (ask_notional + 1e-9),
            'top_bid': float(bids[0][0]) if bids else None,
            'top_ask': float(asks[0][0]) if asks else None,
            'spread': float(asks[0][0] - bids[0][0]) if bids and asks else None,
            'spread_percent': float((asks[0][0] - bids[0][0]) / current_price * 100) if bids and asks else None,
        }

    # 准备市场数据（增强版）
    market_summary = market_data or {}

    # 添加价格变化统计
    price_changes = {
        '1h': float((df['close'].iloc[-1] - df['close'].iloc[-12]) / df['close'].iloc[-12] * 100) if len(df) >= 12 else None,
        '4h': float((df['close'].iloc[-1] - df['close'].iloc[-48]) / df['close'].iloc[-48] * 100) if len(df) >= 48 else None,
        '24h': float((df['close'].iloc[-1] - df['close'].iloc[-24]) / df['close'].iloc[-24] * 100) if len(df) >= 24 else None,
    }

    # 成交量分析
    volume_analysis = {
        'current': float(df['volume'].iloc[-1]),
        'avg_24h': float(df['volume'].tail(24).mean()) if len(df) >= 24 else None,
        'volume_trend': 'increasing' if df['volume'].iloc[-1] > df['volume'].tail(24).mean() else 'decreasing',
    }

    # 构建完整数据包
    data_package = {
        'symbol': symbol,
        'current_price': current_price,
        'price_range': {
            'min': float(df['low'].min()),
            'max': float(df['high'].max()),
            'range_percent': float((df['high'].max() - df['low'].min()) / current_price * 100),
        },
        'price_changes': price_changes,
        'volume_analysis': volume_analysis,
        'klines': klines,  # 完整200根K线
        'indicators': indicators,
        'orderbook': orderbook_summary,
        'market': market_summary,
    }
    
    # 添加 ValuScan 数据（优先级最高的参考数据）
    # AI 分析使用 14 天数据，图像生成使用 7 天数据
    if valuescan_data:
        data_package['valuescan'] = {
            'main_force_level': valuescan_data.get('current_main_force'),  # 主力位（阻力位）
            'main_force_levels': valuescan_data.get('main_force_levels', []),  # 历史主力位
            'main_cost': valuescan_data.get('main_cost'),  # 主力成本（支撑位参考）
            'trade_inflow': valuescan_data.get('trade_inflow'),
            'detailed_inflow': valuescan_data.get('detailed_inflow'),
            'token_flow': valuescan_data.get('token_flow'),  # 代币资金流向
            'whale_flow': valuescan_data.get('whale_flow'),  # 巨鲸资金流向
            'opportunity_signals': valuescan_data.get('opportunity_signals'),  # 机会信号
            'risk_signals': valuescan_data.get('risk_signals'),  # 风险信号
            'exchange_flow_detail': valuescan_data.get('exchange_flow_detail'),
            'fund_flow_history': valuescan_data.get('fund_flow_history'),
            'fund_volume_history': valuescan_data.get('fund_volume_history'),
            'holders_top': valuescan_data.get('holders_top'),
            'chains': valuescan_data.get('chains'),
            'data_days': valuescan_data.get('days', 14),
            'priority': 'HIGHEST',  # ValuScan 数据优先级最高
            'note': '主力位作为阻力位参考，主力成本作为强支撑位参考，资金流和信号作为辅助判断'
        }
        
    # 添加补充数据（资金费率、持仓量、多空比、恐惧贪婪指数）
    if valuescan_data and valuescan_data.get('supplementary'):
        supp = valuescan_data['supplementary']
        data_package['derivatives'] = {
            'funding_rate': supp.get('funding_rate'),  # 资金费率
            'open_interest': supp.get('open_interest'),  # 持仓量
            'long_short_ratio': supp.get('long_short_ratio'),  # 多空比
            'fear_greed_index': supp.get('fear_greed_index'),  # 恐惧贪婪指数
            'note': '衍生品数据反映市场杠杆和情绪，与主力位数据配合分析'
        }
        
    # 添加数据来源说明
    data_package['data_sources'] = {
        'primary': 'ValuScan (主力位、主力成本、资金流、信号) - 优先级最高',
        'derivatives': 'Binance Futures (资金费率、持仓量、多空比) + Fear & Greed Index',
        'supplementary': 'Binance K线数据 - 用于技术指标计算',
        'integration': 'ValuScan主力数据 + 衍生品情绪 + 价格走势 = 综合分析'
    }

    data_json = json.dumps(data_package, ensure_ascii=False, indent=2)

    if language == "en":
        return f"""You are a professional quantitative analyst and technical analyst. Analyze the market data comprehensively.

**IMPORTANT**: You are ONLY responsible for ANALYSIS, NOT drawing lines. The system will draw lines based on your analysis.

Input data (JSON):
{data_json}

Your task:
1. Analyze market structure and trend
2. Identify key support and resistance levels (with reasoning)
3. Evaluate market sentiment and momentum
4. Assess risk and opportunity
5. Provide trading suggestions

Return ONLY strict JSON format:

{{
  "trend": {{
    "direction": "bullish/bearish/sideways",
    "strength": 0-100,
    "description": "Brief trend description"
  }},
  "key_levels": {{
    "supports": [
      {{"price": 0, "strength": 0-100, "reason": "Why this is support"}},
      {{"price": 0, "strength": 0-100, "reason": "Why this is support"}}
    ],
    "resistances": [
      {{"price": 0, "strength": 0-100, "reason": "Why this is resistance"}},
      {{"price": 0, "strength": 0-100, "reason": "Why this is resistance"}}
    ]
  }},
  "patterns": {{
    "detected": ["channel", "wedge", "triangle", "flag", "head_and_shoulders", "double_top", "double_bottom"],
    "primary": "Most significant pattern name or null",
    "description": "Pattern description and implications"
  }},
  "sentiment": {{
    "score": -100 to 100,
    "description": "Market sentiment analysis"
  }},
  "momentum": {{
    "score": -100 to 100,
    "description": "Momentum analysis"
  }},
  "risk_assessment": {{
    "level": "low/medium/high",
    "factors": ["Risk factor 1", "Risk factor 2"]
  }},
  "trading_suggestion": {{
    "action": "buy/sell/hold/wait",
    "entry_zone": [min_price, max_price],
    "stop_loss": price,
    "take_profit": [price1, price2, price3],
    "reasoning": "Why this suggestion"
  }},
  "summary": "2-3 sentence market summary"
}}

Requirements:
1. Support levels MUST be < current_price
2. Resistance levels MUST be > current_price
3. Levels must be based on actual price action (pivots, volume clusters, round numbers)
4. Strength 0-100: higher = stronger level
5. Be specific with reasoning (e.g., "Multiple bounces at $86,500", "High volume node")
6. Consider ALL data: klines, indicators, orderbook, market data
7. Be objective and data-driven"""

    return f"""你是专业的量化分析师和技术分析师。请全面分析市场数据。

**重要**: 你只负责分析，不负责画线。系统会根据你的分析结果绘制辅助线。

输入数据 (JSON):
{data_json}

你的任务:
1. 分析市场结构和趋势
2. 识别关键支撑位和阻力位（**优先使用 valuescan 数据中的主力位作为阻力位，主力成本作为支撑位**）
3. 评估市场情绪和动量
4. 评估风险和机会
5. 提供交易建议

**重要**: 如果输入数据包含 valuescan 字段，请优先参考其中的主力位(main_force_level)和主力成本(main_cost)数据

只返回严格的JSON格式:

{{
  "trend": {{
    "direction": "bullish/bearish/sideways",
    "strength": 0-100,
    "description": "简要趋势描述"
  }},
  "key_levels": {{
    "supports": [
      {{"price": 0, "strength": 0-100, "reason": "为什么这是支撑位"}},
      {{"price": 0, "strength": 0-100, "reason": "为什么这是支撑位"}}
    ],
    "resistances": [
      {{"price": 0, "strength": 0-100, "reason": "为什么这是阻力位"}},
      {{"price": 0, "strength": 0-100, "reason": "为什么这是阻力位"}}
    ]
  }},
  "patterns": {{
    "detected": ["channel", "wedge", "triangle", "flag", "head_and_shoulders", "double_top", "double_bottom"],
    "primary": "最重要的形态名称或null",
    "description": "形态描述和含义"
  }},
  "sentiment": {{
    "score": -100到100,
    "description": "市场情绪分析"
  }},
  "momentum": {{
    "score": -100到100,
    "description": "动量分析"
  }},
  "risk_assessment": {{
    "level": "low/medium/high",
    "factors": ["风险因素1", "风险因素2"]
  }},
  "trading_suggestion": {{
    "action": "buy/sell/hold/wait",
    "entry_zone": [最低价, 最高价],
    "stop_loss": 价格,
    "take_profit": [价格1, 价格2, 价格3],
    "reasoning": "建议理由"
  }},
  "summary": "2-3句话的市场总结"
}}

要求:
1. 支撑位必须 < 当前价格
2. 阻力位必须 > 当前价格
3. 关键位必须基于实际价格行为（枢轴点、成交量集群、整数关口）
4. 强度0-100: 越高越强
5. 理由要具体（例如："$86,500多次反弹"、"高成交量节点"）
6. 考虑所有数据: K线、指标、订单簿、市场数据
7. 客观、数据驱动"""


def call_ai_analysis_api(prompt: str, config: Dict[str, Any]) -> Optional[str]:
    """调用AI API进行分析"""
    api_key = (config.get('api_key') or '').strip()
    api_url = (config.get('api_url') or '').strip()
    model = (config.get('model') or '').strip()

    if not api_key or not api_url or not model:
        return None

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }

    payload = {
        'model': model,
        'messages': [
            {'role': 'system', 'content': 'You are a professional quantitative analyst. Reply with strict JSON only.'},
            {'role': 'user', 'content': prompt}
        ],
        'max_tokens': 8000,
        'temperature': 0.3,
    }

    try:
        session = requests.Session()
        session.trust_env = False
        resp = session.post(api_url, headers=headers, json=payload, timeout=120)
        if resp.status_code != 200:
            logger.warning(f"AI analysis API call failed: {resp.status_code} - {resp.text[:200]}")
            return None

        data = resp.json()
        content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
        if not content:
            return None

        return content.strip()
    except Exception as exc:
        logger.warning(f"AI analysis API call error: {exc}")
        return None


def parse_ai_analysis(raw: str) -> Optional[Dict[str, Any]]:
    """解析AI分析结果"""
    if not raw:
        return None

    cleaned = raw.strip()

    # 尝试直接解析
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    # 尝试提取JSON
    start = cleaned.find('{')
    end = cleaned.rfind('}')
    if start != -1 and end != -1 and end > start:
        try:
            data = json.loads(cleaned[start:end + 1])
            if isinstance(data, dict):
                return data
        except Exception:
            pass

    logger.warning("Failed to parse AI analysis response")
    return None


def get_ai_market_analysis(
    symbol: str,
    df: pd.DataFrame,
    current_price: float,
    orderbook: Optional[Dict] = None,
    market_data: Optional[Dict] = None,
    config: Optional[Dict] = None,
    language: str = "zh"
) -> Optional[Dict[str, Any]]:
    """
    获取AI市场分析
    返回分析结果，不包含绘图坐标
    
    数据优先级：
    1. ValuScan 数据（主力位、主力成本）- 最高优先级
    2. 币安 K线数据 - 补充数据（仅用于技术指标计算）
    3. 订单簿数据 - 辅助参考
    """
    if config is None:
        from ai_market_summary import get_ai_summary_config
        config = get_ai_summary_config()

    if not config or not config.get('api_key'):
        logger.info("AI analysis not available: no API config")
        return None

    # 1. 首先获取 ValuScan 数据（最高优先级）
    valuescan_data = get_valuescan_data(symbol)
    if valuescan_data:
        logger.info(f"[Priority 1] ValuScan data loaded for {symbol}")
    else:
        logger.info(f"[Priority 1] ValuScan data not available for {symbol}")

    # 2. 获取补充数据（资金费率、持仓量、多空比、恐惧贪婪指数）
    supplementary_data = get_supplementary_data(symbol)
    if supplementary_data:
        logger.info(f"[Priority 2] Supplementary data loaded for {symbol}")
    
    # 3. 合并补充数据到 valuescan_data
    if valuescan_data and supplementary_data:
        valuescan_data["supplementary"] = supplementary_data
    elif supplementary_data:
        valuescan_data = {"supplementary": supplementary_data}

    # 4. 构建Prompt（ValuScan 数据优先，补充数据+K线数据补充）
    prompt = build_comprehensive_analysis_prompt(
        symbol, df, current_price, orderbook, market_data, language, valuescan_data
    )

    # 调用AI API
    logger.info(f"Calling AI for comprehensive market analysis of {symbol}...")
    raw_response = call_ai_analysis_api(prompt, config)

    if not raw_response:
        logger.warning("AI analysis failed: no response")
        return None

    # 解析响应
    analysis = parse_ai_analysis(raw_response)

    if not analysis:
        logger.warning("AI analysis failed: parse error")
        return None

    # 验证和清理数据
    analysis = validate_and_clean_analysis(analysis, current_price, valuescan_data)

    logger.info(f"AI analysis completed for {symbol}")
    return analysis


def validate_and_clean_analysis(analysis: Dict[str, Any], current_price: float, valuescan_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """验证和清理AI分析结果"""
    def _extract_price(item):
        if isinstance(item, dict):
            price = item.get("price")
            return float(price) if isinstance(price, (int, float)) else None
        if isinstance(item, (int, float)):
            return float(item)
        return None

    def _merge_levels(preferred, existing):
        out = []
        for item in list(preferred) + list(existing):
            price = _extract_price(item)
            if price is None:
                continue
            if any(abs(price - _extract_price(prev)) / max(_extract_price(prev), 1e-9) <= 0.02 for prev in out):
                continue
            if isinstance(item, dict):
                out.append(item)
            else:
                out.append({"price": price, "strength": 50, "reason": "auto"})
        return out

    if valuescan_data and isinstance(valuescan_data, dict):
        levels = analysis.get("key_levels")
        if not isinstance(levels, dict):
            levels = {}
            analysis["key_levels"] = levels
        supports = levels.get("supports") if isinstance(levels.get("supports"), list) else []
        resistances = levels.get("resistances") if isinstance(levels.get("resistances"), list) else []
        vs_supports = []
        vs_resistances = []
        vs_main_force = valuescan_data.get("current_main_force") or valuescan_data.get("main_force_level")
        vs_main_cost = valuescan_data.get("main_cost")
        vs_force_levels = valuescan_data.get("main_force_levels") or []

        for level in vs_force_levels:
            try:
                val = float(level)
            except Exception:
                continue
            if val <= 0:
                continue
            vs_resistances.append({
                "price": val,
                "strength": 80,
                "reason": "ValuScan main force",
                "source": "valuescan",
            })

        if isinstance(vs_main_force, (int, float)) and vs_main_force > 0:
            vs_resistances.append({
                "price": float(vs_main_force),
                "strength": 90,
                "reason": "ValuScan main force",
                "source": "valuescan",
            })
        if isinstance(vs_main_cost, (int, float)) and vs_main_cost > 0:
            vs_supports.append({
                "price": float(vs_main_cost),
                "strength": 90,
                "reason": "ValuScan main cost",
                "source": "valuescan",
            })
        if vs_supports or vs_resistances:
            levels["supports"] = _merge_levels(vs_supports, [])
            levels["resistances"] = _merge_levels(vs_resistances, [])

    # 验证关键位
    if 'key_levels' in analysis:
        levels = analysis['key_levels']

        # 验证支撑位
        if 'supports' in levels:
            valid_supports = []
            for item in levels['supports']:
                if isinstance(item, dict):
                    price = item.get('price')
                    if isinstance(price, (int, float)) and price < current_price:
                        valid_supports.append(item)
            levels['supports'] = valid_supports[:5]  # 最多5个

        # 验证阻力位
        if 'resistances' in levels:
            valid_resistances = []
            for item in levels['resistances']:
                if isinstance(item, dict):
                    price = item.get('price')
                    if isinstance(price, (int, float)) and price > current_price:
                        valid_resistances.append(item)
            levels['resistances'] = valid_resistances[:5]  # 最多5个

    # 确保必要字段存在
    if 'trend' not in analysis:
        analysis['trend'] = {'direction': 'sideways', 'strength': 50, 'description': 'Unknown'}

    if 'sentiment' not in analysis:
        analysis['sentiment'] = {'score': 0, 'description': 'Neutral'}

    if 'summary' not in analysis:
        analysis['summary'] = 'Market analysis completed.'

    return analysis
