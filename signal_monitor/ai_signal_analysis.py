#!/usr/bin/env python3
"""
AI per-signal analysis.
Builds a compact snapshot (key levels, patterns, fund flow) and asks the
configured AI endpoint to produce a short professional read.
优先使用 ValuScan 数据作为主力位和主力成本参考
"""

import json
import os
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

import requests

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
_BULL_BEAR_SIGNAL_TTL_SECONDS = _read_int_env_or_config(
    "VALUESCAN_BULL_BEAR_SIGNAL_TTL_SECONDS",
    "BULL_BEAR_SIGNAL_TTL_SECONDS",
    86400,
)
_BULLISH_SIGNAL_TYPES = {100, 101, 108, 110, 111}
_BEARISH_SIGNAL_TYPES = {102, 103, 109, 112}


def _extract_signal_timestamp_ms(signal_payload: Optional[Dict[str, Any]]) -> int:
    if not isinstance(signal_payload, dict):
        return 0
    for key in ("createTime", "createdTime", "create_time", "timestamp", "time", "ts", "msgTime"):
        value = signal_payload.get(key)
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


def _extract_signal_type(signal_payload: Optional[Dict[str, Any]]) -> int:
    if not isinstance(signal_payload, dict):
        return 0
    for key in ("type", "msgType", "messageType", "signalType", "warnType"):
        value = signal_payload.get(key)
        if value is None:
            continue
        try:
            return int(value)
        except Exception:
            continue
    return 0


def _is_bull_bear_signal_expired(signal_payload: Optional[Dict[str, Any]]) -> bool:
    if _BULL_BEAR_SIGNAL_TTL_SECONDS <= 0:
        return False
    msg_type = _extract_signal_type(signal_payload)
    if msg_type not in _BULLISH_SIGNAL_TYPES and msg_type not in _BEARISH_SIGNAL_TYPES:
        return False
    msg_time_ms = _extract_signal_timestamp_ms(signal_payload)
    if not msg_time_ms:
        return False
    age_seconds = (time.time() * 1000 - msg_time_ms) / 1000.0
    return age_seconds > _BULL_BEAR_SIGNAL_TTL_SECONDS


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

try:
    from .logger import logger
except Exception:
    try:
        from logger import logger
    except Exception:
        from signal_monitor.logger import logger


def get_ai_signal_config():
    """从独立配置文件获取 AI 信号简评配置"""
    import json
    from pathlib import Path
    
    config_path = Path(__file__).parent / "ai_signal_config.json"
    defaults = {
        "enabled": True,
        "api_key": "",
        "api_url": "https://api.openai.com/v1/chat/completions",
        "model": "gpt-4o-mini",
    }
    
    if config_path.exists():
        try:
            file_config = json.loads(config_path.read_text(encoding="utf-8"))
            return {**defaults, **file_config}
        except Exception:
            pass
    return defaults


