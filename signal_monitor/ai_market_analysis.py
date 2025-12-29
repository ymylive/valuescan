"""
AI市场分析模块（重新设计）
AI只负责分析，不负责绘制
"""

import json
import requests
from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd
from logger import logger


def build_comprehensive_analysis_prompt(
    symbol: str,
    df: pd.DataFrame,
    current_price: float,
    orderbook: Optional[Dict] = None,
    market_data: Optional[Dict] = None,
    language: str = "zh"
) -> str:
    """
    构建全面的市场分析Prompt
    包含所有数据，让AI做深度分析
    增强版：添加更多市场数据（资金费率、持仓量、多空比、清算数据等）
    """
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
2. 识别关键支撑位和阻力位（附带理由）
3. 评估市场情绪和动量
4. 评估风险和机会
5. 提供交易建议

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
    """
    if config is None:
        from ai_market_summary import get_ai_summary_config
        config = get_ai_summary_config()

    if not config or not config.get('api_key'):
        logger.info("AI analysis not available: no API config")
        return None

    # 构建Prompt
    prompt = build_comprehensive_analysis_prompt(
        symbol, df, current_price, orderbook, market_data, language
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
    analysis = validate_and_clean_analysis(analysis, current_price)

    logger.info(f"AI analysis completed for {symbol}")
    return analysis


def validate_and_clean_analysis(analysis: Dict[str, Any], current_price: float) -> Dict[str, Any]:
    """验证和清理AI分析结果"""
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
