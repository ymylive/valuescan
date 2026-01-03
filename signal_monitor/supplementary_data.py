#!/usr/bin/env python3
"""
补充数据模块 - 与 ValuScan 数据配合使用
数据来源：
1. 币安 API（资金费率、持仓量、多空比）
2. 免费外部 API（Fear & Greed Index）

数据优先级：ValuScan > 本模块补充数据 > K线数据
"""

import os
import sys
import requests
from typing import Dict, Any, Optional
from datetime import datetime

try:
    from logger import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

# 代理配置
try:
    from config import SOCKS5_PROXY, HTTP_PROXY
except ImportError:
    SOCKS5_PROXY = ""
    HTTP_PROXY = ""


def _get_proxies() -> Optional[Dict[str, str]]:
    """获取代理配置"""
    if os.getenv("VALUESCAN_NO_PROXY", "0") == "1":
        return None
    
    proxy = SOCKS5_PROXY or os.getenv("SOCKS5_PROXY") or os.getenv("HTTP_PROXY")
    if proxy:
        return {"http": proxy, "https": proxy}
    return None


def get_funding_rate(symbol: str) -> Optional[Dict[str, Any]]:
    """
    获取币安永续合约资金费率
    反映多空博弈强度：正费率=多方付费，负费率=空方付费
    """
    try:
        clean_symbol = symbol.upper().replace("$", "").strip()
        if not clean_symbol.endswith("USDT"):
            clean_symbol += "USDT"
        
        url = "https://fapi.binance.com/fapi/v1/fundingRate"
        resp = requests.get(
            url,
            params={"symbol": clean_symbol, "limit": 10},
            timeout=10,
            proxies=_get_proxies()
        )
        
        if resp.status_code == 200:
            data = resp.json()
            if data:
                latest = data[-1]
                rate = float(latest.get("fundingRate", 0))
                return {
                    "symbol": clean_symbol,
                    "funding_rate": rate,
                    "funding_rate_percent": rate * 100,
                    "timestamp": latest.get("fundingTime"),
                    "interpretation": "多方付费" if rate > 0 else "空方付费" if rate < 0 else "平衡",
                    "sentiment": "bullish_crowd" if rate > 0.0005 else "bearish_crowd" if rate < -0.0005 else "neutral"
                }
    except Exception as e:
        logger.debug(f"Failed to get funding rate for {symbol}: {e}")
    return None


def get_open_interest(symbol: str) -> Optional[Dict[str, Any]]:
    """
    获取币安永续合约持仓量
    持仓量增加 = 新资金入场，持仓量减少 = 资金离场
    """
    try:
        clean_symbol = symbol.upper().replace("$", "").strip()
        if not clean_symbol.endswith("USDT"):
            clean_symbol += "USDT"
        
        url = "https://fapi.binance.com/fapi/v1/openInterest"
        resp = requests.get(
            url,
            params={"symbol": clean_symbol},
            timeout=10,
            proxies=_get_proxies()
        )
        
        if resp.status_code == 200:
            data = resp.json()
            oi = float(data.get("openInterest", 0))
            return {
                "symbol": clean_symbol,
                "open_interest": oi,
                "timestamp": data.get("time"),
            }
    except Exception as e:
        logger.debug(f"Failed to get open interest for {symbol}: {e}")
    return None


