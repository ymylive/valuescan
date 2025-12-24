#!/usr/bin/env python3
"""
AI 市场总结模块

功能：
1. 收集 ValueScan 信号数据
2. 使用 AI 分析市场机会
3. 生成市场总结报告
4. 每小时发送到 Telegram
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

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

# 加密新闻 API（可选）
CRYPTO_NEWS_API_KEY = os.getenv("CRYPTO_NEWS_API_KEY", "").strip()

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


def _build_ai_prompt(
    signals: Dict[str, Any], 
    movements: Dict[str, Any],
    quant_data: Optional[Dict[str, Any]] = None,
    news: Optional[List[Dict[str, Any]]] = None
) -> str:
    """构建 AI 分析的 Prompt"""
    
    now = datetime.now(BEIJING_TZ)
    
    # 统计各类信号
    bullish_count = len(signals.get("bullish", []))
    bearish_count = len(signals.get("bearish", []))
    arbitrage_count = len(signals.get("arbitrage", []))
    
    # 提取热门币种
    symbol_counts: Dict[str, int] = {}
    for category in ["bullish", "bearish", "arbitrage", "whale", "other"]:
        for sig in signals.get(category, []):
            sym = sig.get("symbol", "")
            if sym:
                symbol_counts[sym] = symbol_counts.get(sym, 0) + 1
    
    hot_symbols = sorted(symbol_counts.items(), key=lambda x: -x[1])[:10]
    
    prompt = f"""你是一个专业的加密货币市场分析师。请根据以下 ValueScan 信号数据，生成一份简洁的市场总结报告。

**当前时间**: {now.strftime('%Y-%m-%d %H:%M')} (北京时间)
**数据时间范围**: 最近 {signals.get('lookback_hours', 1)} 小时
**信号总数**: {signals.get('total_count', 0)}

## 信号统计
- 看涨信号: {bullish_count} 条
- 看跌信号: {bearish_count} 条
- 套利机会: {arbitrage_count} 条

## 热门币种
{', '.join([f"{sym}({cnt}次)" for sym, cnt in hot_symbols]) if hot_symbols else '暂无'}

## Alpha 币种（Binance 官方推荐）
{', '.join(movements.get('alpha_coins', [])[:10]) if movements.get('alpha_coins') else '暂无'}

## FOMO 热度币种
{', '.join(movements.get('fomo_coins', [])[:10]) if movements.get('fomo_coins') else '暂无'}

## 看涨信号详情（前5条）
"""
    
    for sig in signals.get("bullish", [])[:5]:
        prompt += f"- {sig.get('symbol', 'N/A')}: {sig.get('content', '')[:100]}\n"
    
    prompt += "\n## 看跌信号详情（前5条）\n"
    for sig in signals.get("bearish", [])[:5]:
        prompt += f"- {sig.get('symbol', 'N/A')}: {sig.get('content', '')[:100]}\n"
    
    # 添加量化数据
    if quant_data and quant_data.get("coins"):
        prompt += "\n## 量化数据分析（NOFX API）\n"
        summary = quant_data.get("summary", {})
        
        if summary.get("bullish_netflow"):
            prompt += f"**资金净流入（看涨）**: {', '.join(summary['bullish_netflow'])}\n"
        if summary.get("bearish_netflow"):
            prompt += f"**资金净流出（看跌）**: {', '.join(summary['bearish_netflow'])}\n"
        if summary.get("high_oi_change"):
            prompt += f"**OI大幅变化**: {', '.join(summary['high_oi_change'])}\n"
        
        prompt += "\n币种详情:\n"
        for coin in quant_data.get("coins", [])[:5]:
            sym = coin.get("symbol", "")
            price = coin.get("price", {})
            netflow = coin.get("netflow", {})
            oi = coin.get("oi", {})
            
            price_change = price.get("change_24h", 0)
            nf_1h = netflow.get("netflow_1h", 0)
            oi_change = oi.get("oi_change_1h", 0)
            
            prompt += f"- {sym}: 24h涨跌 {price_change:.2f}%, 1h净流入 ${nf_1h/1e6:.2f}M, OI变化 {oi_change:.2f}%\n"
    
    # 添加新闻数据
    if news:
        prompt += "\n## 市场新闻与趋势\n"
        for item in news[:5]:
            if item.get("coins"):
                # CoinGecko 趋势
                coins = item.get("coins", [])
                trending = ", ".join([f"{c.get('symbol', '')}({c.get('name', '')})" for c in coins[:5]])
                prompt += f"**{item.get('title', '')}**: {trending}\n"
            else:
                prompt += f"- [{item.get('source', '')}] {item.get('title', '')[:80]}\n"
    
    prompt += """