from chart_pro_v10 import (
    get_klines,
    get_orderbook,
    calculate_atr,
    detect_channel,
    detect_best_flag,
    detect_best_wedge,
    detect_best_triangle,
    PATTERN_SCORE_THRESHOLDS,
)
from ai_key_levels_cache import set_levels
from ai_overlays_cache import set_overlays
from market_data_sources import fetch_market_snapshot


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
    """
    if days is None:
        days = VALUESCAN_AI_ANALYSIS_DAYS
    
    try:
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
            logger.debug(f"ValuScan: No keyword found for {symbol}")
            return None
        
        result = {"symbol": clean_symbol, "days": days, "keyword": keyword}
        
        # 1. 主力位（阻力位）
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
        
        # 2. 主力成本（支撑位）
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
        
        # 5. 机会/风险信号
        try:
            os_data = get_opportunity_signals(1, 10)
            if os_data.get("code") == 200:
                result["opportunity_signals"] = os_data.get("data", {})
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
        logger.debug(f"ValuScan data fetch failed for {symbol}: {e}")
        return None

# ==================== 代理配置 ====================
try:
    from config import SOCKS5_PROXY, HTTP_PROXY
except ImportError:
    SOCKS5_PROXY = ""
    HTTP_PROXY = ""


def _get_binance_proxies():
    """获取 Binance API 请求的代理配置"""
    if os.getenv("VALUESCAN_NO_PROXY", "0") == "1":
        return None

    def _read_env_proxy(names):
        for name in names:
            val = os.getenv(name) or os.getenv(name.lower())
            if val and isinstance(val, str) and val.strip():
                return val.strip()
        return ""

    # 优先使用 SOCKS5 代理（配置文件）
    if SOCKS5_PROXY and isinstance(SOCKS5_PROXY, str) and SOCKS5_PROXY.strip():
        proxy_url = SOCKS5_PROXY.strip()
        return {'http': proxy_url, 'https': proxy_url}

    # 其次使用 HTTP 代理（配置文件）
    if HTTP_PROXY and isinstance(HTTP_PROXY, str) and HTTP_PROXY.strip():
        proxy_url = HTTP_PROXY.strip()
        return {'http': proxy_url, 'https': proxy_url}

    # 环境变量回退
    env_socks = _read_env_proxy(["SOCKS5_PROXY", "ALL_PROXY", "VALUESCAN_SOCKS5_PROXY"])
    if env_socks:
        return {'http': env_socks, 'https': env_socks}

    env_http = _read_env_proxy(["HTTPS_PROXY", "HTTP_PROXY"])
    if env_http:
        return {'http': env_http, 'https': env_http}

    return None


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


def _safe_symbol(symbol: str) -> str:
    return symbol.upper().replace("$", "").replace("USDT", "").strip()


def seed_valuescan_key_levels(symbol: str, days: Optional[int] = None) -> bool:
    valuescan_data = get_valuescan_data(symbol, days)
    if not valuescan_data:
        return False

    supports = []
    resistances = []

    main_force = valuescan_data.get("current_main_force")
    if isinstance(main_force, (int, float)) and main_force > 0:
        resistances.append(float(main_force))

    for level in valuescan_data.get("main_force_levels", []) or []:
        try:
            price = float(level)
        except Exception:
            continue
        if price > 0:
            resistances.append(price)

    main_cost = valuescan_data.get("main_cost")
    if isinstance(main_cost, (int, float)) and main_cost > 0:
        supports.append(float(main_cost))

    if not supports and not resistances:
        return False

    set_levels(
        _safe_symbol(symbol),
        supports,
        resistances,
        meta={"source": "valuescan", "days": valuescan_data.get("days", days)},
    )
    return True


def _fetch_taker_flow(symbol: str) -> Dict[str, Dict[str, float]]:
    """Fetch taker buy/sell ratio from Binance with proxy support"""
    base = _safe_symbol(symbol)
    sym = f"{base}USDT"
    periods = ["15m", "1h", "4h", "1d"]
    result: Dict[str, Dict[str, float]] = {}
    proxies = _get_binance_proxies()
    
    for period in periods:
        try:
            url = "https://fapi.binance.com/futures/data/takerlongshortRatio"
            resp = requests.get(
                url, 
                params={"symbol": sym, "period": period, "limit": 1}, 
                timeout=15,
                proxies=proxies
            )
            if resp.status_code != 200:
                # 代理失败时尝试直连
                if proxies:
                    try:
                        resp = requests.get(
                            url,
                            params={"symbol": sym, "period": period, "limit": 1},
                            timeout=15
                        )
                        if resp.status_code != 200:
                            continue
                    except:
                        continue
                else:
                    continue
            data = resp.json()
            if not isinstance(data, list) or not data:
                continue
            row = data[-1]
            buy_vol = float(row.get("buyVol", 0) or 0)
            sell_vol = float(row.get("sellVol", 0) or 0)
            total = buy_vol + sell_vol
            ratio = buy_vol / total if total > 0 else 0.5
            result[period] = {
                "buy_vol": buy_vol,
                "sell_vol": sell_vol,
                "net": buy_vol - sell_vol,
                "ratio": ratio,
            }
        except Exception as e:
            logger.debug(f"[AI Signal] _fetch_taker_flow {period} failed: {e}")
            continue
    return result


def _build_snapshot(
    symbol: str,
    interval: str = "1h",
    limit: int = 200,
) -> Optional[Dict[str, Any]]:
    """构建市场快照数据用于AI分析"""
    logger.debug(f"[AI Signal] 构建快照: {symbol} ({interval}, {limit})")
    
    df = get_klines(symbol, timeframe=interval, limit=limit)
    if df is None or df.empty:
        logger.warning(f"[AI Signal] 无法获取K线数据: {symbol} - df={'None' if df is None else 'empty'}")
        return None
    
    logger.debug(f"[AI Signal] K线数据获取成功: {symbol} ({len(df)} 条)")

    current_price = float(df["close"].iloc[-1])
    orderbook = get_orderbook(symbol, limit=100)

    klines = []
    if "timestamp" in df.columns:
        ts_ms = (df["timestamp"].astype("int64") // 10**6).astype("int64")
        for i, row in df.reset_index(drop=True).iterrows():
            klines.append(
                {
                    "ts": int(ts_ms.iloc[i]),
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": float(row["volume"]),
                }
            )

    orderbook_summary = {}
    if isinstance(orderbook, dict):
        bids = orderbook.get("bids") or []
        asks = orderbook.get("asks") or []
        orderbook_summary = {
            "bids": [
                {"price": float(p), "amount": float(a), "notional": float(p) * float(a)}
                for p, a in bids[:20]
            ],
            "asks": [
                {"price": float(p), "amount": float(a), "notional": float(p) * float(a)}
                for p, a in asks[:20]
            ],
        }

    atr = calculate_atr(df)
    channel = detect_channel(df, atr=atr, windows=(60, 80, 120), r2_min=0.55)
    flag = detect_best_flag(df, atr, impulse_lookback=20, windows=(12, 18, 24))
    wedge = detect_best_wedge(df, atr=atr, windows=(60, 80, 120), r2_min=0.5)
    triangle = detect_best_triangle(df, atr=atr, windows=(60, 80, 120), r2_min=0.5)

    market_snapshot = fetch_market_snapshot(symbol) or {}
    valuescan_data = get_valuescan_data(symbol)
    valuescan_flow = valuescan_data.get("exchange_flow_detail") if valuescan_data else {}
    taker_flow = _fetch_taker_flow(symbol) if not valuescan_flow else {}
    fund_flow = valuescan_flow or taker_flow or {}

    lows = [k.get("low") for k in klines if isinstance(k.get("low"), (int, float))]
    highs = [k.get("high") for k in klines if isinstance(k.get("high"), (int, float))]
    price_min = min(lows) if lows else None
    price_max = max(highs) if highs else None

    overlay_candidates = _build_overlay_candidates(
        {
            "channel": channel,
            "flag": flag,
            "wedge": wedge,
            "triangle": triangle,
        },
        len(klines),
    )

    snapshot = {
        "symbol": _safe_symbol(symbol),
        "interval": interval,
        "current_price": current_price,
        "klines": klines,
        "price_min": price_min,
        "price_max": price_max,
        "orderbook": orderbook_summary,
        "patterns": {
            "channel": channel,
            "flag": flag,
            "wedge": wedge,
            "triangle": triangle,
        },
        "fund_flow": fund_flow,
        "market": market_snapshot,
        "overlay_candidates": overlay_candidates,
    }
    
    # 添加 ValuScan 数据（优先级最高的参考数据）
    # AI 简评使用 14 天数据
    if valuescan_data:
        snapshot["valuescan"] = {
            "main_force_level": valuescan_data.get("current_main_force"),  # 主力位（阻力位）
            "main_force_levels": valuescan_data.get("main_force_levels", []),
            "main_cost": valuescan_data.get("main_cost"),  # 主力成本（支撑位）
            "trade_inflow": valuescan_data.get("trade_inflow"),
            "detailed_inflow": valuescan_data.get("detailed_inflow"),
            "token_flow": valuescan_data.get("token_flow"),  # 代币资金流向
            "whale_flow": valuescan_data.get("whale_flow"),  # 巨鲸资金流向
            "opportunity_signals": valuescan_data.get("opportunity_signals"),
            "risk_signals": valuescan_data.get("risk_signals"),
            "exchange_flow_detail": valuescan_data.get("exchange_flow_detail"),
            "fund_flow_history": valuescan_data.get("fund_flow_history"),
            "fund_volume_history": valuescan_data.get("fund_volume_history"),
            "holders_top": valuescan_data.get("holders_top"),
            "chains": valuescan_data.get("chains"),
            "data_days": valuescan_data.get("days", 14),
            "priority": "HIGHEST",
            "note": "主力位作为阻力位参考，主力成本作为强支撑位参考"
        }
    
    # 获取补充数据（资金费率、持仓量、多空比、恐惧贪婪指数）
    supplementary_data = get_supplementary_data(symbol)
    if supplementary_data:
        snapshot["derivatives"] = {
            "funding_rate": supplementary_data.get("funding_rate"),
            "open_interest": supplementary_data.get("open_interest"),
            "long_short_ratio": supplementary_data.get("long_short_ratio"),
            "fear_greed_index": supplementary_data.get("fear_greed_index"),
        }
    
    # 数据来源说明
    snapshot["data_sources"] = {
        "primary": "ValuScan (主力位、主力成本、资金流、信号)",
        "derivatives": "Binance Futures (资金费率、持仓量、多空比) + Fear & Greed",
        "supplementary": "Binance K线/订单簿 (价格走势和技术指标)",
        "integration": "ValuScan主力数据 + 衍生品情绪 + 价格走势 = 综合分析"
    }
    
    return snapshot


def _format_patterns(patterns: Dict[str, Any]) -> List[Dict[str, Any]]:
    out = []
    if not isinstance(patterns, dict):
        return out

    for key, value in patterns.items():
        if not value or not isinstance(value, dict):
            continue
        score = float(value.get("score", 0))
        threshold = PATTERN_SCORE_THRESHOLDS.get(key, 0.6)
        if score < threshold:
            continue
        out.append(
            {
                "name": key,
                "type": value.get("type"),
                "score": round(score, 2),
                "window": value.get("window"),
            }
        )
    return out


def _build_overlay_candidates(patterns: Dict[str, Any], klines_len: int) -> List[Dict[str, Any]]:
    candidates: List[Dict[str, Any]] = []
    if not isinstance(patterns, dict) or klines_len < 20:
        return candidates

    style_map = {
        "channel": "solid",
        "flag": "dashed",
        "wedge": "dashdot",
        "triangle": "dot",
    }

    for key in ("channel", "flag", "wedge", "triangle"):
        pattern = patterns.get(key)
        if not isinstance(pattern, dict):
            continue
        score = float(pattern.get("score", 0))
        threshold = PATTERN_SCORE_THRESHOLDS.get(key, 0.6)
        if score < threshold:
            continue
        window = int(pattern.get("window") or 0)
        if window < 20 or window > klines_len:
            continue
        upper = pattern.get("upper")
        lower = pattern.get("lower")
        if not (isinstance(upper, (list, tuple)) and isinstance(lower, (list, tuple))):
            continue
        if len(upper) < 2 or len(lower) < 2:
            continue
        slope_u, intercept_u = float(upper[0]), float(upper[1])
        slope_l, intercept_l = float(lower[0]), float(lower[1])
        x_start = klines_len - window
        x1 = x_start
        x2 = x_start + window - 1
        y1_u = slope_u * 0 + intercept_u
        y2_u = slope_u * (window - 1) + intercept_u
        y1_l = slope_l * 0 + intercept_l
        y2_l = slope_l * (window - 1) + intercept_l
        style = style_map.get(key, "solid")
        candidates.append(
            {
                "id": f"{key}_top",
                "x1": x1,
                "y1": y1_u,
                "x2": x2,
                "y2": y2_u,
                "style": style,
                "label": f"{key}_top",
                "type": key,
            }
        )
        candidates.append(
            {
                "id": f"{key}_bottom",
                "x1": x1,
                "y1": y1_l,
                "x2": x2,
                "y2": y2_l,
                "style": style,
                "label": f"{key}_bottom",
                "type": key,
            }
        )

    return candidates


def _format_fund_flow(fund_flow: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(fund_flow, dict):
        return {}
    result = {}
    for period in ("15m", "1h", "4h", "12h", "24h", "1d"):
        data = fund_flow.get(period)
        if not isinstance(data, dict):
            continue
        result[period] = {
            "net": data.get("net"),
            "ratio": data.get("ratio"),
        }
    return result






def _build_prompt(
    symbol: str,
    snapshot: Dict[str, Any],
    signal_payload: Optional[Dict[str, Any]] = None,
    language: str = "zh",
) -> str:
    patterns = _format_patterns(snapshot.get("patterns", {}))
    fund_flow = _format_fund_flow(snapshot.get("fund_flow", {}))

    signal_info = {}
    if isinstance(signal_payload, dict):
        item = signal_payload.get("item") or {}
        content = signal_payload.get("parsed_content") or {}
        signal_info = {
            "title": item.get("title"),
            "type": item.get("type") or item.get("messageType"),
            "source": content.get("source"),
            "tradeType": content.get("tradeType"),
            "fundsMovementType": content.get("fundsMovementType"),
        }

    payload = {
        "symbol": symbol,
        "price": snapshot.get("current_price"),
        "klines": snapshot.get("klines", []),
        "orderbook": snapshot.get("orderbook", {}),
        "patterns": patterns,
        "fund_flow": fund_flow,
        "market": snapshot.get("market", {}),
        "signal": signal_info,
    }
    if "valuescan" in snapshot:
        payload["valuescan"] = snapshot.get("valuescan")
    if "derivatives" in snapshot:
        payload["derivatives"] = snapshot.get("derivatives")
    if "data_sources" in snapshot:
        payload["data_sources"] = snapshot.get("data_sources")

    payload_json = json.dumps(payload, ensure_ascii=False)

    if language == "en":
        return f"""You are a senior quantitative analyst. Make a strict entry decision after a rigorous review.