def get_long_short_ratio(symbol: str) -> Optional[Dict[str, Any]]:
    """
    获取币安多空账户比和多空持仓比
    用于判断散户情绪（通常与大户相反）
    """
    try:
        clean_symbol = symbol.upper().replace("$", "").strip()
        if not clean_symbol.endswith("USDT"):
            clean_symbol += "USDT"
        
        result = {}
        
        # 大户账户多空比
        url = "https://fapi.binance.com/futures/data/topLongShortAccountRatio"
        resp = requests.get(
            url,
            params={"symbol": clean_symbol, "period": "1h", "limit": 1},
            timeout=10,
            proxies=_get_proxies()
        )
        if resp.status_code == 200:
            data = resp.json()
            if data:
                result["top_trader_accounts"] = {
                    "long_ratio": float(data[0].get("longAccount", 0)),
                    "short_ratio": float(data[0].get("shortAccount", 0)),
                    "ratio": float(data[0].get("longShortRatio", 1)),
                }
        
        # 大户持仓多空比
        url = "https://fapi.binance.com/futures/data/topLongShortPositionRatio"
        resp = requests.get(
            url,
            params={"symbol": clean_symbol, "period": "1h", "limit": 1},
            timeout=10,
            proxies=_get_proxies()
        )
        if resp.status_code == 200:
            data = resp.json()
            if data:
                result["top_trader_positions"] = {
                    "long_ratio": float(data[0].get("longPosition", 0)),
                    "short_ratio": float(data[0].get("shortPosition", 0)),
                    "ratio": float(data[0].get("longShortRatio", 1)),
                }
        
        # 全市场多空比
        url = "https://fapi.binance.com/futures/data/globalLongShortAccountRatio"
        resp = requests.get(
            url,
            params={"symbol": clean_symbol, "period": "1h", "limit": 1},
            timeout=10,
            proxies=_get_proxies()
        )
        if resp.status_code == 200:
            data = resp.json()
            if data:
                result["global_accounts"] = {
                    "long_ratio": float(data[0].get("longAccount", 0)),
                    "short_ratio": float(data[0].get("shortAccount", 0)),
                    "ratio": float(data[0].get("longShortRatio", 1)),
                }
        
        if result:
            result["symbol"] = clean_symbol
            return result
            
    except Exception as e:
        logger.debug(f"Failed to get long/short ratio for {symbol}: {e}")
    return None


def get_fear_greed_index() -> Optional[Dict[str, Any]]:
    """
    获取加密货币恐惧与贪婪指数
    0-25: 极度恐惧（买入机会）
    25-50: 恐惧
    50-75: 贪婪
    75-100: 极度贪婪（卖出信号）
    """
    try:
        url = "https://api.alternative.me/fng/"
        resp = requests.get(url, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            if data and data.get("data"):
                fng = data["data"][0]
                value = int(fng.get("value", 50))
                classification = fng.get("value_classification", "Neutral")
                
                return {
                    "value": value,
                    "classification": classification,
                    "timestamp": fng.get("timestamp"),
                    "interpretation": _interpret_fng(value),
                    "trading_signal": _fng_trading_signal(value),
                }
    except Exception as e:
        logger.debug(f"Failed to get Fear & Greed Index: {e}")
    return None


def _interpret_fng(value: int) -> str:
    """解读恐惧贪婪指数"""
    if value <= 25:
        return "极度恐惧 - 市场过度悲观，可能是买入机会"
    elif value <= 40:
        return "恐惧 - 市场情绪偏空，需谨慎"
    elif value <= 60:
        return "中性 - 市场情绪平稳"
    elif value <= 75:
        return "贪婪 - 市场情绪偏多，注意风险"
    else:
        return "极度贪婪 - 市场过度乐观，可能是卖出信号"


def _fng_trading_signal(value: int) -> str:
    """根据恐惧贪婪指数给出交易信号"""
    if value <= 20:
        return "strong_buy"
    elif value <= 35:
        return "buy"
    elif value <= 65:
        return "neutral"
    elif value <= 80:
        return "sell"
    else:
        return "strong_sell"


def get_all_supplementary_data(symbol: str) -> Dict[str, Any]:
    """
    获取所有补充数据
    用于与 ValuScan 数据配合进行 AI 分析
    """
    result = {
        "symbol": symbol,
        "data_source": "binance_api + alternative.me",
        "priority": "SUPPLEMENTARY",  # 补充数据，优先级低于 ValuScan
    }
    
    # 1. 资金费率
    funding = get_funding_rate(symbol)
    if funding:
        result["funding_rate"] = funding
        logger.info(f"[Supplementary] {symbol} 资金费率: {funding['funding_rate_percent']:.4f}%")
    
    # 2. 持仓量
    oi = get_open_interest(symbol)
    if oi:
        result["open_interest"] = oi
        logger.info(f"[Supplementary] {symbol} 持仓量: {oi['open_interest']:,.0f}")
    
    # 3. 多空比
    ls_ratio = get_long_short_ratio(symbol)
    if ls_ratio:
        result["long_short_ratio"] = ls_ratio
    
    # 4. 恐惧贪婪指数（全市场）
    fng = get_fear_greed_index()
    if fng:
        result["fear_greed_index"] = fng
        logger.info(f"[Supplementary] Fear & Greed: {fng['value']} ({fng['classification']})")
    
    return result


if __name__ == "__main__":
    # 测试
    print("=" * 50)
    print("补充数据测试")
    print("=" * 50)
    
    data = get_all_supplementary_data("BTC")
    
    import json
    print(json.dumps(data, indent=2, ensure_ascii=False, default=str))
