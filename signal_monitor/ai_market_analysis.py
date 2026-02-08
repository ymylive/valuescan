"""
AI市场分析模块（重新设计）
AI只负责分析，不负责绘制
"""

import json
import os
import time as _time_mod
import requests

try:
    from .ai_api_utils import (
        AI_PROTOCOL_RESPONSES,
        build_payload,
        override_responses_token_key,
        parse_compatible_content,
        parse_responses_body,
        resolve_protocol_and_url,
        resolve_responses_token_key_override,
        should_force_responses_stream,
    )
except Exception:
    from ai_api_utils import (  # type: ignore[import-not-found]
        AI_PROTOCOL_RESPONSES,
        build_payload,
        override_responses_token_key,
        parse_compatible_content,
        parse_responses_body,
        resolve_protocol_and_url,
        resolve_responses_token_key_override,
        should_force_responses_stream,
    )
from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd
from logger import logger
from macro_data import load_macro_data
try:
    from .ai_request_queue import call_ai_with_queue
except Exception:
    from ai_request_queue import call_ai_with_queue  # type: ignore[import-not-found]

# 巨鲸数据模块

try:
    _NOFX_PROMPT_LIMIT = int(os.getenv("NOFX_AI_NOFX_LIMIT", "10") or 10)
except ValueError:
    _NOFX_PROMPT_LIMIT = 10

try:
    _NOFX_STRATEGY_LIMIT = int(os.getenv("NOFX_AI_NOFX_STRATEGY_LIMIT", "5") or 5)
except ValueError:
    _NOFX_STRATEGY_LIMIT = 5

try:
    from nofx_data_sources import (
        fetch_nofx_competition,
        fetch_nofx_public_strategies,
        fetch_nofx_top_traders,
    )
except ImportError:
    fetch_nofx_competition = None
    fetch_nofx_public_strategies = None
    fetch_nofx_top_traders = None