Return ONLY strict JSON, no extra text.
JSON format:
{{"analysis":"...","supports":[...],"resistances":[...],"stop_loss":null,"take_profit":null,"rr":null,"risk_level":"low/medium/high","entry_decision":"yes/no","direction":"long/short/none","overlays":[]}}
Requirements:
1) analysis: concise, ~90-110 words.
2) analysis must explicitly reference ALL data sources: klines/trend, orderbook liquidity, flow data, patterns, market snapshot (volume/market cap), and signal context.
2.1) If valuescan data exists, treat it as the highest-priority source (main_force_level/main_cost) and only use Binance/market data as supplementary context.
3) You must evaluate BOTH long and short scenarios and pick the stronger one. If bearish evidence is consistent, set entry_decision="yes" with direction="short" (do not default to long).
4) entry_decision: "yes" only if at least 4 of 6 data sources align directionally AND risk is acceptable; if data is insufficient or conflicting, choose "no".
5) If entry_decision is "no", do NOT provide stop-loss/take-profit in analysis and keep stop_loss/take_profit/rr as null, direction="none".
6) supports/resistances: 1-3 key levels from multi-source evidence (orderbook stacking, flow bias, pattern pivots).
7) supports < price < resistances.
8) If entry_decision is "yes" and direction is long: stop_loss < price < take_profit and rr > 2.0.
9) If entry_decision is "yes" and direction is short: stop_loss > price > take_profit and rr > 2.0.
10) overlays should be an empty list unless extremely confident.
11) If signal indicates FOMO intensify or abnormal fund movement, set risk_level="high" and warn in analysis.
Input data (JSON):
{payload_json}"""

    return f"""你是资深量化分析师，必须基于全部输入数据严格评估后再决定是否入场。