---

请生成一份简洁的市场总结报告，包括：
1. **市场整体情绪**（看涨/看跌/震荡）- 综合信号、资金流向和新闻判断
2. **值得关注的看涨币种**（2-3个，结合资金流入和信号说明理由）
3. **值得关注的看跌币种**（2-3个，结合资金流出和信号说明理由）
4. **套利机会**（如有）
5. **市场热点**（根据新闻趋势总结）
6. **风险提示**

要求：
- 使用中文
- 简洁明了，适合 Telegram 发送
- 使用 emoji 增加可读性
- 总长度控制在 600 字以内
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
    header = f"📊 <b>AI 市场总结</b>\n⏰ {now.strftime('%Y-%m-%d %H:%M')} (北京时间)\n\n"
    
    # 转换 markdown 到 HTML
    message = header + summary
    # 简单的 markdown 到 HTML 转换
    message = message.replace("**", "<b>").replace("</b><b>", "")
    # 确保 bold 标签成对
    bold_count = message.count("<b>")
    if bold_count % 2 == 1:
        message += "</b>"
    
    result = send_telegram_message(message, pin_message=False)
    return result is not None and result.get("success", False)


def generate_market_summary(force: bool = False) -> Optional[str]:
    """
    生成市场总结
    
    Args:
        force: 是否强制生成（忽略时间间隔）
    
    Returns:
        生成的总结文本，失败返回 None
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
    
    logger.info("开始生成 AI 市场总结...")
    
    # 收集数据
    lookback = config.get("lookback_hours", 1)
    signals = _collect_recent_signals(lookback)
    movements = _collect_movement_data()
    
    # 提取热门币种用于量化数据查询
    hot_symbols = ["BTC", "ETH"]  # 始终包含主流币
    for category in ["bullish", "bearish", "arbitrage", "whale"]:
        for sig in signals.get(category, []):
            sym = sig.get("symbol", "")
            if sym and sym.upper() not in [s.upper() for s in hot_symbols]:
                hot_symbols.append(sym.upper())
    
    # 添加 Alpha 和 FOMO 币种
    for sym in movements.get("alpha_coins", [])[:5]:
        if sym and sym.upper() not in [s.upper() for s in hot_symbols]:
            hot_symbols.append(sym.upper())
    for sym in movements.get("fomo_coins", [])[:5]:
        if sym and sym.upper() not in [s.upper() for s in hot_symbols]:
            hot_symbols.append(sym.upper())
    
    # 收集量化数据
    logger.info("获取量化数据...")
    quant_data = _collect_quantitative_data(hot_symbols[:10])
    
    # 获取新闻数据
    logger.info("获取新闻数据...")
    news = _fetch_crypto_news()
    
    if signals.get("total_count", 0) == 0 and not quant_data.get("coins") and not news:
        logger.info("没有足够的数据，跳过总结")
        return None
    
    # 构建 prompt
    prompt = _build_ai_prompt(signals, movements, quant_data, news)
    
    # 调用 AI
    summary = _call_ai_api(prompt, config)
    if not summary:
        logger.error("AI 生成总结失败")
        return None
    
    logger.info("AI 市场总结生成成功")
    _last_summary_time = now
    
    # 发送到 Telegram
    if _send_summary_to_telegram(summary):
        logger.info("市场总结已发送到 Telegram")
    else:
        logger.warning("市场总结发送到 Telegram 失败")
    
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