# Analysis frequency control: {symbol: (monotonic_timestamp, cached_result)}
_analysis_cache: Dict[str, tuple] = {}
_ANALYSIS_CACHE_MAX = 200  # Max cached symbols to prevent unbounded growth


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
    # 准备K线数据（最近100根，减少Prompt大小）
    klines = []
    if 'timestamp' in df.columns:
        recent_df = df.tail(100).reset_index(drop=True)
        ts_ms = (recent_df['timestamp'].astype('int64') // 10**6).astype('int64')
        for i, row in recent_df.iterrows():
            klines.append({
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
    macro_data = load_macro_data()

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

    # 巨鲸/资金流分析
    source_data = None
    if fetch_nofx_competition or fetch_nofx_top_traders or fetch_nofx_public_strategies:
        source_payload = {}
        try:
            if fetch_nofx_competition:
                data = fetch_nofx_competition(limit=_NOFX_PROMPT_LIMIT)
                if data is not None:
                    source_payload["competition"] = data
            if fetch_nofx_top_traders:
                data = fetch_nofx_top_traders(limit=_NOFX_PROMPT_LIMIT)
                if data is not None:
                    source_payload["top_traders"] = data
            if fetch_nofx_public_strategies:
                data = fetch_nofx_public_strategies(limit=_NOFX_STRATEGY_LIMIT)
                if data is not None:
                    source_payload["public_strategies"] = data
        except Exception as exc:
            logger.warning(f"External data fetch failed: {exc}")
            source_payload = {}
        if source_payload:
            source_data = source_payload

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
        'source_data': source_data,
        'klines': klines,
        'indicators': indicators,
        'orderbook': orderbook_summary,
        'market': market_summary,
        'macro_data': macro_data,
    }

    data_json = json.dumps(data_package, ensure_ascii=False, indent=2)

    language = (language or "zh").strip().lower()
    if language not in ("en", "zh"):
        language = "zh"

    return f"""You are a professional quantitative and technical analyst. Provide a macro market analysis. All descriptive text in the output MUST be in Chinese.
Translate any English macro/news/event titles into Chinese before using them in descriptive fields.

IMPORTANT: This is macro market analysis, not a single-signal brief. You are responsible only for analysis; the system draws lines.
Input data (JSON):
{data_json}

You must cover and clearly separate:
A. Fundamentals: tokenomics/onchain/project/sentiment and impact, plus major events and upcoming/released data from macro_data.
B. Technicals: structure/trend/patterns/indicators/key levels.
C. Flow & liquidity: orderbook, fund flow, volume, volatility.
D. Macro & market: macro_data/market context, market regime and sentiment.
E. Risk & opportunity.
F. Data conflicts & insufficiency (must be stated in data_conflicts).
G. If market context is available, mention overall market direction and BTC/ETH category separately (as context, not as proxy).

Return ONLY strict JSON. Do not rename keys; do not translate enum values:
{{
  "trend": {{
    "direction": "bullish/bearish/sideways",
    "strength": 0-100,
    "description": "Trend description"
  }},
  "key_levels": {{
    "supports": [
      {{"price": 0, "strength": 0-100, "reason": "Support reasoning"}},
      {{"price": 0, "strength": 0-100, "reason": "Support reasoning"}}
    ],
    "resistances": [
      {{"price": 0, "strength": 0-100, "reason": "Resistance reasoning"}},
      {{"price": 0, "strength": 0-100, "reason": "Resistance reasoning"}}
    ]
  }},
  "patterns": {{
    "detected": ["channel", "wedge", "triangle", "flag", "head_and_shoulders", "double_top", "double_bottom"],
    "primary": "Most significant pattern name or null",
    "description": "Pattern description"
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
    "reasoning": "Suggestion reasoning"
  }},
  "summary": "2-3 sentence market summary"
}}

Required extra fields (must be present; Chinese):
"fundamental_view", "technical_view", "macro_view", "liquidity_view", "data_conflicts"
If no conflicts, set data_conflicts to "无". If data is insufficient, state "数据不足".

Requirements:
1. Support levels MUST be < current_price; resistance levels MUST be > current_price.
2. Allow multiple levels (1-5 each) when confirmed by multi-source evidence.
3. Use weighted evidence (approx): price structure + volume clusters 40%, orderbook liquidity 25%, indicators 15%, crowd/strategy 10%, macro_data 10%.
4. Do not mention any data source names; say "based on signals" or "based on data".
5. Strength 0-100: higher = stronger level.
6. Be specific with reasoning (e.g., "Multiple bounces at 86500", "High volume node", "Orderbook sell wall").
7. Consider ALL data: klines, indicators, orderbook, market data, crowd/strategy context, macro_data.
8. macro_data includes only the next 7 days schedule and releases within the last 3 days; avoid stale data.
9. Summary MUST include fundamentals, technicals, liquidity/flow, and market regime; if data is insufficient, say so in Chinese.
10. All descriptive fields (reason/description/summary/optional views) MUST be in Chinese."""

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

    timeout_sec = int(os.getenv("NOFX_AI_API_TIMEOUT", "90") or 90)
    connect_timeout = float(os.getenv("NOFX_AI_CONNECT_TIMEOUT", "15") or 15)
    max_tokens = int(os.getenv("NOFX_AI_MARKET_MAX_TOKENS", "8000") or 8000)

    protocol, resolved_url = resolve_protocol_and_url(api_url, config.get('api_protocol'))
    stream = should_force_responses_stream(resolved_url, protocol)
    payload = build_payload(
        protocol,
        resolved_url,
        model,
        "你是专业量化分析师，要求多维度全面分析，仅返回严格 JSON，所有描述性文本使用中文。",
        prompt,
        max_tokens,
        0.3,
        stream,
    )

    try:
        session = requests.Session()
        session.trust_env = False
        if protocol == AI_PROTOCOL_RESPONSES:
            headers["Accept"] = "text/event-stream" if stream else "application/json"
        resp = session.post(resolved_url, headers=headers, json=payload, timeout=(connect_timeout, timeout_sec))
        if resp.status_code != 200:
            if resp.status_code == 429:
                raise RuntimeError(f"AI_429: {resp.text[:200]}")
            if protocol == AI_PROTOCOL_RESPONSES and resp.status_code == 400:
                override_key = resolve_responses_token_key_override(resp.text)
                if override_key is not None:
                    payload = override_responses_token_key(payload, override_key, max_tokens)
                    resp = session.post(
                        resolved_url,
                        headers=headers,
                        json=payload,
                        timeout=(connect_timeout, timeout_sec),
                    )
            if resp.status_code != 200:
                logger.warning(f"AI analysis API call failed: {resp.status_code} - {resp.text[:200]}")
                return None

        if protocol == AI_PROTOCOL_RESPONSES:
            try:
                content = parse_responses_body(resp.text)
            except Exception as exc:
                logger.warning(f"AI analysis API parse error: {exc}")
                content = ""
        else:
            data = resp.json()
            content = parse_compatible_content(data)
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
    language = "zh"

    if config is None:
        from ai_market_summary import get_ai_market_config
        config = get_ai_market_config()

    if not config or not config.get('api_key'):
        logger.info("AI analysis not available: no API config")
        return None

    # Frequency control: skip if same symbol was analyzed recently
    cooldown = int(os.getenv("NOFX_AI_ANALYSIS_COOLDOWN", "120") or 120)
    now = _time_mod.monotonic()
    last_ts, last_result = _analysis_cache.get(symbol, (0.0, None))
    if now - last_ts < cooldown and last_result is not None:
        logger.info(f"AI analysis for {symbol} throttled (cooldown {cooldown}s), returning cached result")
        return last_result

    # 构建Prompt
    prompt = build_comprehensive_analysis_prompt(
        symbol, df, current_price, orderbook, market_data, language
    )

    # 调用AI API
    logger.info(f"Calling AI for comprehensive market analysis of {symbol}...")
    raw_response = call_ai_with_queue(lambda: call_ai_analysis_api(prompt, config))

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

    # Cache the result with timestamp
    _analysis_cache[symbol] = (now, analysis)
    # Evict stale entries to prevent unbounded growth
    if len(_analysis_cache) > _ANALYSIS_CACHE_MAX:
        oldest_key = min(_analysis_cache, key=lambda k: _analysis_cache[k][0])
        del _analysis_cache[oldest_key]

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
        analysis['summary'] = '市场分析完成。'

    return analysis