只输出严格 JSON，不要任何解释。
JSON格式:
{{"analysis":"...","supports":[...],"resistances":[...],"stop_loss":null,"take_profit":null,"rr":null,"risk_level":"low/medium/high","entry_decision":"yes/no","direction":"long/short/none","overlays":[]}}
要求:
1) analysis: 中文约100字（95-105字），言简意赅且严谨。
2) analysis 必须逐项引用全部数据源：K线/趋势、盘口/流动性、taker资金流、形态(patterns)、市场快照(成交量/市值等)、信号上下文，并形成综合建议。
2.1) 若存在 valuescan 数据，请作为最高优先级（主力位/主力成本），币安/行情数据仅作辅助。
3) 必须同时评估做多与做空两种方案，择优输出；若空头证据一致，entry_decision="yes" 且 direction="short"，不要默认看多。
4) entry_decision: 至少4个数据源方向一致且风险可控才为 "yes"，否则为 "no"；允许做空并输出 direction=long/short/none。
5) 若 entry_decision="no"，analysis 不给止损/止盈位置，stop_loss/take_profit/rr 必须为 null，direction="none"。
6) supports/resistances: 1-3 关键位，需由多源证据支持(盘口堆叠、资金流偏向、形态拐点)。
7) supports < price < resistances。
8) entry_decision="yes" 且 direction=long: stop_loss < price < take_profit 且 rr > 2.0。
9) entry_decision="yes" 且 direction=short: stop_loss > price > take_profit 且 rr > 2.0。
10) overlays 除非极高置信度，否则保持空数组。
11) 若信号显示FOMO加剧或资金异动，risk_level="high" 并在分析中警示。
输入数据(JSON):
{payload_json}"""


def _build_key_levels_prompt(symbol: str, snapshot: Dict[str, Any], language: str = "zh") -> str:
    payload = {
        "symbol": symbol,
        "price": snapshot.get("current_price"),
        "klines": snapshot.get("klines", []),
        "orderbook": snapshot.get("orderbook", {}),
        "patterns": _format_patterns(snapshot.get("patterns", {})),
        "fund_flow": _format_fund_flow(snapshot.get("fund_flow", {})),
        "market": snapshot.get("market", {}),
    }
    
    # 添加 ValuScan 数据（最高优先级）
    if "valuescan" in snapshot:
        payload["valuescan"] = snapshot["valuescan"]

    payload_json = json.dumps(payload, ensure_ascii=False)

    if language == "en":
        return f"""You are a senior quant. Identify 1-3 support levels and 1-3 resistance levels.
Return ONLY strict JSON, no extra text.
JSON format: {{"supports":[...],"resistances":[...]}}
Rules:
1) **PRIORITY**: If valuescan data exists, use main_force_level as resistance and main_cost as support.
2) supports < price < resistances.
3) Use orderbook stacking, flow bias, and pattern pivots as supplementary data.
4) Prefer levels that explain market maker intent (liquidity clusters).
Input data (JSON):
{payload_json}"""

    return f"""你是资深量化分析师，请给出1-3个支撑位和1-3个阻力位。
