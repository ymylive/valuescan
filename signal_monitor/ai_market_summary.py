#!/usr/bin/env python3
"""
AI 市场宏观分析模块

功能：
1. 收集 BTC/ETH OHLCV K线数据
2. 收集 NOFX 量化数据（netflow, oi, price）
3. 收集 OI 排行数据
4. 收集加密货币新闻
5. 收集 ValueScan 信号数据
6. 使用 AI 综合分析市场宏观走向
7. 生成专业市场分析报告
8. 定时发送到 Telegram
"""

import json
import logging
import os
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

# 北京时区
BEIJING_TZ = timezone(timedelta(hours=8))

# 配置
AI_SUMMARY_ENABLED = os.getenv("VALUESCAN_AI_SUMMARY_ENABLED", "0") == "1"
AI_SUMMARY_INTERVAL_HOURS = float(os.getenv("VALUESCAN_AI_SUMMARY_INTERVAL_HOURS", "1"))
AI_SUMMARY_API_KEY = os.getenv("VALUESCAN_AI_SUMMARY_API_KEY", "").strip()
AI_SUMMARY_API_URL = os.getenv(
    "VALUESCAN_AI_SUMMARY_API_URL", 
    "https://api.openai.com/v1/chat/completions"
).strip()
AI_SUMMARY_MODEL = os.getenv("VALUESCAN_AI_SUMMARY_MODEL", "gpt-4o-mini").strip()

# 数据收集时间范围（小时）
SIGNAL_LOOKBACK_HOURS = float(os.getenv("VALUESCAN_SIGNAL_LOOKBACK_HOURS", "1"))

# NOFX 量化数据 API
NOFX_API_BASE = os.getenv("NOFX_API_BASE", "http://nofxaios.com:30006").strip()
NOFX_API_AUTH = os.getenv("NOFX_API_AUTH", "cm_568c67eae410d912c54c").strip()

# Binance Futures API
BINANCE_FUTURES_BASE = "https://fapi.binance.com"

# 加密新闻 API（可选）
CRYPTO_NEWS_API_KEY = os.getenv("CRYPTO_NEWS_API_KEY", "").strip()

# 主要分析币种
MAJOR_COINS = ["BTC", "ETH"]

# 上次总结时间
_last_summary_time: float = 0.0


