#!/usr/bin/env python3
"""
AI 市场宏观分析模块

功能：
1. 收集 BTC/ETH OHLCV K线数据
2. 收集市场快照数据（价格/成交额/市值）
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

from market_data_sources import fetch_market_snapshot, fetch_news, fetch_trending

logger = logging.getLogger(__name__)

# 北京时区
BEIJING_TZ = timezone(timedelta(hours=8))

# 配置
AI_SUMMARY_ENABLED = os.getenv("VALUESCAN_AI_SUMMARY_ENABLED", "0") == "1"
AI_SUMMARY_INTERVAL_HOURS = float(os.getenv("VALUESCAN_AI_SUMMARY_INTERVAL_HOURS", "1"))
AI_SUMMARY_API_KEY = os.getenv("VALUESCAN_AI_SUMMARY_API_KEY", "sk-chat2api").strip()
AI_SUMMARY_API_URL = os.getenv(
    "VALUESCAN_AI_SUMMARY_API_URL",
    "https://chat.cornna.xyz/chatgpt/v1/chat/completions"
).strip()
AI_SUMMARY_MODEL = os.getenv("VALUESCAN_AI_SUMMARY_MODEL", "gpt-5.2").strip()

# 数据收集时间范围（小时）- 改为2天（48小时）
SIGNAL_LOOKBACK_HOURS = float(os.getenv("VALUESCAN_SIGNAL_LOOKBACK_HOURS", "48"))
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


def _compact_valuescan_history(resp: Optional[Dict[str, Any]], limit: int = 30) -> List[Dict[str, Any]]:
    items = _extract_valuescan_list(resp)
    if not items:
        return []
    return items[:limit]


def _compact_holder_items(resp: Optional[Dict[str, Any]], limit: int = 3) -> List[Dict[str, Any]]:
    items = _extract_valuescan_list(resp)
    if not items:
        return []
    trimmed: List[Dict[str, Any]] = []
    for item in items[:limit]:
        trimmed.append({
            "address": item.get("address"),
            "balance": item.get("balance"),
            "balancePercent": item.get("balancePercent"),
            "chainName": item.get("chainName"),
        })
    return trimmed


def _compact_chain_items(resp: Optional[Dict[str, Any]], limit: int = 5) -> List[Dict[str, Any]]:
    items = _extract_valuescan_list(resp)
    if not items:
        return []
    trimmed: List[Dict[str, Any]] = []
    for item in items[:limit]:
        trimmed.append({
            "chainName": item.get("chainName"),
            "contractAddress": item.get("contractAddress"),
            "coinKey": item.get("coinKey"),
        })
    return trimmed


BULL_BEAR_SIGNAL_TTL_SECONDS = _read_int_env_or_config(
    "VALUESCAN_BULL_BEAR_SIGNAL_TTL_SECONDS",
    "BULL_BEAR_SIGNAL_TTL_SECONDS",
    86400,
)
_BULLISH_SIGNAL_TYPES = {108, 110, 111, 100, 101}
_BEARISH_SIGNAL_TYPES = {109, 112, 102, 103}


def _get_language() -> str:
    lang = (os.getenv("VALUESCAN_LANGUAGE") or os.getenv("LANGUAGE") or "").strip().lower()
    if not lang:
        try:
            import config as signal_config
            lang = getattr(signal_config, "LANGUAGE", "").strip().lower()
        except Exception:
            lang = ""
    if lang not in ("zh", "en"):
        lang = "zh"
    return lang

# Binance Futures API
BINANCE_FUTURES_BASE = "https://fapi.binance.com"

# 代理配置 - Clash 代理在 7890 端口
PROXY_URL = os.getenv("VALUESCAN_PROXY") or os.getenv("HTTP_PROXY") or "http://127.0.0.1:7890"

def _get_proxies():
    """获取代理配置"""
    if PROXY_URL:
        return {"http": PROXY_URL, "https": PROXY_URL}
    return None

# 加密新闻 API（可选）
CRYPTO_NEWS_API_KEY = os.getenv("CRYPTO_NEWS_API_KEY", "").strip()

# 主要分析币种
MAJOR_COINS = ["BTC", "ETH"]

# 上次总结时间
_last_summary_time: float = 0.0


def _load_config() -> Dict[str, Any]:
    """从配置文件加载 AI 总结配置（AI简评专用）"""
    config_path = Path(__file__).parent / "ai_summary_config.json"
    if config_path.exists():
        try:
            return json.loads(config_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _load_market_config() -> Dict[str, Any]:
    """从配置文件加载 AI 市场分析配置"""
    config_path = Path(__file__).parent / "ai_market_summary_config.json"
    if config_path.exists():
        try:
            return json.loads(config_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    # 如果不存在，尝试从旧配置迁移
    return _load_config()


def _save_config(config: Dict[str, Any]) -> bool:
    """保存 AI 总结配置（AI简评专用）"""
    config_path = Path(__file__).parent / "ai_summary_config.json"
    try:
        config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except Exception as e:
        logger.error("保存 AI 总结配置失败: %s", e)
        return False


def _save_market_config(config: Dict[str, Any]) -> bool:
    """保存 AI 市场分析配置"""
    config_path = Path(__file__).parent / "ai_market_summary_config.json"
    try:
        config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except Exception as e:
        logger.error("保存 AI 市场分析配置失败: %s", e)
        return False


def get_ai_summary_config() -> Dict[str, Any]:
    """获取 AI 总结配置（AI简评专用）"""
    file_config = _load_config()
    return {
        "enabled": file_config.get("enabled", AI_SUMMARY_ENABLED),
        "interval_hours": file_config.get("interval_hours", AI_SUMMARY_INTERVAL_HOURS),
        "api_key": file_config.get("api_key", AI_SUMMARY_API_KEY),
        "api_url": file_config.get("api_url", AI_SUMMARY_API_URL),
        "model": file_config.get("model", AI_SUMMARY_MODEL),
        "lookback_hours": file_config.get("lookback_hours", SIGNAL_LOOKBACK_HOURS),
    }


def get_ai_market_config() -> Dict[str, Any]:
    """获取 AI 市场分析配置"""
    file_config = _load_market_config()
    return {
        "enabled": file_config.get("enabled", AI_SUMMARY_ENABLED),
        "interval_hours": file_config.get("interval_hours", AI_SUMMARY_INTERVAL_HOURS),
        "api_key": file_config.get("api_key", AI_SUMMARY_API_KEY),
        "api_url": file_config.get("api_url", AI_SUMMARY_API_URL),
        "model": file_config.get("model", AI_SUMMARY_MODEL),
        "lookback_hours": file_config.get("lookback_hours", SIGNAL_LOOKBACK_HOURS),
    }


def _load_overlays_config() -> Dict[str, Any]:
    """从配置文件加载 AI Overlays 配置"""
    config_path = Path(__file__).parent / "ai_overlays_config.json"
    if config_path.exists():
        try:
            return json.loads(config_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    # 如果不存在，回退到 ai_summary_config.json
    return _load_config()


def get_ai_overlays_config() -> Dict[str, Any]:
    """获取 AI Overlays（画线）配置"""
    file_config = _load_overlays_config()
    return {
        "enabled": file_config.get("enabled", AI_SUMMARY_ENABLED),
        "api_key": file_config.get("api_key", AI_SUMMARY_API_KEY),
        "api_url": file_config.get("api_url", AI_SUMMARY_API_URL),
        "model": file_config.get("model", AI_SUMMARY_MODEL),
    }



def update_ai_summary_config(config: Dict[str, Any]) -> bool:
    """更新 AI 总结配置（AI简评专用）"""
    return _save_config(config)


def update_ai_market_config(config: Dict[str, Any]) -> bool:
    """更新 AI 市场分析配置"""
    return _save_market_config(config)


def _collect_recent_signals(lookback_hours: float = 48.0) -> Dict[str, Any]:
    """
    收集最近的 ValueScan 信号数据（默认2天）

    Returns:
        包含各类信号和币种推荐的字典
    """
    from database import MessageDatabase

    cutoff_time = time.time() - (lookback_hours * 3600)
    cutoff_ms = int(cutoff_time * 1000)

    def _normalize_timestamp_ms(value: Any) -> int:
        try:
            ts = float(value)
        except (TypeError, ValueError):
            return 0
        if ts <= 0:
            return 0
        if ts > 1e11:
            return int(ts)
        return int(ts * 1000)

    try:
        db = MessageDatabase()
        messages = db.get_recent_messages_for_ai(limit=500, since_timestamp_ms=cutoff_ms)
    except Exception as e:
        logger.warning("获取最近消息失败: %s", e)
        messages = []

    # 分类信号
    bullish_signals = []  # 看涨信号
    bearish_signals = []  # 看跌信号
    arbitrage_signals = []  # 套利机会
    whale_signals = []  # 大户动向
    other_signals = []  # 其他信号

    # 币种信号统计 {symbol: {"bullish": count, "bearish": count, "whale": count, "latest_time": timestamp}}
    coin_signal_stats = {}

    now_ms = int(time.time() * 1000)
    for msg in messages:
        msg_type = msg.get("type") or msg.get("messageType")
        symbol_raw = msg.get("symbol") or ""
        symbol = symbol_raw.upper().replace("USDT", "").replace("PERP", "") if symbol_raw else ""
        content = msg.get("content", "") or msg.get("message", "")
        msg_time = msg.get("createTime") or msg.get("timestamp") or 0
        msg_time_ms = _normalize_timestamp_ms(msg_time)

        if msg_type in _BULLISH_SIGNAL_TYPES or msg_type in _BEARISH_SIGNAL_TYPES:
            if BULL_BEAR_SIGNAL_TTL_SECONDS > 0 and msg_time_ms:
                if now_ms - msg_time_ms > BULL_BEAR_SIGNAL_TTL_SECONDS * 1000:
                    continue

        if not symbol:
            continue

        signal_info = {
            "symbol": symbol,
            "type": msg_type,
            "content": content[:200] if content else "",
            "time": msg_time_ms or msg_time,
        }

        # 初始化币种统计
        if symbol not in coin_signal_stats:
            coin_signal_stats[symbol] = {
                "bullish": 0,
                "bearish": 0,
                "whale": 0,
                "arbitrage": 0,
                "latest_time": 0,
                "signals": []
            }

        # 更新最新时间
        if msg_time_ms > coin_signal_stats[symbol]["latest_time"]:
            coin_signal_stats[symbol]["latest_time"] = msg_time_ms

        # 根据类型分类并统计
        if msg_type in _BULLISH_SIGNAL_TYPES:  # 大单买入、资金流入、看涨信号等
            bullish_signals.append(signal_info)
            coin_signal_stats[symbol]["bullish"] += 1
            coin_signal_stats[symbol]["signals"].append({"type": "bullish", "time": msg_time_ms})
        elif msg_type in _BEARISH_SIGNAL_TYPES:  # 大单卖出、资金流出、看跌信号等
            bearish_signals.append(signal_info)
            coin_signal_stats[symbol]["bearish"] += 1
            coin_signal_stats[symbol]["signals"].append({"type": "bearish", "time": msg_time_ms})
        elif msg_type in (113, 114):  # 套利相关
            arbitrage_signals.append(signal_info)
            coin_signal_stats[symbol]["arbitrage"] += 1
        elif msg_type in (115, 116):  # 大户动向
            whale_signals.append(signal_info)
            coin_signal_stats[symbol]["whale"] += 1
            coin_signal_stats[symbol]["signals"].append({"type": "whale", "time": msg_time})
        else:
            other_signals.append(signal_info)

    # 生成币种推荐
    bullish_coins = []  # 看涨币种
    bearish_coins = []  # 看跌币种
    opportunity_coins = []  # 机会币种（有巨鲸活动或套利机会）

    for symbol, stats in coin_signal_stats.items():
        total_signals = stats["bullish"] + stats["bearish"] + stats["whale"] + stats["arbitrage"]
        if total_signals < 2:  # 至少2个信号才考虑
            continue

        bullish_score = stats["bullish"] * 1.0 + stats["whale"] * 0.5
        bearish_score = stats["bearish"] * 1.0

        coin_info = {
            "symbol": symbol,
            "bullish_count": stats["bullish"],
            "bearish_count": stats["bearish"],
            "whale_count": stats["whale"],
            "arbitrage_count": stats["arbitrage"],
            "total_signals": total_signals,
            "score": bullish_score - bearish_score,
            "latest_time": stats["latest_time"]
        }

        # 看涨币种：看涨信号明显多于看跌信号
        if bullish_score >= bearish_score * 1.5 and stats["bullish"] >= 2:
            bullish_coins.append(coin_info)

        # 看跌币种：看跌信号明显多于看涨信号
        elif bearish_score >= bullish_score * 1.5 and stats["bearish"] >= 2:
            bearish_coins.append(coin_info)

        # 机会币种：有巨鲸活动或套利机会
        if stats["whale"] >= 2 or stats["arbitrage"] >= 2:
            opportunity_coins.append(coin_info)

    # 按信号数量和得分排序
    bullish_coins.sort(key=lambda x: (x["total_signals"], x["score"]), reverse=True)
    bearish_coins.sort(key=lambda x: (x["total_signals"], -x["score"]), reverse=True)
    opportunity_coins.sort(key=lambda x: (x["whale_count"] + x["arbitrage_count"], x["total_signals"]), reverse=True)

    return {
        "bullish": bullish_signals,
        "bearish": bearish_signals,
        "arbitrage": arbitrage_signals,
        "whale": whale_signals,
        "other": other_signals,
        "total_count": len(messages),
        "lookback_hours": lookback_hours,
        # 币种推荐
        "recommended_bullish": bullish_coins[:5],  # 前5个看涨币种
        "recommended_bearish": bearish_coins[:5],  # 前5个看跌币种
        "recommended_opportunity": opportunity_coins[:5],  # 前5个机会币种
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
        proxies = _get_proxies()
        resp = requests.get(url, params=params, timeout=15, proxies=proxies)
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


def _fetch_binance_open_interest(symbol: str) -> Optional[float]:
    base = symbol.upper().replace("$", "")
    if not base.endswith("USDT"):
        base = f"{base}USDT"
    url = f"{BINANCE_FUTURES_BASE}/fapi/v1/openInterest"
    try:
        resp = requests.get(url, params={"symbol": base}, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return float(data.get("openInterest", 0) or 0)
    except Exception as e:
        logger.debug("获取 OI 失败: %s", e)
    return None


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
            "market": {},
            "open_interest": None,
        }

        # 收集不同周期K线数据
        for interval, key in [("1h", "klines_1h"), ("4h", "klines_4h"), ("1d", "klines_1d")]:
            klines = _fetch_binance_klines(symbol, interval, limit=24)
            if klines:
                coin_data[key] = _analyze_klines(klines)

        # 市场数据（CMC/CG/CC 数据源）
        market = fetch_market_snapshot(symbol)
        if market:
            coin_data["market"] = market

        # Binance OI
        coin_data["open_interest"] = _fetch_binance_open_interest(symbol)

        result[symbol] = coin_data
    
    return result


def _collect_valuescan_macro_data(symbols: List[str]) -> Dict[str, Dict[str, Any]]:
    result: Dict[str, Dict[str, Any]] = {}
    try:
        import sys
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if base_dir not in sys.path:
            sys.path.insert(0, base_dir)
        from valuescan_api import (
            get_main_force,
            get_hold_cost,
            get_inflow,
            get_detailed_inflow,
            get_token_flow,
            get_whale_flow,
            get_opportunity_signals,
            get_risk_signals,
            get_exchange_flow_detail,
            get_fund_trade_history_total,
            get_holder_page,
            get_chain_page,
        )
    except Exception as exc:
        logger.debug("ValuScan macro data import failed: %s", exc)
        return result

    for symbol in symbols:
        clean_symbol = symbol.upper().replace("USDT", "").replace("$", "").strip()
        item: Dict[str, Any] = {"symbol": clean_symbol}

        try:
            mf = get_main_force(clean_symbol, 15)
            if mf.get("code") == 200:
                mf_data = mf.get("data", [])
                if mf_data:
                    item["main_force"] = float(mf_data[-1]["price"])
        except Exception:
            pass

        try:
            hc = get_hold_cost(clean_symbol, 14)
            if hc.get("code") == 200:
                hc_data = hc.get("data", {}).get("holdingPrice", [])
                if hc_data:
                    item["main_cost"] = float(hc_data[-1]["val"])
        except Exception:
            pass

        try:
            inflow = get_inflow(clean_symbol)
            if inflow.get("code") == 200:
                item["trade_inflow"] = inflow.get("data", {})
        except Exception:
            pass

        try:
            detailed = get_detailed_inflow(clean_symbol)
            if detailed.get("code") == 200:
                item["detailed_inflow"] = detailed.get("data", {})
        except Exception:
            pass

        try:
            tf = get_token_flow("H12", 1, 20)
            if tf.get("code") == 200:
                item["token_flow"] = tf.get("data", {})
        except Exception:
            pass

        try:
            wf = get_whale_flow(1, "m5", 1, 20)
            if wf.get("code") == 200:
                item["whale_flow"] = wf.get("data", {})
        except Exception:
            pass

        try:
            os_data = get_opportunity_signals(1, 10)
            if os_data.get("code") == 200:
                item["opportunity_signals"] = os_data.get("data", {})
        except Exception:
            pass

        try:
            rs_data = get_risk_signals(1, 10)
            if rs_data.get("code") == 200:
                item["risk_signals"] = rs_data.get("data", {})
        except Exception:
            pass

        try:
            flow_detail = _normalize_exchange_flow_detail(get_exchange_flow_detail(clean_symbol))
            if flow_detail:
                item["exchange_flow_detail"] = flow_detail
        except Exception:
            pass

        try:
            flow_history = _compact_valuescan_history(
                get_fund_trade_history_total(
                    clean_symbol,
                    time_particle="12h",
                    limit_size=30,
                    flow=True,
                    trade_type=2,
                ),
                limit=30,
            )
            if flow_history:
                item["fund_flow_history"] = flow_history
        except Exception:
            pass

        try:
            volume_history = _compact_valuescan_history(
                get_fund_trade_history_total(
                    clean_symbol,
                    time_particle="12h",
                    limit_size=30,
                    flow=False,
                    trade_type=2,
                ),
                limit=30,
            )
            if volume_history:
                item["fund_volume_history"] = volume_history
        except Exception:
            pass

        try:
            holders = _compact_holder_items(get_holder_page(clean_symbol, page=1, page_size=5), limit=3)
            if holders:
                item["holders_top"] = holders
        except Exception:
            pass

        try:
            chains = _compact_chain_items(get_chain_page(clean_symbol, page=1, page_size=5), limit=5)
            if chains:
                item["chains"] = chains
        except Exception:
            pass

        if len(item) > 1:
            result[clean_symbol] = item

    return result


def _collect_quantitative_data(symbols: List[str]) -> Dict[str, Any]:
    """
    Collect quantitative snapshot data for a set of symbols.

    Args:
        symbols: symbols to query

    Returns:
        Aggregated quantitative data
    """
    if not symbols:
        return {"coins": [], "summary": {}}

    symbols_to_fetch = list(set(symbols))[:10]

    coin_data = []
    bullish_coins = []
    bearish_coins = []
    high_volume_coins = []

    for sym in symbols_to_fetch:
        data = fetch_market_snapshot(sym)
        if not data:
            continue

        coin_info = {
            "symbol": sym,
            "price": data.get("price"),
            "price_change_24h": data.get("price_change_percent"),
            "volume_24h": data.get("volume_24h"),
            "market_cap": data.get("market_cap"),
        }
        coin_data.append(coin_info)

        change = data.get("price_change_percent")
        if isinstance(change, (int, float)):
            if change >= 2:
                bullish_coins.append(sym)
            elif change <= -2:
                bearish_coins.append(sym)

        vol = data.get("volume_24h")
        if isinstance(vol, (int, float)) and vol >= 1e8:
            high_volume_coins.append(sym)

    return {
        "coins": coin_data,
        "summary": {
            "bullish_price": bullish_coins,
            "bearish_price": bearish_coins,
            "high_volume": high_volume_coins,
        },
    }


def _fetch_crypto_news() -> List[Dict[str, Any]]:
    """Fetch market news and trending coins."""
    news = []
    try:
        news = fetch_news(limit=5)
    except Exception as e:
        logger.debug("fetch_news failed: %s", e)

    trending = []
    try:
        trending = fetch_trending(limit=5)
    except Exception as e:
        logger.debug("fetch_trending failed: %s", e)

    if trending:
        news.append({
            "title": "Trending Coins",
            "source": "Market",
            "coins": trending,
        })
    return news


def _build_macro_analysis_prompt(
    major_coin_data: Dict[str, Dict[str, Any]],
    oi_ranking: List[Dict[str, Any]],
    signals: Dict[str, Any],
    valuescan_data: Optional[Dict[str, Dict[str, Any]]] = None,
    news: Optional[List[Dict[str, Any]]] = None,
    language: str = "zh",
) -> str:
    """Build macro summary prompt."""
    now = datetime.now(BEIJING_TZ)
    lines: List[str] = []
    sep = "\n"
    def _fmt_value(value):
        return f"{value:.2f}" if isinstance(value, (int, float)) else "N/A"

    def _compact_value(value, max_keys=4):
        if isinstance(value, dict):
            out = {}
            for idx, (key, val) in enumerate(value.items()):
                if idx >= max_keys:
                    break
                out[key] = val
            return out
        return value

    def _fmt_json(value):
        if value is None:
            return "N/A"
        return json.dumps(_compact_value(value), ensure_ascii=False)


    if language == "en":
        lines.append("You are a top crypto macro analyst. Produce a concise macro report based on the data.")
        lines.append("Priority: If ValuScan data exists, treat it as the highest-priority source; other data is supplementary.")
        lines.append(f"**Analysis Time**: {now.strftime('%Y-%m-%d %H:%M')} (Beijing Time)")
        lines.append("")
        lines.append("BTC/ETH Core Data:")
        for symbol in MAJOR_COINS:
            data = major_coin_data.get(symbol, {})
            lines.append("")
            lines.append(f"### {symbol}")
            for tf, key in [("1h", "klines_1h"), ("4h", "klines_4h"), ("1d", "klines_1d")]:
                kl = data.get(key, {})
                if kl:
                    lines.append(
                        f"{tf}: trend={kl.get('trend','N/A')}, price={kl.get('latest_price',0):.2f}, "
                        f"change={kl.get('price_change_pct',0):.2f}%, range={kl.get('price_range_pct',0):.2f}%, "
                        f"volume={kl.get('volume_ratio',1):.2f}x, MA5={kl.get('ma5',0):.2f}, MA10={kl.get('ma10',0):.2f}"
                    )
            market = data.get("market", {})
            if market:
                lines.append(
                    f"Market: price=${market.get('price',0):.2f}, change_24h={market.get('price_change_percent',0):.2f}%, "
                    f"volume_24h={market.get('volume_24h',0):.2f}, mcap={market.get('market_cap',0):.2f}, source={market.get('source','')}"
                )
            oi = data.get("open_interest")
            if oi:
                lines.append(f"Open Interest: {oi:.2f}")
            vs = valuescan_data.get(symbol, {}) if valuescan_data else {}
            if vs:
                main_force = vs.get("main_force")
                main_cost = vs.get("main_cost")
                if main_force or main_cost:
                    lines.append(
                        f"ValuScan Levels: main_force={_fmt_value(main_force)}, main_cost={_fmt_value(main_cost)}"
                    )
                trade_inflow = vs.get("trade_inflow")
                detailed_inflow = vs.get("detailed_inflow")
                if trade_inflow or detailed_inflow:
                    lines.append(
                        f"ValuScan Flow: trade_inflow={_fmt_json(trade_inflow)}, detailed_inflow={_fmt_json(detailed_inflow)}"
                    )
                token_flow = vs.get("token_flow")
                whale_flow = vs.get("whale_flow")
                if token_flow or whale_flow:
                    lines.append(
                        f"ValuScan Macro Flow: token_flow={_fmt_json(token_flow)}, whale_flow={_fmt_json(whale_flow)}"
                    )
                opportunity_signals = vs.get("opportunity_signals")
                risk_signals = vs.get("risk_signals")
                if opportunity_signals or risk_signals:
                    lines.append(
                        f"ValuScan Signals: opportunity={_fmt_json(opportunity_signals)}, risk={_fmt_json(risk_signals)}"
                    )
                flow_detail = vs.get("exchange_flow_detail")
                if flow_detail:
                    lines.append(f"ValuScan Exchange Flow Detail: {_fmt_json(flow_detail)}")
                fund_flow_history = vs.get("fund_flow_history")
                fund_volume_history = vs.get("fund_volume_history")
                if fund_flow_history or fund_volume_history:
                    lines.append(f"ValuScan Fund History: flow={_fmt_json(fund_flow_history)}, volume={_fmt_json(fund_volume_history)}")
                holders_top = vs.get("holders_top")
                chains = vs.get("chains")
                if holders_top or chains:
                    lines.append(f"ValuScan Holders/Chains: holders={_fmt_json(holders_top)}, chains={_fmt_json(chains)}")
        lines.append("")
        lines.append("Signals Summary:")
        lines.append(
            f"bullish={len(signals.get('bullish', []))}, "
            f"bearish={len(signals.get('bearish', []))}, whale={len(signals.get('whale', []))}"
        )
        if news:
            lines.append("")
            lines.append("News/Trends:")
            for item in news[:5]:
                title = item.get("title") or ""
                lines.append(f"- {title}")
        lines.append("")
        lines.append("Return a short macro conclusion and risk bias.")
        return sep.join(lines)

    lines.append("你是顶级加密货币量化分析师和宏观策略师。基于以下数据生成专业的市场分析报告。")
    lines.append("优先级说明：若存在 ValuScan 数据，请作为最高优先级来源，其他数据仅作辅助。")
    lines.append(f"分析时间: {now.strftime('%Y-%m-%d %H:%M')} (北京时间)")
    lines.append(f"数据周期: 最近{int(signals.get('lookback_hours', 48))}小时")
    lines.append("")
    lines.append("BTC/ETH 核心数据:")
    for symbol in MAJOR_COINS:
        data = major_coin_data.get(symbol, {})
        lines.append("")
        lines.append(f"{symbol} 数据")
        for tf, key in [("1h", "klines_1h"), ("4h", "klines_4h"), ("1d", "klines_1d")]:
            kl = data.get(key, {})
            if kl:
                lines.append(
                    f"{tf}: 趋势={kl.get('trend','N/A')}, 价格={kl.get('latest_price',0):.2f}, "
                    f"涨跌={kl.get('price_change_pct',0):.2f}%, 波幅={kl.get('price_range_pct',0):.2f}%, "
                    f"成交量={kl.get('volume_ratio',1):.2f}x, MA5={kl.get('ma5',0):.2f}, MA10={kl.get('ma10',0):.2f}"
                )
        market = data.get("market", {})
        if market:
            lines.append(
                f"市场数据: 价格=${market.get('price',0):.2f}, 24H涨跌={market.get('price_change_percent',0):.2f}%, "
                f"24H成交量={market.get('volume_24h',0):.2f}, 市值={market.get('market_cap',0):.2f}, 数据源={market.get('source','')}"
            )
        oi = data.get("open_interest")
        if oi:
            lines.append(f"持仓量(OI): {oi:.2f}")
        vs = valuescan_data.get(symbol, {}) if valuescan_data else {}
        if vs:
            main_force = vs.get("main_force")
            main_cost = vs.get("main_cost")
            if main_force or main_cost:
                lines.append(
                    f"ValuScan 主力位: main_force={_fmt_value(main_force)}, main_cost={_fmt_value(main_cost)}"
                )
            trade_inflow = vs.get("trade_inflow")
            detailed_inflow = vs.get("detailed_inflow")
            if trade_inflow or detailed_inflow:
                lines.append(
                    f"ValuScan 资金流: trade_inflow={_fmt_json(trade_inflow)}, detailed_inflow={_fmt_json(detailed_inflow)}"
                )
            token_flow = vs.get("token_flow")
            whale_flow = vs.get("whale_flow")
            if token_flow or whale_flow:
                lines.append(
                    f"ValuScan ???? token_flow={_fmt_json(token_flow)}, whale_flow={_fmt_json(whale_flow)}"
                )
            opportunity_signals = vs.get("opportunity_signals")
            risk_signals = vs.get("risk_signals")
            if opportunity_signals or risk_signals:
                lines.append(
                    f"ValuScan ?? opportunity={_fmt_json(opportunity_signals)}, risk={_fmt_json(risk_signals)}"
                )
            flow_detail = vs.get("exchange_flow_detail")
            if flow_detail:
                lines.append(f"ValuScan ????????????: exchange_flow_detail={_fmt_json(flow_detail)}")
            fund_flow_history = vs.get("fund_flow_history")
            fund_volume_history = vs.get("fund_volume_history")
            if fund_flow_history or fund_volume_history:
                lines.append(f"ValuScan ????????????: flow={_fmt_json(fund_flow_history)}, volume={_fmt_json(fund_volume_history)}")
            holders_top = vs.get("holders_top")
            chains = vs.get("chains")
            if holders_top or chains:
                lines.append(f"ValuScan ??????/?????????: holders={_fmt_json(holders_top)}, chains={_fmt_json(chains)}")
    lines.append("")
    lines.append("信号汇总:")
    lines.append(f"看涨={len(signals.get('bullish', []))}个, 看跌={len(signals.get('bearish', []))}个, 巨鲸={len(signals.get('whale', []))}个")

    # 添加币种推荐数据
    bullish_coins = signals.get("recommended_bullish", [])
    bearish_coins = signals.get("recommended_bearish", [])
    opportunity_coins = signals.get("recommended_opportunity", [])

    if bullish_coins:
        lines.append("")
        lines.append("看涨币种推荐（按信号强度排序）:")
        for coin in bullish_coins[:3]:  # 只显示前3个
            lines.append(
                f"- {coin['symbol']}: 看涨信号{coin['bullish_count']}个, "
                f"看跌信号{coin['bearish_count']}个, 巨鲸{coin['whale_count']}个"
            )

    if bearish_coins:
        lines.append("")
        lines.append("看跌币种推荐（按信号强度排序）:")
        for coin in bearish_coins[:3]:  # 只显示前3个
            lines.append(
                f"- {coin['symbol']}: 看跌信号{coin['bearish_count']}个, "
                f"看涨信号{coin['bullish_count']}个"
            )

    if opportunity_coins:
        lines.append("")
        lines.append("机会币种推荐（巨鲸活动/套利机会）:")
        for coin in opportunity_coins[:3]:  # 只显示前3个
            lines.append(
                f"- {coin['symbol']}: 巨鲸{coin['whale_count']}个, "
                f"套利{coin['arbitrage_count']}个, 总信号{coin['total_signals']}个"
            )

    if news:
        lines.append("")
        lines.append("新闻/热点:")
        for item in news[:5]:
            title = item.get("title") or ""
            lines.append(f"- {title}")
    lines.append("")
    lines.append("【分析要求】")
    lines.append("生成一份精炼的市场分析报告，包含以下5个部分：")
    lines.append("")
    lines.append("1. 市场概况（60-80字）")
    lines.append("   BTC/ETH价格、涨跌幅、持仓量，市场情绪")
    lines.append("")
    lines.append("2. 技术分析（80-100字）")
    lines.append("   多周期趋势，关键支撑阻力位（格式：BTC支撑85000/83500，阻力90000/92500）")
    lines.append("")
    lines.append("3. 币种推荐（80-100字）")
    lines.append("   基于信号数据，推荐2-3个看涨币种、2-3个看跌币种、2-3个机会币种")
    lines.append("   格式：【看涨】BTC、ETH（理由）【看跌】DOGE（理由）【机会】LINK（理由）")
    lines.append("")
    lines.append("4. 趋势研判（60-80字）")
    lines.append("   短期（1-3天）趋势：看多/看空/震荡，概率和触发条件")
    lines.append("")
    lines.append("5. 操作策略（60-80字）")
    lines.append("   仓位建议、入场点位、止损位、目标位")
    lines.append("")
    lines.append("【格式要求】")
    lines.append("1. 不使用markdown符号（不要*、#、-、>等）")
    lines.append("2. 纯文本格式，段落间空行分隔")
    lines.append("3. 重点用【】标注，如【核心观点】【风险警示】")
    lines.append("4. 数据精确引用，如：BTC价格87576美元，涨幅0.69%")
    lines.append("5. 总字数控制在400-500字")
    lines.append("6. 言简意赅，专业深度，避免废话")
    return sep.join(lines)


def _call_ai_api(prompt: str, config: Dict[str, Any], language: str = "zh") -> Optional[str]:
    """调用 AI API 生成分析"""
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

    system_prompt = (
        "You are a professional crypto market analyst. Output plain text only, no markdown symbols."
        if language == "en"
        else "你是专业的加密货币市场分析师。只输出纯文本，不要使用任何markdown符号（不要用*、#、-、>等）。"
    )

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 4000,  # 增加到4000以确保完整输出
        "temperature": 0.7,
    }

    try:
        # 显式禁用代理直接连接 AI API
        logger.info(f"[AI Market] 调用 AI API: {api_url} (无代理)")
        session = requests.Session()
        session.trust_env = False
        resp = session.post(api_url, headers=headers, json=payload, timeout=120)
        if resp.status_code != 200:
            logger.error("AI API 返回错误: %s - %s", resp.status_code, resp.text[:200])
            return None
        data = resp.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        logger.info(f"[AI Market] AI API 返回成功，内容长度: {len(content) if content else 0}")
        return content.strip() if content else None
    except Exception as e:
        logger.error("AI API 调用失败: %s", e)
        return None


def _send_summary_to_telegram(summary: str, language: str = "zh") -> bool:
    """发送总结到 Telegram"""
    from telegram import send_telegram_message
    
    now = datetime.now(BEIJING_TZ)
    if language == "en":
        header = f"📊 AI Market Summary\n⏰ {now.strftime('%Y-%m-%d %H:%M')} (Beijing Time)\n\n"
    else:
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

    # 使用AI市场分析的独立配置
    config = get_ai_market_config()
    language = _get_language()

    if not config.get("enabled") and not force:
        logger.debug("AI 市场总结功能未启用")
        return None

    # 检查时间间隔
    interval_seconds = config.get("interval_hours", 1) * 3600
    now = time.time()
    if not force and (now - _last_summary_time) < interval_seconds:
        logger.debug("距离上次总结时间不足，跳过")
        return None

    logger.info("=" * 60)
    logger.info("🚀 开始生成 AI 宏观市场分析...")
    logger.info("=" * 60)

    try:
        # 1. 收集 BTC/ETH 核心数据（K线 + 量化数据）
        logger.info("📊 [1/6] 收集 BTC/ETH 核心数据...")
        major_coin_data = _collect_major_coin_data()
        logger.info(f"   ✅ 收集到 {len(major_coin_data)} 个主流币数据")

        # 2. 获取 OI 排行数据
        logger.info("📈 [2/6] 获取 OI 排行数据...")
        oi_ranking = []
        logger.info(f"   ✅ OI 排行数据: {len(oi_ranking)} 条")

        # 3. 收集 ValueScan 信号数据
        lookback = config.get("lookback_hours", 1)
        logger.info(f"🔍 [3/6] 收集最近 {lookback} 小时信号数据...")
        signals = _collect_recent_signals(lookback)
        total_signals = signals.get("total_count", 0)
        valuescan_macro = _collect_valuescan_macro_data(MAJOR_COINS)
        if valuescan_macro:
            logger.info("   ValuScan macro data: %s symbols", len(valuescan_macro))
        else:
            logger.info("   ValuScan macro data not available")
        logger.info(f"   ✅ 收集到 {total_signals} 个信号")

        # 4. 获取新闻数据
        logger.info("📰 [4/6] 获取市场新闻...")
        news = _fetch_crypto_news()
        logger.info(f"   ✅ 收集到 {len(news) if news else 0} 条新闻")

        # 检查是否有足够数据
        if not major_coin_data and not oi_ranking and total_signals == 0:
            logger.warning("⚠️  没有足够的数据，跳过总结")
            return None

        # 5. 构建专业宏观分析 prompt
        logger.info("🤖 [5/6] 调用 AI 生成分析...")
        prompt = _build_macro_analysis_prompt(major_coin_data, oi_ranking, signals, valuescan_macro, news, language=language)

        # 调用 AI
        summary = _call_ai_api(prompt, config, language=language)
        if not summary:
            logger.error("❌ AI 生成分析失败")
            return None

        logger.info(f"   ✅ AI 分析生成成功 ({len(summary)} 字符)")
        _last_summary_time = now

        # 6. 发送到 Telegram
        logger.info("📤 [6/6] 发送到 Telegram...")
        if _send_summary_to_telegram(summary, language=language):
            logger.info("   ✅ 市场分析已发送到 Telegram")
        else:
            logger.warning("   ⚠️  市场分析发送到 Telegram 失败")

        logger.info("=" * 60)
        logger.info("✅ AI 宏观市场分析完成！")
        logger.info("=" * 60)

        return summary

    except Exception as e:
        logger.error(f"❌ 生成市场分析时出错: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


def check_and_generate_summary() -> None:
    """
    检查是否需要生成总结（由 polling_monitor 定期调用）
    """
    # 使用AI市场分析的独立配置
    config = get_ai_market_config()
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