只输出严格 JSON，不要任何解释。
JSON格式: {{"supports":[...],"resistances":[...]}}
规则:
1) **最高优先级**: 如果存在 valuescan 数据，请优先使用 main_force_level 作为阻力位，main_cost 作为支撑位。
2) supports < price < resistances。
3) 盘口堆叠、taker资金流偏向、形态拐点作为补充数据。
4) 优先能解释主力意图的流动性簇。
输入数据(JSON):
{payload_json}"""
def _strip_thoughts(text: str) -> str:
    """Return only the final answer when the model includes thought markers."""
    if not text:
        return text
    cleaned = text.strip()
    markers = [
        "</think>",
        "思考:",
        "最终答案:",
        "最终:",
        "结论:",
        "答案:",
        "Final Answer:",
        "Final:",
        "Answer:",
    ]
    for marker in markers:
        if marker in cleaned:
            cleaned = cleaned.split(marker, 1)[-1].strip()
    if "<think>" in cleaned:
        cleaned = cleaned.split("<think>", 1)[0].strip()
    return cleaned


def _sanitize_no_entry_analysis(analysis: str, language: str) -> str:
    if not analysis:
        return analysis
    if language == "en":
        for token in ("stop loss", "stop-loss", "take profit", "take-profit"):
            analysis = analysis.replace(token, "risk control")
            analysis = analysis.replace(token.title(), "risk control")
    else:
        analysis = analysis.replace("止盈", "风险控制").replace("止损", "风险控制")
    return analysis


def _ensure_no_entry_hint(analysis: str, language: str) -> str:
    if not analysis:
        return analysis
    if language == "en":
        lowered = analysis.lower()
        if "wait" not in lowered and "stand aside" not in lowered:
            analysis = f"{analysis} Stand aside."
    else:
        if "观望" not in analysis and "不入场" not in analysis:
            analysis = f"{analysis} 建议观望。"
    return analysis


def _clamp_analysis_length(analysis: str, language: str) -> str:
    if not analysis:
        return analysis
    if language == "zh":
        max_len = 110
        if len(analysis) > max_len:
            analysis = analysis[:max_len].rstrip("，。；;,. ")
        return analysis
    words = analysis.split()
    if len(words) > 120:
        analysis = " ".join(words[:120])
    return analysis

def _parse_ai_response(raw: str) -> Dict[str, Any]:
    if not raw:
        return {
            "analysis": "",
            "supports": [],
            "resistances": [],
            "risk_level": "medium",
            "entry_decision": "no",
            "direction": "none",
        }
    cleaned = raw.strip()
    data = None
    try:
        data = json.loads(cleaned)
    except Exception:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                data = json.loads(cleaned[start:end + 1])
            except Exception:
                data = None
    if not isinstance(data, dict):
        return {
            "analysis": cleaned,
            "supports": [],
            "resistances": [],
            "risk_level": "medium",
            "entry_decision": "no",
            "direction": "none",
        }
    return data


def _normalize_entry_decision(value: Any) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (int, float)):
        return "yes" if value > 0 else "no"
    if isinstance(value, str):
        val = value.strip().lower()
        if val in {"yes", "y", "true", "1", "是", "入场", "进场", "开仓", "做多", "做空", "多", "空"}:
            return "yes"
        if val in {"no", "n", "false", "0", "否", "不入场", "观望", "空仓"}:
            return "no"
    return "no"


def _normalize_risk_level(value: Any) -> str:
    if isinstance(value, str):
        val = value.strip().lower()
        mapping = {
            "low": "low",
            "medium": "medium",
            "high": "high",
            "l": "low",
            "m": "medium",
            "h": "high",
            "低": "low",
            "中": "medium",
            "高": "high",
        }
        if val in mapping:
            return mapping[val]
    return "medium"


def _normalize_direction(value: Any) -> str:
    if isinstance(value, str):
        val = value.strip().lower()
        if val in {"long", "bull", "bullish", "up", "多", "看多", "做多", "多头", "买入"}:
            return "long"
        if val in {"short", "bear", "bearish", "down", "空", "看空", "做空", "空头", "卖出"}:
            return "short"
        if val in {"none", "neutral", "sideways", "无", "观望", "不入场", "空仓", "中性"}:
            return "none"
    return "none"


def _infer_direction_from_levels(price: float, stop_loss: Optional[float], take_profit: Optional[float]) -> str:
    if stop_loss is None or take_profit is None:
        return "none"
    if stop_loss < price < take_profit:
        return "long"
    if stop_loss > price > take_profit:
        return "short"
    return "none"


def _normalize_levels(values: Any, price: float, is_support: bool) -> List[float]:
    if not isinstance(values, list):
        return []
    out = []
    for item in values:
        val = None
        if isinstance(item, (int, float)):
            val = float(item)
        elif isinstance(item, dict):
            if isinstance(item.get("price"), (int, float)):
                val = float(item["price"])
        if val is None:
            continue
        if is_support and val >= price:
            continue
        if not is_support and val <= price:
            continue
        out.append(val)
    return out[:3]


def _merge_valuescan_levels(
    valuescan_data: Optional[Dict[str, Any]],
    supports: List[float],
    resistances: List[float],
    price: float,
) -> Tuple[List[float], List[float], str]:
    if not valuescan_data or not isinstance(valuescan_data, dict):
        return supports[:3], resistances[:3], "ai"

    vs_supports: List[float] = []
    vs_resistances: List[float] = []
    raw_levels = valuescan_data.get("main_force_levels") or []
    for level in raw_levels:
        try:
            val = float(level)
        except Exception:
            continue
        if val > 0:
            vs_resistances.append(val)

    vs_main_force = valuescan_data.get("main_force_level") or valuescan_data.get("current_main_force")
    if isinstance(vs_main_force, (int, float)) and vs_main_force > 0:
        vs_resistances.append(float(vs_main_force))

    vs_main_cost = valuescan_data.get("main_cost")
    if isinstance(vs_main_cost, (int, float)) and vs_main_cost > 0:
        vs_supports.append(float(vs_main_cost))

    if price:
        vs_supports = [s for s in vs_supports if s < price]
        vs_resistances = [r for r in vs_resistances if r > price]

    if vs_supports or vs_resistances:
        return vs_supports[:3], vs_resistances[:3], "valuescan"
    return supports[:3], resistances[:3], "ai"


def _normalize_price_value(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, dict):
        val = value.get("price")
        if isinstance(val, (int, float)):
            return float(val)
    return None


def _extract_trade_levels(
    parsed: Dict[str, Any],
    price: float,
    supports: List[float],
    resistances: List[float],
    entry_decision: str,
    direction: str,
):
    if entry_decision != "yes" or direction == "none":
        return None, None, None

    stop_loss = _normalize_price_value(parsed.get("stop_loss"))
    take_profit = _normalize_price_value(parsed.get("take_profit"))

    if direction == "long":
        if stop_loss is None and supports:
            stop_loss = min(supports)
        if take_profit is None and resistances:
            take_profit = max(resistances)
        if stop_loss is not None and stop_loss >= price:
            stop_loss = None
        if take_profit is not None and take_profit <= price:
            take_profit = None
    elif direction == "short":
        if stop_loss is None and resistances:
            stop_loss = max(resistances)
        if take_profit is None and supports:
            take_profit = min(supports)
        if stop_loss is not None and stop_loss <= price:
            stop_loss = None
        if take_profit is not None and take_profit >= price:
            take_profit = None
    else:
        return None, None, None

    rr_val = parsed.get("rr")
    rr = None
    if isinstance(rr_val, (int, float)) and rr_val > 0:
        rr = float(rr_val)
    elif stop_loss is not None and take_profit is not None:
        if direction == "long" and price > stop_loss:
            rr = (take_profit - price) / (price - stop_loss)
        elif direction == "short" and stop_loss > price:
            rr = (price - take_profit) / (stop_loss - price)
    if stop_loss is None or take_profit is None:
        rr = None
    return stop_loss, take_profit, rr


def _is_fomo_intensify(signal_payload: Optional[Dict[str, Any]]) -> bool:
    if not isinstance(signal_payload, dict):
        return False
    item = signal_payload.get("item") or {}
    content = signal_payload.get("parsed_content") or {}
    text = " ".join(
        str(val)
        for val in [
            item.get("title"),
            content.get("source"),
            content.get("titleSimplified"),
            content.get("title"),
        ]
        if val
    ).lower()
    tokens = ["\u52a0\u5267", "\u5f3a\u5316", "\u7206\u53d1", "intensify", "intensified", "spike", "surge"]
    if "fomo" in text and any(token in text for token in tokens):
        return True
    if item.get("type") in (112,):
        return True
    if content.get("fundsMovementType") == 7:
        return True
    return text.count("fomo") >= 2


def _line_touches(series: List[float], line: Dict[str, Any], tolerance: float = 0.015) -> int:
    x1 = int(round(line["x1"]))
    x2 = int(round(line["x2"]))
    if x2 == x1:
        return 0
    if x1 > x2:
        x1, x2 = x2, x1
    x1 = max(0, x1)
    x2 = min(len(series) - 1, x2)
    if x2 <= x1:
        return 0
    slope = (line["y2"] - line["y1"]) / (line["x2"] - line["x1"])
    intercept = line["y1"] - slope * line["x1"]
    touches = 0
    for idx in range(x1, x2 + 1):
        y_line = slope * idx + intercept
        if y_line == 0:
            continue
        if abs(series[idx] - y_line) / y_line <= tolerance:
            touches += 1
    return touches


def _normalize_overlays(
    values: Any,
    max_x: int,
    price_min: Optional[float],
    price_max: Optional[float],
    lows: List[float],
    highs: List[float],
    candidates: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    if not isinstance(values, list):
        return []
    out = []
    candidate_list = candidates if isinstance(candidates, list) else []
    price_range = None
    if isinstance(price_min, (int, float)) and isinstance(price_max, (int, float)):
        price_range = max(1e-9, price_max - price_min)
    for item in values:
        if not isinstance(item, dict):
            continue
        x1 = item.get("x1")
        y1 = item.get("y1")
        x2 = item.get("x2")
        y2 = item.get("y2")
        if not all(isinstance(v, (int, float)) for v in (x1, y1, x2, y2)):
            continue
        x1 = max(0, min(float(x1), max_x))
        x2 = max(0, min(float(x2), max_x))
        if abs(x2 - x1) < 20:
            continue
        if isinstance(price_min, (int, float)) and isinstance(price_max, (int, float)):
            lower = price_min * 0.95
            upper = price_max * 1.05
            if not (lower <= float(y1) <= upper and lower <= float(y2) <= upper):
                continue
        overlay = {
            "x1": x1,
            "y1": float(y1),
            "x2": x2,
            "y2": float(y2),
            "style": item.get("style", "solid"),
            "label": item.get("label", ""),
            "type": item.get("type", ""),
            "color": item.get("color", ""),
        }

        if candidate_list:
            best = None
            best_dist = None
            for cand in candidate_list:
                if not isinstance(cand, dict):
                    continue
                try:
                    dx = abs(float(cand.get("x1", 0)) - float(overlay["x1"])) + abs(float(cand.get("x2", 0)) - float(overlay["x2"]))
                    dy = abs(float(cand.get("y1", 0)) - float(overlay["y1"])) + abs(float(cand.get("y2", 0)) - float(overlay["y2"]))
                except Exception:
                    continue
                dist = dx + (dy / (price_range or 1.0))
                if best_dist is None or dist < best_dist:
                    best_dist = dist
                    best = cand
            if not best:
                continue
            x_tol = 2.5
            y_tol = (price_range or 1.0) * 0.03
            if (
                abs(float(best.get("x1", 0)) - float(overlay["x1"])) > x_tol
                or abs(float(best.get("x2", 0)) - float(overlay["x2"])) > x_tol
                or abs(float(best.get("y1", 0)) - float(overlay["y1"])) > y_tol
                or abs(float(best.get("y2", 0)) - float(overlay["y2"])) > y_tol
            ):
                continue
            overlay.update(
                {
                    "x1": float(best.get("x1", overlay["x1"])),
                    "y1": float(best.get("y1", overlay["y1"])),
                    "x2": float(best.get("x2", overlay["x2"])),
                    "y2": float(best.get("y2", overlay["y2"])),
                    "style": best.get("style", overlay["style"]),
                    "label": best.get("label", overlay["label"]),
                    "type": best.get("type", overlay["type"]),
                }
            )
        out.append(overlay)
    if not out:
        return []

    # Validate channel parallelism if both rails exist.
    channel_lines = [o for o in out if "channel" in str(o.get("label", "")).lower() or o.get("type") == "channel"]
    if len(channel_lines) >= 2:
        top = None
        bottom = None
        for item in channel_lines:
            label = str(item.get("label", "")).lower()
            if "top" in label and top is None:
                top = item
            elif "bottom" in label and bottom is None:
                bottom = item
        if top and bottom:
            dx = float(top["x2"]) - float(top["x1"])
            dx2 = float(bottom["x2"]) - float(bottom["x1"])
            if dx != 0 and dx2 != 0:
                slope_top = (float(top["y2"]) - float(top["y1"])) / dx
                slope_bottom = (float(bottom["y2"]) - float(bottom["y1"])) / dx2
                diff = abs(slope_top - slope_bottom)
                tol = max(0.05, abs(slope_top) * 0.2)
                if diff > tol:
                    out = [o for o in out if o not in (top, bottom)]
            # Require pivot touches for channel rails.
            if highs and lows and top and bottom:
                top_hits = _line_touches(highs, top, tolerance=0.02)
                bottom_hits = _line_touches(lows, bottom, tolerance=0.02)
                if top_hits < 2 or bottom_hits < 2:
                    out = [o for o in out if o not in (top, bottom)]

    return out[:6]


def _call_ai_api(prompt: str, config: Dict[str, Any], language: str = "zh") -> Optional[str]:
    api_key = (config.get("api_key") or "").strip()
    api_url = (config.get("api_url") or "").strip()
    model = (config.get("model") or "").strip()

    if not api_key or not api_url or not model:
        return None

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    system_prompt = (
        "You are a professional quantitative analyst. Reply with strict JSON only."
        if language == "en"
        else "你是专业的量化分析师，只能输出严格 JSON。"
    )

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 8000,
        "temperature": 0.4,
    }

    try:
        # 显式禁用代理直接连接 AI API
        session = requests.Session()
        session.trust_env = False
        resp = session.post(api_url, headers=headers, json=payload, timeout=120)
        if resp.status_code != 200:
            logger.warning("AI API call failed: %s - %s", resp.status_code, resp.text[:200])
            return None
        data = resp.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        if not content:
            return None
        return _strip_thoughts(content)
    except Exception as exc:
        logger.warning("AI API call error: %s", exc)
        return None


def generate_ai_key_levels(symbol: str) -> Optional[Dict[str, Any]]:
    """Generate AI key levels and populate the in-memory cache."""
    logger.info("[AI Key Levels] Start for %s", symbol)

    try:
        from ai_key_levels_config import get_ai_levels_config
    except Exception:
        from signal_monitor.ai_key_levels_config import get_ai_levels_config

    config = get_ai_levels_config()
    logger.info(
        "[AI Key Levels] Config: enabled=%s, has_api_key=%s",
        config.get("enabled"),
        bool(config.get("api_key")),
    )

    if not config.get("enabled", True):
        logger.info("[AI Key Levels] Disabled, skipping.")
        return None
    if not config.get("api_key"):
        logger.warning("[AI Key Levels] Missing API key, skipping.")
        return None

    snapshot = _build_snapshot(symbol)
    if not snapshot:
        logger.warning("[AI Key Levels] Snapshot unavailable for %s", symbol)
        return None

    language = _get_language()
    prompt = _build_key_levels_prompt(_safe_symbol(symbol), snapshot, language=language)
    logger.info("[AI Key Levels] Calling AI API for %s", symbol)
    raw = _call_ai_api(prompt, config, language=language)
    if not raw:
        logger.warning("[AI Key Levels] AI API returned empty response.")
        return None
    logger.info("[AI Key Levels] AI API response received (%s chars)", len(raw))

    parsed = _parse_ai_response(raw)
    price = float(snapshot.get("current_price", 0) or 0)
    supports = _normalize_levels(parsed.get("supports"), price, True)
    resistances = _normalize_levels(parsed.get("resistances"), price, False)
    valuescan_data = snapshot.get("valuescan")
    supports, resistances, key_level_source = _merge_valuescan_levels(
        valuescan_data, supports, resistances, price
    )
    logger.info(
        "[AI Key Levels] Parsed levels: supports=%s, resistances=%s",
        len(supports),
        len(resistances),
    )

    if supports or resistances:
        safe_symbol = _safe_symbol(symbol)
        set_levels(safe_symbol, supports, resistances, meta={"source": key_level_source})
        logger.info(
            "[AI Key Levels] Cached: %s supports, %s resistances",
            len(supports),
            len(resistances),
        )
    else:
        logger.warning("[AI Key Levels] No valid levels parsed.")

    return {"supports": supports, "resistances": resistances}


def analyze_signal(symbol: str, signal_payload: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """AI 信号简评分析"""
    logger.info(f"[AI Signal] 开始分析 {symbol}...")

    if _is_bull_bear_signal_expired(signal_payload):
        logger.info("[AI Signal] Skip expired bull/bear signal: %s", symbol)
        return None
    
    # AI简评使用 ai_signal_config.json 配置
    config = get_ai_signal_config()
    logger.info(f"[AI Signal] 配置: enabled={config.get('enabled')}, has_api_key={bool(config.get('api_key'))}")
    logger.info(
        "[AI Signal] Using model=%s url=%s",
        config.get("model"),
        config.get("api_url"),
    )
    
    if not config.get("enabled", True):
        logger.info(f"[AI Signal] 模块已禁用，跳过分析")
        return None
    
    if not config.get("api_key"):
        logger.warning(f"[AI Signal] 缺少 API Key，跳过分析")
        return None

    snapshot = _build_snapshot(symbol)
    if not snapshot:
        logger.warning(f"[AI Signal] 无法构建 {symbol} 快照数据")
        return None
    language = _get_language()
    prompt = _build_prompt(
        _safe_symbol(symbol),
        snapshot,
        signal_payload=signal_payload,
        language=language,
    )
    logger.info(f"[AI Signal] 调用 AI API 分析 {symbol}...")
    raw = _call_ai_api(prompt, config, language=language)
    if not raw:
        logger.warning(f"[AI Signal] AI API 未返回结果")
        return None

    logger.info(f"[AI Signal] AI API 返回成功，解析结果...")
    parsed = _parse_ai_response(raw)
    analysis = (parsed.get("analysis") or "").strip()
    price = float(snapshot.get("current_price", 0) or 0)
    entry_decision = _normalize_entry_decision(parsed.get("entry_decision"))
    risk_level = _normalize_risk_level(parsed.get("risk_level"))
    direction = _normalize_direction(parsed.get("direction"))
    raw_stop_loss = _normalize_price_value(parsed.get("stop_loss"))
    raw_take_profit = _normalize_price_value(parsed.get("take_profit"))
    if entry_decision == "yes" and direction == "none":
        direction = _infer_direction_from_levels(price, raw_stop_loss, raw_take_profit)
    if entry_decision != "yes":
        direction = "none"

    is_fomo_intensify = _is_fomo_intensify(signal_payload)
    if analysis and entry_decision == "yes" and not is_fomo_intensify:
        if "止盈" in analysis or "take profit" in analysis.lower():
            analysis = analysis.replace("及时止盈", "注意风险").replace("止盈", "注意风险")
    if analysis and entry_decision == "yes" and is_fomo_intensify:
        if "止盈" not in analysis and "take profit" not in analysis.lower():
            if _get_language() == "en":
                analysis = f"{analysis} Risk spikes; take profit in time."
            else:
                analysis = f"{analysis} 风险加剧，注意及时止盈。"
    supports = _normalize_levels(parsed.get("supports"), price, True)
    resistances = _normalize_levels(parsed.get("resistances"), price, False)
    valuescan_data = snapshot.get("valuescan")
    supports, resistances, key_level_source = _merge_valuescan_levels(
        valuescan_data, supports, resistances, price
    )

    stop_loss, take_profit, rr = _extract_trade_levels(
        parsed,
        price,
        supports,
        resistances,
        entry_decision,
        direction,
    )
    overlays = _normalize_overlays(
        parsed.get("overlays"),
        max(0, len(snapshot.get("klines", [])) - 1),
        snapshot.get("price_min"),
        snapshot.get("price_max"),
        [k.get("low") for k in snapshot.get("klines", []) if isinstance(k.get("low"), (int, float))],
        [k.get("high") for k in snapshot.get("klines", []) if isinstance(k.get("high"), (int, float))],
        snapshot.get("overlay_candidates", []),
    )

    if supports or resistances:
        set_levels(symbol, supports, resistances, meta={"source": key_level_source})
        logger.info(f"[{key_level_source.upper()}] Cached levels: {len(supports)} supports, {len(resistances)} resistances")
    if overlays:
        set_overlays(symbol, overlays, meta={"source": "ai"})
        logger.info(f"[AI Signal] 缓存辅助线: {len(overlays)} 条")

    logger.info(f"[AI Signal] ✅ {symbol} 分析完成: {analysis[:50]}..." if analysis else f"[AI Signal] ✅ {symbol} 分析完成")

    result = {
        "analysis": analysis or raw,
        "supports": supports,
        "resistances": resistances,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "rr": rr,
        "risk_level": risk_level,
        "entry_decision": entry_decision,
        "direction": direction,
        "overlays": overlays,
    }

    # 如果 AI 建议入场，转发信号到交易系统
    if entry_decision == "yes" and direction in ("long", "short") and stop_loss and take_profit:
        try:
            from ai_signal_forwarder import forward_ai_signal

            # 构建止盈级别列表
            tp_levels = []
            if take_profit:
                # 默认分两级止盈
                if direction == "long":
                    tp_levels = [
                        (price + (take_profit - price) * 0.6, 0.5),  # 60% 目标平 50%
                        (take_profit, 0.5),  # 100% 目标平剩余 50%
                    ]
                else:  # short
                    tp_levels = [
                        (price - (price - take_profit) * 0.6, 0.5),  # 60% 目标平 50%
                        (take_profit, 0.5),  # 100% 目标平剩余 50%
                    ]

            # 计算信心度（基于风险等级和 RR 比）
            confidence = 0.5
            if risk_level == "low":
                confidence = 0.7
            elif risk_level == "high":
                confidence = 0.3
            if rr and rr >= 2.0:
                confidence = min(1.0, confidence + 0.2)

            message_id = None
            if signal_payload and isinstance(signal_payload, dict):
                item = signal_payload.get("item", {})
                message_id = item.get("id") or item.get("messageId")

            forward_ai_signal(
                symbol=symbol,
                direction=direction.upper(),
                entry_price=price,
                stop_loss=stop_loss,
                take_profit_levels=tp_levels,
                confidence=confidence,
                analysis=analysis,
                message_id=str(message_id) if message_id else None,
            )
            logger.info(f"[AI Signal] 已转发交易信号: {symbol} {direction.upper()} @ {price}")
        except Exception as e:
            logger.warning(f"[AI Signal] 转发交易信号失败: {e}")

    return result


def test_ai_single(symbol: str = "BTC") -> Optional[Dict[str, Any]]:
    """Run AI analysis for one symbol and render a chart locally."""
    result = analyze_signal(symbol)
    if not result:
        logger.warning("AI analysis failed or missing API config.")
        return None

    from chart_pro_v10 import generate_chart_v10

    image_data = generate_chart_v10(symbol, interval="1h", limit=200)
    if not image_data:
        logger.warning("Chart generation failed.")
        return result

    os.makedirs("output", exist_ok=True)
    image_path = os.path.join("output", f"ai_single_{symbol}.png")
    json_path = os.path.join("output", f"ai_single_{symbol}.json")

    with open(image_path, "wb") as f:
        f.write(image_data)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    logger.info("Saved AI single output: %s", image_path)
    logger.info("Saved AI single JSON: %s", json_path)
    return result