def _load_config() -> Dict[str, Any]:
    """从配置文件加载 AI 总结配置"""
    config_path = Path(__file__).parent / "ai_summary_config.json"
    if config_path.exists():
        try:
            return json.loads(config_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_config(config: Dict[str, Any]) -> bool:
    """保存 AI 总结配置"""
    config_path = Path(__file__).parent / "ai_summary_config.json"
    try:
        config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except Exception as e:
        logger.error("保存 AI 总结配置失败: %s", e)
        return False


def get_ai_summary_config() -> Dict[str, Any]:
    """获取 AI 总结配置"""
    file_config = _load_config()
    return {
        "enabled": file_config.get("enabled", AI_SUMMARY_ENABLED),
        "interval_hours": file_config.get("interval_hours", AI_SUMMARY_INTERVAL_HOURS),
        "api_key": file_config.get("api_key", AI_SUMMARY_API_KEY),
        "api_url": file_config.get("api_url", AI_SUMMARY_API_URL),
        "model": file_config.get("model", AI_SUMMARY_MODEL),
        "lookback_hours": file_config.get("lookback_hours", SIGNAL_LOOKBACK_HOURS),
    }


def update_ai_summary_config(config: Dict[str, Any]) -> bool:
    """更新 AI 总结配置"""
    return _save_config(config)


def _collect_recent_signals(lookback_hours: float = 1.0) -> Dict[str, Any]:
    """
    收集最近的 ValueScan 信号数据
    
    Returns:
        包含各类信号的字典
    """
    from database import MessageDatabase
    
    cutoff_time = time.time() - (lookback_hours * 3600)
    cutoff_ms = int(cutoff_time * 1000)
    
    try:
        db = MessageDatabase()
        messages = db.get_recent_messages_for_ai(limit=200, since_timestamp_ms=cutoff_ms)
    except Exception as e:
        logger.warning("获取最近消息失败: %s", e)
        messages = []
    
    # 分类信号
    bullish_signals = []  # 看涨信号
    bearish_signals = []  # 看跌信号
    arbitrage_signals = []  # 套利机会
    whale_signals = []  # 大户动向
    other_signals = []  # 其他信号
    
    for msg in messages:
        msg_type = msg.get("type") or msg.get("messageType")
        symbol = msg.get("symbol", "")
        content = msg.get("content", "") or msg.get("message", "")
        
        signal_info = {
            "symbol": symbol,
            "type": msg_type,
            "content": content[:200] if content else "",
            "time": msg.get("createTime") or msg.get("timestamp"),
        }
        
        # 根据类型分类
        if msg_type in (108, 110, 111):  # 大单买入、资金流入等
            bullish_signals.append(signal_info)
        elif msg_type in (109, 112):  # 大单卖出、资金流出等
            bearish_signals.append(signal_info)
        elif msg_type in (113, 114):  # 套利相关
            arbitrage_signals.append(signal_info)
        elif msg_type in (115, 116):  # 大户动向
            whale_signals.append(signal_info)
        else:
            other_signals.append(signal_info)
    
    return {
        "bullish": bullish_signals,
        "bearish": bearish_signals,
        "arbitrage": arbitrage_signals,
        "whale": whale_signals,
        "other": other_signals,
        "total_count": len(messages),
        "lookback_hours": lookback_hours,
    }


def _collect_movement_data() -> Dict[str, Any]:
    """收集异动榜单数据"""
    try:
        from movement_list_cache import get_movement_list_cache
        cache = get_movement_list_cache()
        
        alpha_symbols = cache.get_symbols_with_alpha()
        fomo_symbols = cache.get_symbols_with_fomo()
        
        return {
            "alpha_coins": list(alpha_symbols)[:20],
            "fomo_coins": list(fomo_symbols)[:20],
        }
    except Exception as e:
        logger.warning("获取异动榜单失败: %s", e)
        return {"alpha_coins": [], "fomo_coins": []}


def _fetch_binance_klines(symbol: str, interval: str = "1h", limit: int = 24) -> List[Dict[str, Any]]:
    """
    从 Binance Futures API 获取 K 线数据
    
    Args:
        symbol: 币种符号（如 BTCUSDT）
        interval: K线周期（1m, 5m, 15m, 1h, 4h, 1d）
        limit: 获取数量
    
    Returns:
        K线数据列表
    """
    if not symbol.endswith("USDT"):
        symbol = f"{symbol}USDT"
    
    url = f"{BINANCE_FUTURES_BASE}/fapi/v1/klines"
    params = {
        "symbol": symbol.upper(),
        "interval": interval,
        "limit": limit,
    }
    
    try:
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            klines = []
            for k in data:
                klines.append({
                    "open_time": k[0],
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                    "close_time": k[6],
                    "quote_volume": float(k[7]),
                    "trades": int(k[8]),
                })
            return klines
        else:
            logger.debug("Binance API 返回 %d: %s", resp.status_code, symbol)
            return []
    except Exception as e:
        logger.debug("Binance API 请求失败 (%s): %s", symbol, e)
        return []


def _analyze_klines(klines: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    分析 K 线数据，计算技术指标
    
    Returns:
        包含趋势、波动率等分析结果
    """
    if not klines or len(klines) < 2:
        return {}
    
    closes = [k["close"] for k in klines]
    highs = [k["high"] for k in klines]
    lows = [k["low"] for k in klines]
    volumes = [k["volume"] for k in klines]
    
    # 价格变化
    latest_close = closes[-1]
    first_close = closes[0]
    price_change_pct = ((latest_close - first_close) / first_close) * 100
    
    # 最高最低价
    period_high = max(highs)
    period_low = min(lows)
    price_range_pct = ((period_high - period_low) / period_low) * 100
    
    # 平均成交量
    avg_volume = sum(volumes) / len(volumes)
    latest_volume = volumes[-1]
    volume_ratio = latest_volume / avg_volume if avg_volume > 0 else 1
    
    # 简单趋势判断（基于收盘价）
    up_candles = sum(1 for i in range(1, len(closes)) if closes[i] > closes[i-1])
    down_candles = len(closes) - 1 - up_candles
    
    # MA5 和 MA10
    ma5 = sum(closes[-5:]) / 5 if len(closes) >= 5 else latest_close
    ma10 = sum(closes[-10:]) / 10 if len(closes) >= 10 else latest_close
    
    trend = "bullish" if ma5 > ma10 and price_change_pct > 0 else "bearish" if ma5 < ma10 and price_change_pct < 0 else "neutral"
    
    return {
        "latest_price": latest_close,
        "price_change_pct": round(price_change_pct, 2),
        "period_high": period_high,
        "period_low": period_low,
        "price_range_pct": round(price_range_pct, 2),
        "avg_volume": avg_volume,
        "volume_ratio": round(volume_ratio, 2),
        "up_candles": up_candles,
        "down_candles": down_candles,
        "ma5": round(ma5, 2),
        "ma10": round(ma10, 2),
        "trend": trend,
    }


def _fetch_nofx_coin_data(symbol: str) -> Optional[Dict[str, Any]]:
    """
    从 NOFX API 获取单个币种的量化数据
    
    Args:
        symbol: 币种符号（如 BTC, ETH）
    
    Returns:
        包含 netflow, oi, price 等数据的字典
    """
    if not NOFX_API_BASE or not NOFX_API_AUTH:
        return None
    
    url = f"{NOFX_API_BASE}/api/coin/{symbol.upper()}?include=netflow,oi,price&auth={NOFX_API_AUTH}"
    
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        else:
            logger.debug("NOFX API 返回 %d: %s", resp.status_code, symbol)
            return None
    except Exception as e:
        logger.debug("NOFX API 请求失败 (%s): %s", symbol, e)
        return None


def _fetch_oi_ranking(limit: int = 20, duration: str = "1h") -> List[Dict[str, Any]]:
    """
    从 NOFX API 获取 OI 排行数据
    
    Args:
        limit: 获取数量
        duration: 时间周期（1h, 4h, 24h）
    
    Returns:
        OI 排行列表
    """
    if not NOFX_API_BASE or not NOFX_API_AUTH:
        return []
    
    url = f"{NOFX_API_BASE}/api/oi/top-ranking?limit={limit}&duration={duration}&auth={NOFX_API_AUTH}"
    
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("data", []) if isinstance(data, dict) else data if isinstance(data, list) else []
        else:
            logger.debug("NOFX OI Ranking API 返回 %d", resp.status_code)
            return []
    except Exception as e:
        logger.debug("NOFX OI Ranking API 请求失败: %s", e)
        return []


def _collect_major_coin_data() -> Dict[str, Dict[str, Any]]:
    """
    收集 BTC 和 ETH 的综合数据
    
    Returns:
        包含 K线分析、量化数据的字典
    """
    result = {}
    
    for symbol in MAJOR_COINS:
        logger.info(f"收集 {symbol} 数据...")
        coin_data = {
            "symbol": symbol,
            "klines_1h": {},
            "klines_4h": {},
            "klines_1d": {},
            "quant": {},
        }
        
        # 获取不同周期的 K 线数据
        for interval, key in [("1h", "klines_1h"), ("4h", "klines_4h"), ("1d", "klines_1d")]:
            klines = _fetch_binance_klines(symbol, interval, limit=24)
            if klines:
                coin_data[key] = _analyze_klines(klines)
        
        # 获取 NOFX 量化数据
        quant = _fetch_nofx_coin_data(symbol)
        if quant:
            coin_data["quant"] = quant
        
        result[symbol] = coin_data
    
    return result


def _collect_quantitative_data(symbols: List[str]) -> Dict[str, Any]:
    """
    收集多个币种的量化数据
    
    Args:
        symbols: 币种符号列表
    
    Returns:
        量化数据汇总
    """
    if not symbols:
        return {"coins": [], "summary": {}}
    
    # 限制并发请求数量
    symbols_to_fetch = list(set(symbols))[:10]
    
    coin_data = []
    bullish_coins = []
    bearish_coins = []
    high_oi_coins = []
    
    for sym in symbols_to_fetch:
        data = _fetch_nofx_coin_data(sym)
        if not data:
            continue
        
        coin_info = {
            "symbol": sym,
            "price": data.get("price", {}),
            "netflow": data.get("netflow", {}),
            "oi": data.get("oi", {}),
        }
        coin_data.append(coin_info)
        
        # 分析看涨/看跌信号
        netflow = data.get("netflow", {})
        oi = data.get("oi", {})
        
        # 净流入为正 -> 看涨
        if netflow.get("netflow_1h", 0) > 0 and netflow.get("netflow_4h", 0) > 0:
            bullish_coins.append(sym)
        elif netflow.get("netflow_1h", 0) < 0 and netflow.get("netflow_4h", 0) < 0:
            bearish_coins.append(sym)
        
        # OI 变化大
        if abs(oi.get("oi_change_1h", 0)) > 5:  # >5% 变化
            high_oi_coins.append(sym)
    
    return {
        "coins": coin_data,
        "summary": {
            "bullish_netflow": bullish_coins,
            "bearish_netflow": bearish_coins,
            "high_oi_change": high_oi_coins,
        }
    }


def _fetch_crypto_news() -> List[Dict[str, Any]]:
    """
    获取加密货币新闻
    
    Returns:
        新闻列表
    """
    news = []
    
    # 尝试从 CryptoCompare 获取新闻（免费 API）
    try:
        url = "https://min-api.cryptocompare.com/data/v2/news/?lang=EN&sortOrder=popular"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            for item in (data.get("Data") or [])[:5]:
                news.append({
                    "title": item.get("title", ""),
                    "source": item.get("source", ""),
                    "url": item.get("url", ""),
                    "categories": item.get("categories", ""),
                    "published": item.get("published_on", 0),
                })
    except Exception as e:
        logger.debug("获取 CryptoCompare 新闻失败: %s", e)
    
    # 尝试从 CoinGecko 获取市场趋势
    try:
        url = "https://api.coingecko.com/api/v3/search/trending"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            trending_coins = []
            for item in (data.get("coins") or [])[:5]:
                coin = item.get("item", {})
                trending_coins.append({
                    "name": coin.get("name", ""),
                    "symbol": coin.get("symbol", ""),
                    "market_cap_rank": coin.get("market_cap_rank", 0),
                })
            if trending_coins:
                news.append({
                    "title": "Trending Coins on CoinGecko",
                    "source": "CoinGecko",
                    "coins": trending_coins,
                })
    except Exception as e:
        logger.debug("获取 CoinGecko 趋势失败: %s", e)
    
    return news


def _build_macro_analysis_prompt(
    major_coin_data: Dict[str, Dict[str, Any]],
    oi_ranking: List[Dict[str, Any]],
    signals: Dict[str, Any], 
    news: Optional[List[Dict[str, Any]]] = None
) -> str:
    """
    构建专业的宏观市场分析 Prompt
    
    专注于 BTC/ETH 分析，综合 K线、量化数据、OI排行、新闻和 ValueScan 信号
    """
    
    now = datetime.now(BEIJING_TZ)
    
    prompt = f"""你是一位顶级加密货币宏观分析师，拥有丰富的技术分析和链上数据分析经验。
请根据以下多维度数据，对加密货币市场进行专业的宏观分析。

**分析时间**: {now.strftime('%Y-%m-%d %H:%M')} (北京时间)

================================================================================
                              📊 BTC/ETH 核心数据分析
================================================================================
"""
    
    # BTC 和 ETH 详细数据
    for symbol in MAJOR_COINS:
        data = major_coin_data.get(symbol, {})
        prompt += f"\n### {symbol} 数据\n"
        
        # K 线分析
        for tf, key in [("1小时", "klines_1h"), ("4小时", "klines_4h"), ("日线", "klines_1d")]:
            kl = data.get(key, {})
            if kl:
                trend_emoji = "🟢" if kl.get("trend") == "bullish" else "🔴" if kl.get("trend") == "bearish" else "⚪"
                prompt += f"**{tf}周期**: {trend_emoji} 趋势={kl.get('trend', 'N/A')}, "
                prompt += f"价格={kl.get('latest_price', 0):.2f}, 涨跌={kl.get('price_change_pct', 0):.2f}%, "
                prompt += f"波动率={kl.get('price_range_pct', 0):.2f}%, 成交量比={kl.get('volume_ratio', 1):.2f}x, "
                prompt += f"MA5={kl.get('ma5', 0):.2f}, MA10={kl.get('ma10', 0):.2f}\n"
        
        # NOFX 量化数据
        quant = data.get("quant", {})
        if quant:
            price_data = quant.get("price", {})
            netflow = quant.get("netflow", {})
            oi = quant.get("oi", {})
            
            prompt += f"\n**量化指标 (NOFX)**:\n"
            
            if price_data:
                prompt += f"  - 24h价格变化: {price_data.get('change_24h', 0):.2f}%\n"
            
            if netflow:
                nf_1h = netflow.get("netflow_1h", 0)
                nf_4h = netflow.get("netflow_4h", 0)
                nf_24h = netflow.get("netflow_24h", 0)
                nf_emoji = "📈" if nf_1h > 0 else "📉"
                prompt += f"  - 资金净流入: {nf_emoji} 1h=${nf_1h/1e6:.2f}M, 4h=${nf_4h/1e6:.2f}M, 24h=${nf_24h/1e6:.2f}M\n"
            
            if oi:
                oi_change_1h = oi.get("oi_change_1h", 0)
                oi_change_4h = oi.get("oi_change_4h", 0)
                oi_value = oi.get("oi_value", 0)
                oi_emoji = "⬆️" if oi_change_1h > 0 else "⬇️"
                prompt += f"  - 持仓量(OI): {oi_emoji} 变化1h={oi_change_1h:.2f}%, 4h={oi_change_4h:.2f}%, 总OI=${oi_value/1e9:.2f}B\n"
    
    # OI 排行数据
    if oi_ranking and isinstance(oi_ranking, list) and len(oi_ranking) > 0:
        prompt += f"""
================================================================================
                              📈 OI 排行榜 Top 10 (1h变化)
================================================================================
"""
        for i, item in enumerate(oi_ranking[:10], 1):
            if not isinstance(item, dict):
                continue
            sym = item.get("symbol", "N/A")
            oi_change = item.get("oi_change", item.get("change", 0)) or 0
            oi_value = item.get("oi_value", item.get("value", 0)) or 0
            emoji = "🔥" if oi_change > 5 else "📊"
            prompt += f"{i}. {emoji} {sym}: OI变化={oi_change:.2f}%, OI值=${oi_value/1e6:.1f}M\n"
    
    # ValueScan 信号统计
    bullish_count = len(signals.get("bullish", []))
    bearish_count = len(signals.get("bearish", []))
    
    prompt += f"""
================================================================================
                              🎯 ValueScan 信号数据
================================================================================
- 看涨信号: {bullish_count} 条
- 看跌信号: {bearish_count} 条
- 信号比: {bullish_count}:{bearish_count} ({"偏多" if bullish_count > bearish_count else "偏空" if bearish_count > bullish_count else "平衡"})
"""
    
    # 热门信号币种
    symbol_counts: Dict[str, int] = {}
    for category in ["bullish", "bearish"]:
        for sig in signals.get(category, []):
            sym = sig.get("symbol", "")
            if sym:
                symbol_counts[sym] = symbol_counts.get(sym, 0) + 1
    
    hot_symbols = sorted(symbol_counts.items(), key=lambda x: -x[1])[:10]
    if hot_symbols:
        prompt += f"- 热门信号币种: {', '.join([f'{sym}({cnt})' for sym, cnt in hot_symbols])}\n"
    
    # 新闻数据
    if news:
        prompt += f"""
================================================================================
                              📰 市场新闻与趋势
================================================================================
"""
        for item in news[:5]:
            if item.get("coins"):
                coins = item.get("coins", [])
                trending = ", ".join([f"{c.get('symbol', '')}" for c in coins[:5]])
                prompt += f"- 热门趋势: {trending}\n"
            else:
                prompt += f"- [{item.get('source', '')}] {item.get('title', '')[:60]}\n"
    
    prompt += """
================================================================================
                              🎯 分析要求
================================================================================

请基于以上所有数据，生成一份专业的加密货币宏观市场分析报告，必须包含以下内容：

1. **宏观市场走向判断**
   - 综合 BTC/ETH 的技术面（K线趋势、MA）和资金面（净流入、OI变化）
   - 给出未来 24-48 小时可能的市场走向（看涨/看跌/震荡）
   - 提供信心指数（1-10分）

2. **BTC 专项分析**
   - 当前趋势强度
   - 关键支撑/阻力位
   - 资金流向解读

3. **ETH 专项分析**
   - 当前趋势强度
   - 与 BTC 的联动关系
   - ETH/BTC 汇率走势判断

4. **套利机会识别**
   - 基于 OI 排行和信号数据识别潜在套利机会
   - 列出 2-3 个值得关注的山寨币

5. **市场情绪总结**
   - 综合所有数据判断当前市场情绪（贪婪/恐惧/中性）
   - 大户动向解读

6. **风险提示**
   - 当前市场主要风险点
   - 需要警惕的信号

要求：
- 使用中文，专业但易懂
- 适合 Telegram 发送
- 使用 emoji 增加可读性
- 观点明确，有理有据
- 总长度控制在 800 字以内
"""
    
    return prompt


def _call_ai_api(prompt: str, config: Dict[str, Any]) -> Optional[str]:
    """调用 AI API 生成总结"""
    api_key = config.get("api_key", "")
    api_url = config.get("api_url", AI_SUMMARY_API_URL)
    model = config.get("model", AI_SUMMARY_MODEL)
    
    if not api_key:
        logger.error("AI API Key 未配置")
        return None
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "你是一个专业的加密货币市场分析师，擅长分析市场信号并给出简洁的投资建议。"},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 1000,
        "temperature": 0.7,
    }
    
    try:
        resp = requests.post(api_url, headers=headers, json=payload, timeout=60)
        if resp.status_code != 200:
            logger.error("AI API 请求失败: %s - %s", resp.status_code, resp.text[:200])
            return None
        
        data = resp.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return content.strip() if content else None
    except Exception as e:
        logger.error("AI API 调用异常: %s", e)
        return None


def _send_summary_to_telegram(summary: str) -> bool:
    """发送总结到 Telegram"""
    from telegram import send_telegram_message
    
    now = datetime.now(BEIJING_TZ)
    header = f"📊 AI 市场总结\n⏰ {now.strftime('%Y-%m-%d %H:%M')} (北京时间)\n\n"
    
    # 清理消息，移除 markdown 格式，使用纯文本
    message = header + summary
    # 移除 markdown 格式符号
    message = message.replace("**", "")
    message = message.replace("###", "")
    message = message.replace("---", "")
    # 移除可能导致 HTML 解析错误的标签
    message = message.replace("<b>", "").replace("</b>", "")
    message = message.replace("<i>", "").replace("</i>", "")
    
    # 使用纯文本模式发送，不使用 HTML 解析
    result = send_telegram_message(message, pin_message=False, parse_mode=None)
    return result is not None and result.get("success", False)


def generate_market_summary(force: bool = False) -> Optional[str]:
    """
    生成专业的宏观市场分析报告
    
    Args:
        force: 是否强制生成（忽略时间间隔）
    
    Returns:
        生成的分析文本，失败返回 None
    """
    global _last_summary_time
    
    config = get_ai_summary_config()
    
    if not config.get("enabled") and not force:
        logger.debug("AI 市场总结功能未启用")
        return None
    
    # 检查时间间隔
    interval_seconds = config.get("interval_hours", 1) * 3600
    now = time.time()
    if not force and (now - _last_summary_time) < interval_seconds:
        logger.debug("距离上次总结时间不足，跳过")
        return None
    
    logger.info("开始生成 AI 宏观市场分析...")
    
    # 1. 收集 BTC/ETH 核心数据（K线 + 量化数据）
    logger.info("收集 BTC/ETH 核心数据...")
    major_coin_data = _collect_major_coin_data()
    
    # 2. 获取 OI 排行数据
    logger.info("获取 OI 排行数据...")
    oi_ranking = _fetch_oi_ranking(limit=20, duration="1h")
    
    # 3. 收集 ValueScan 信号数据
    lookback = config.get("lookback_hours", 1)
    logger.info(f"收集最近 {lookback} 小时信号数据...")
    signals = _collect_recent_signals(lookback)
    
    # 4. 获取新闻数据
    logger.info("获取市场新闻...")
    news = _fetch_crypto_news()
    
    # 检查是否有足够数据
    if not major_coin_data and not oi_ranking and signals.get("total_count", 0) == 0:
        logger.info("没有足够的数据，跳过总结")
        return None
    
    # 构建专业宏观分析 prompt
    prompt = _build_macro_analysis_prompt(major_coin_data, oi_ranking, signals, news)
    
    # 调用 AI
    summary = _call_ai_api(prompt, config)
    if not summary:
        logger.error("AI 生成分析失败")
        return None
    
    logger.info("AI 宏观市场分析生成成功")
    _last_summary_time = now
    
    # 发送到 Telegram
    if _send_summary_to_telegram(summary):
        logger.info("市场分析已发送到 Telegram")
    else:
        logger.warning("市场分析发送到 Telegram 失败")
    
    return summary


def check_and_generate_summary() -> None:
    """
    检查是否需要生成总结（由 polling_monitor 定期调用）
    """
    config = get_ai_summary_config()
    if not config.get("enabled"):
        return
    
    interval_seconds = config.get("interval_hours", 1) * 3600
    now = time.time()
    
    if (now - _last_summary_time) >= interval_seconds:
        generate_market_summary()


def main():
    """测试入口"""
    import argparse
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    
    parser = argparse.ArgumentParser(description="AI 市场总结")
    parser.add_argument("--force", action="store_true", help="强制生成总结")
    parser.add_argument("--test", action="store_true", help="测试模式（不发送 Telegram）")
    args = parser.parse_args()
    
    if args.test:
        config = get_ai_summary_config()
        print("当前配置:", json.dumps(config, ensure_ascii=False, indent=2))
        
        signals = _collect_recent_signals()
        print(f"\n信号统计: {signals.get('total_count', 0)} 条")
        print(f"  看涨: {len(signals.get('bullish', []))}")
        print(f"  看跌: {len(signals.get('bearish', []))}")
        
        movements = _collect_movement_data()
        print(f"\nAlpha 币种: {len(movements.get('alpha_coins', []))}")
        print(f"FOMO 币种: {len(movements.get('fomo_coins', []))}")
    else:
        summary = generate_market_summary(force=args.force)
        if summary:
            print("\n生成的总结:\n")
            print(summary)
        else:
            print("生成总结失败")


if __name__ == "__main__":
    main()
