"""
专业图表生成模块 v20 (Quantum Omni-Intelligence)
- Features: Vertical Heatmap, AI Trend Projections, Indicators Confluence
- Data: Full Backend Docking (Binance, CoinGecko/CMC/CryptoCompare fallback)
- Style: Ultra-Professional Fintech Cinematic (Glow & Projections)
"""

import io
import os
import math
import time
import requests
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.collections import LineCollection, PolyCollection
from matplotlib.colors import LinearSegmentedColormap
from scipy.ndimage import gaussian_filter1d
from chart_logger import ChartGenerationLogger
from logger import logger
from key_levels_enhanced import find_key_levels_enhanced, check_confluence
from ai_market_analysis import get_ai_market_analysis
from auxiliary_line_drawer import draw_auxiliary_lines_optimized
from ai_key_levels_cache import get_levels as get_ai_levels
from ai_market_summary import get_ai_summary_config, get_ai_overlays_config
from chart_fonts import configure_matplotlib_fonts
from market_data_sources import fetch_market_snapshot

# ==================== 代理配置 ====================
try:
    from config import SOCKS5_PROXY, HTTP_PROXY
except ImportError:
    SOCKS5_PROXY = ""
    HTTP_PROXY = ""

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


def _read_int_env(env_key: str, default: int) -> int:
    raw = os.getenv(env_key)
    if raw is not None and str(raw).strip() != "":
        try:
            return int(float(raw))
        except Exception:
            return default
    return default


VALUESCAN_KEY_LEVELS_DAYS = _read_int_env("VALUESCAN_KEY_LEVELS_CHART_DAYS", 7)


def _get_proxies():
    """
    获取代理配置用于 Binance API 请求
    """
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


# ==================== Endpoints ====================
BINANCE_FUT_BASE = "https://fapi.binance.com"

COLORS = {
    'bg_top': '#0F172A', 'bg_bot': '#020617', 'panel': '#1E293B',
    'grid': '#334155', 'text': '#F8FAFC', 'text_dim': '#94A3B8',
    'up': '#10B981', 'down': '#F43F5E', 'ema20': '#F59E0B',
    'ema50': '#38BDF8', 'ema200': '#A855F7', 'vwap': '#EC4899',
    'ai_accent': '#6366F1', 'gold': '#F59E0B'
}

# ==================== Professional Data Matrix ====================

def _req(url, params=None, headers=None):
    """发送 HTTP GET 请求，支持代理"""
    proxies = _get_proxies()
    try:
        r = requests.get(url, params=params, headers=headers, timeout=15, proxies=proxies)
        return r.json() if r.status_code == 200 else None
    except Exception as e:
        # 如果代理失败，尝试直连
        if proxies:
            try:
                r = requests.get(url, params=params, headers=headers, timeout=15)
                return r.json() if r.status_code == 200 else None
            except:
                pass
        logger.debug(f"[chart_pro_v10] _req failed: {url} - {e}")
        return None


def _normalize_valuescan_flow_detail(resp):
    if not isinstance(resp, dict) or resp.get("code") != 200:
        return {}
    data = resp.get("data")
    items = []
    if isinstance(data, list):
        items = [item for item in data if isinstance(item, dict)]
    elif isinstance(data, dict):
        for key in ("list", "records", "items"):
            if isinstance(data.get(key), list):
                items = [item for item in data.get(key) if isinstance(item, dict)]
                break
        if not items:
            for key, value in data.items():
                if isinstance(value, dict):
                    item = dict(value)
                    item.setdefault("timeType", key)
                    items.append(item)
    result = {}
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
    def _first_float(obj, keys):
        for key in keys:
            value = obj.get(key)
            if value is None:
                continue
            try:
                return float(value)
            except Exception:
                continue
        return None
    for item in items:
        period = item.get("timeType") or item.get("period") or item.get("time") or item.get("timeParticle")
        period = aliases.get(str(period).strip().lower(), str(period).strip().lower() if period else "")
        if not period:
            continue
        in_val = _first_float(item, ("inFlowValue", "inFlow", "tradeIn", "stopTradeIn", "contractTradeIn"))
        out_val = _first_float(item, ("outFlowValue", "outFlow", "tradeOut", "stopTradeOut", "contractTradeOut"))
        net_val = _first_float(item, ("netFlowValue", "netFlow", "tradeInflow", "stopTradeInflow", "contractTradeInflow"))
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


def _get_valuescan_exchange_flow(symbol):
    try:
        import sys
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if base_dir not in sys.path:
            sys.path.insert(0, base_dir)
        from valuescan_api import get_exchange_flow_detail
        clean_symbol = symbol.upper().replace("$", "").replace("USDT", "").strip()
        resp = get_exchange_flow_detail(clean_symbol)
        return _normalize_valuescan_flow_detail(resp)
    except Exception as exc:
        logger.debug(f"[chart_pro_v10] valuescan flow failed: {exc}")
        return {}


def _calc_liq_from_binance(payload):
    if not isinstance(payload, list):
        return None
    longs = 0.0
    shorts = 0.0
    for item in payload:
        if not isinstance(item, dict):
            continue
        side = str(item.get("side", "")).upper()
        price = float(item.get("avgPrice") or item.get("price") or 0)
        qty = float(item.get("origQty") or item.get("executedQty") or 0)
        notional = price * qty
        if side == "SELL":
            longs += notional
        elif side == "BUY":
            shorts += notional
    if longs == 0 and shorts == 0:
        return None
    return {"longs": longs, "shorts": shorts}

def get_integrated_data(symbol, interval):
    base = symbol.upper().replace('$', '').replace('USDT', '').strip()
    fs = f"{base}USDT"
    
    # 1. Primary Market
    k_raw = _req(f"{BINANCE_FUT_BASE}/fapi/v1/klines", {'symbol': fs, 'interval': interval, 'limit': 200})
    if not k_raw: return None
    df = pd.DataFrame(k_raw, columns=['timestamp','open','high','low','close','volume','ct','qv','t','tbb','tbq','i']).iloc[:,:6]
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    for c in df.columns[1:]: df[c] = df[c].astype(float)
    
    # 2. Intelligence Sources
    tick = _req(f"{BINANCE_FUT_BASE}/fapi/v1/ticker/24hr", {'symbol': fs})
    if not isinstance(tick, dict):
        market = fetch_market_snapshot(base)
        if market:
            tick = {
                "priceChangePercent": market.get("price_change_percent", 0),
                "highPrice": market.get("high_24h", 0),
                "lowPrice": market.get("low_24h", 0),
                "quoteVolume": market.get("volume_24h", 0),
                "openPrice": market.get("open_24h", market.get("price", 0)),
            }
    fund = _req(f"{BINANCE_FUT_BASE}/fapi/v1/fundingRate", {'symbol': fs, 'limit': 1})
    ls_hist = _req(f"{BINANCE_FUT_BASE}/futures/data/globalLongShortAccountRatio", {'symbol': fs, 'period': '5m', 'limit': 1})
    
    vs_flow = _get_valuescan_exchange_flow(base)
    taker_flow = _req(f"{BINANCE_FUT_BASE}/futures/data/takerlongshortRatio", {'symbol': fs, 'period': '15m', 'limit': 24}) if not vs_flow else None
    oi_raw = _req(f"{BINANCE_FUT_BASE}/fapi/v1/openInterest", {'symbol': fs})
    oi_hist = _req(f"{BINANCE_FUT_BASE}/futures/data/openInterestHist", {'symbol': fs, 'period': '1h', 'limit': 2})
    liq = None
    ob_raw = _req(f"{BINANCE_FUT_BASE}/fapi/v1/depth", {'symbol': fs, 'limit': 50})
    
    # AI System Docking
    ai_lvls = get_ai_levels(base)

    end_ms = int(time.time() * 1000)
    start_ms = end_ms - 24 * 60 * 60 * 1000
    liq_raw = _req(
        f"{BINANCE_FUT_BASE}/fapi/v1/forceOrders",
        {'symbol': fs, 'startTime': start_ms, 'endTime': end_ms, 'limit': 1000},
    )
    liq_stats = _calc_liq_from_binance(liq_raw)

    oi_stats = {}
    if isinstance(oi_raw, dict):
        oi_stats["current"] = float(oi_raw.get("openInterest", 0) or 0)
    if isinstance(oi_hist, list) and len(oi_hist) >= 2:
        try:
            prev = float(oi_hist[-2].get("sumOpenInterest", 0) or 0)
            curr = float(oi_hist[-1].get("sumOpenInterest", 0) or 0)
            if prev > 0:
                oi_stats["delta_1h"] = (curr - prev) / prev * 100.0
        except Exception:
            pass

    return {
        'df': df,
        'tick': tick,
        'fund': fund,
        'oi': oi_stats,
        'taker_flow': taker_flow,
        'vs_flow': vs_flow,
        'liq': liq_stats,
        'ls': ls_hist,
        'ai_lvls': ai_lvls,
        'ob': {'bids':[[float(p),float(a)] for p,a in ob_raw['bids']], 'asks':[[float(p),float(a)] for p,a in ob_raw['asks']]} if ob_raw else None
    }


def get_klines(symbol, timeframe='1h', limit=200):
    base = symbol.upper().replace('$', '').strip()
    if not base.endswith('USDT'):
        base = f"{base}USDT"
    k_raw = _req(
        f"{BINANCE_FUT_BASE}/fapi/v1/klines",
        {'symbol': base, 'interval': timeframe, 'limit': limit},
    )
    if not k_raw:
        return None
    df = pd.DataFrame(
        k_raw,
        columns=['timestamp','open','high','low','close','volume','ct','qv','t','tbb','tbq','i'],
    ).iloc[:,:6]
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    for c in df.columns[1:]:
        df[c] = df[c].astype(float)
    return df


def get_orderbook(symbol, limit=100):
    base = symbol.upper().replace('$', '').strip()
    if not base.endswith('USDT'):
        base = f"{base}USDT"
    ob_raw = _req(f"{BINANCE_FUT_BASE}/fapi/v1/depth", {'symbol': base, 'limit': limit})
    if not ob_raw:
        return None
    return {
        'bids': [[float(p), float(a)] for p, a in ob_raw.get('bids', [])],
        'asks': [[float(p), float(a)] for p, a in ob_raw.get('asks', [])],
    }


def calculate_atr(df, period=14):
    if df is None or df.empty:
        return None
    high = df['high']
    low = df['low']
    close = df['close'].shift(1)
    tr = pd.concat([(high - low), (high - close).abs(), (low - close).abs()], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    return float(atr.iloc[-1]) if not atr.empty else None


# ==================== Pattern Detection (Local) ====================

PATTERN_SCORE_THRESHOLDS = {
    "channel": 0.62,
    "flag": 0.6,
    "wedge": 0.6,
    "triangle": 0.6,
}

def _linear_regression(series):
    x = np.arange(len(series), dtype=float)
    y = np.asarray(series, dtype=float)
    if len(y) < 2:
        return 0.0, y[-1] if len(y) else 0.0, 0.0
    slope, intercept = np.polyfit(x, y, 1)
    y_pred = slope * x + intercept
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
    return float(slope), float(intercept), float(r2)


def _find_swings(series, window=4, mode="high"):
    points = []
    if len(series) < window * 2 + 1:
        return points
    for i in range(window, len(series) - window):
        seg = series[i - window : i + window + 1]
        if mode == "high" and series[i] >= max(seg):
            points.append((i, series[i]))
        elif mode == "low" and series[i] <= min(seg):
            points.append((i, series[i]))
    return points


def _count_line_touches(points, slope, intercept, tol):
    touches = 0
    for idx, price in points:
        if abs((slope * idx + intercept) - price) <= tol:
            touches += 1
    return touches


def detect_channel(df, atr=None, windows=(60, 80, 120), r2_min=0.55):
    best = None
    highs = df["high"].values
    lows = df["low"].values
    curr = float(df["close"].iloc[-1])
    tol = max((atr or 0) * 0.5, curr * 0.003)

    for w in windows:
        if len(df) < w + 5:
            continue
        h = highs[-w:]
        l = lows[-w:]
        slope_h, intercept_h, r2_h = _linear_regression(h)
        slope_l, intercept_l, r2_l = _linear_regression(l)
        if min(r2_h, r2_l) < r2_min:
            continue
        slope_diff = abs(slope_h - slope_l)
        slope_avg = (abs(slope_h) + abs(slope_l)) / 2.0 + 1e-9
        parallel_score = max(0.0, 1.0 - slope_diff / (slope_avg * 0.6))
        width_start = intercept_h - intercept_l
        width_end = (slope_h * (w - 1) + intercept_h) - (slope_l * (w - 1) + intercept_l)
        width_avg = (abs(width_start) + abs(width_end)) / 2.0
        if width_avg < max((atr or 0) * 1.2, curr * 0.004):
            continue

        high_swings = _find_swings(h, window=3, mode="high")
        low_swings = _find_swings(l, window=3, mode="low")
        hi_hits = _count_line_touches(high_swings, slope_h, intercept_h, tol)
        lo_hits = _count_line_touches(low_swings, slope_l, intercept_l, tol)
        if hi_hits < 2 or lo_hits < 2:
            continue

        score = min(r2_h, r2_l) * 0.55 + parallel_score * 0.45
        best = {
            "type": "up" if slope_h > 0 else "down" if slope_h < 0 else "side",
            "upper": (slope_h, intercept_h),
            "lower": (slope_l, intercept_l),
            "window": w,
            "score": float(score),
        } if not best or score > best["score"] else best
    return best


def detect_best_wedge(df, atr=None, windows=(60, 80, 120), r2_min=0.5):
    best = None
    highs = df["high"].values
    lows = df["low"].values
    curr = float(df["close"].iloc[-1])
    tol = max((atr or 0) * 0.6, curr * 0.0035)
    vols = df["volume"].values

    for w in windows:
        if len(df) < w + 5:
            continue
        h = highs[-w:]
        l = lows[-w:]
        slope_h, intercept_h, r2_h = _linear_regression(h)
        slope_l, intercept_l, r2_l = _linear_regression(l)
        if min(r2_h, r2_l) < r2_min:
            continue
        if slope_h == 0 or slope_l == 0:
            continue
        if slope_h * slope_l < 0:
            continue
        width_start = intercept_h - intercept_l
        width_end = (slope_h * (w - 1) + intercept_h) - (slope_l * (w - 1) + intercept_l)
        if abs(width_end) >= abs(width_start) * 0.8:
            continue
        if abs(slope_h - slope_l) < abs(slope_h) * 0.15:
            continue

        vol_slope, _, _ = _linear_regression(vols[-w:])
        vol_score = 1.0 if vol_slope < 0 else 0.4
        high_swings = _find_swings(h, window=3, mode="high")
        low_swings = _find_swings(l, window=3, mode="low")
        hi_hits = _count_line_touches(high_swings, slope_h, intercept_h, tol)
        lo_hits = _count_line_touches(low_swings, slope_l, intercept_l, tol)
        if hi_hits < 2 or lo_hits < 2:
            continue

        score = min(r2_h, r2_l) * 0.6 + vol_score * 0.4
        best = {
            "type": "rising" if slope_h > 0 else "falling",
            "upper": (slope_h, intercept_h),
            "lower": (slope_l, intercept_l),
            "window": w,
            "score": float(score),
        } if not best or score > best["score"] else best
    return best


def detect_best_triangle(df, atr=None, windows=(60, 80, 120), r2_min=0.5):
    best = None
    highs = df["high"].values
    lows = df["low"].values
    curr = float(df["close"].iloc[-1])
    flat_thresh = max((atr or 0) * 0.15, curr * 0.0008)
    vols = df["volume"].values

    for w in windows:
        if len(df) < w + 5:
            continue
        h = highs[-w:]
        l = lows[-w:]
        slope_h, intercept_h, r2_h = _linear_regression(h)
        slope_l, intercept_l, r2_l = _linear_regression(l)
        if min(r2_h, r2_l) < r2_min:
            continue
        width_start = intercept_h - intercept_l
        width_end = (slope_h * (w - 1) + intercept_h) - (slope_l * (w - 1) + intercept_l)
        if abs(width_end) >= abs(width_start) * 0.85:
            continue

        is_flat_top = abs(slope_h) <= flat_thresh
        is_flat_bot = abs(slope_l) <= flat_thresh
        if is_flat_top:
            t_type = "descending"
        elif is_flat_bot:
            t_type = "ascending"
        elif slope_h < 0 and slope_l > 0:
            t_type = "sym"
        else:
            continue

        vol_slope, _, _ = _linear_regression(vols[-w:])
        vol_score = 1.0 if vol_slope < 0 else 0.5
        score = min(r2_h, r2_l) * 0.6 + vol_score * 0.4
        best = {
            "type": t_type,
            "upper": (slope_h, intercept_h),
            "lower": (slope_l, intercept_l),
            "window": w,
            "score": float(score),
        } if not best or score > best["score"] else best
    return best


def detect_best_flag(df, atr=None, impulse_lookback=20, windows=(12, 18, 24)):
    best = None
    closes = df["close"].values
    highs = df["high"].values
    lows = df["low"].values
    vols = df["volume"].values
    curr = float(df["close"].iloc[-1])
    atr = atr or (curr * 0.005)

    for w in windows:
        if len(df) < w + impulse_lookback + 2:
            continue
        flag_start = len(df) - w
        impulse_start = len(df) - w - impulse_lookback
        impulse_move = closes[flag_start] - closes[impulse_start]
        if abs(impulse_move) < atr * 3.0:
            continue
        impulse_dir = 1 if impulse_move > 0 else -1

        h = highs[-w:]
        l = lows[-w:]
        slope_h, intercept_h, r2_h = _linear_regression(h)
        slope_l, intercept_l, r2_l = _linear_regression(l)
        if min(r2_h, r2_l) < 0.5:
            continue
        if impulse_dir > 0 and slope_h > 0:
            continue
        if impulse_dir < 0 and slope_l < 0:
            continue

        vol_slope, _, _ = _linear_regression(vols[-w:])
        vol_score = 1.0 if vol_slope < 0 else 0.5
        score = min(r2_h, r2_l) * 0.6 + vol_score * 0.4
        best = {
            "type": "bull" if impulse_dir > 0 else "bear",
            "upper": (slope_h, intercept_h),
            "lower": (slope_l, intercept_l),
            "window": w,
            "score": float(score),
        } if not best or score > best["score"] else best
    return best


def _fmt_big(value):
    if value is None:
        return "N/A"
    try:
        v = float(value)
    except Exception:
        return "N/A"
    if abs(v) >= 1e9:
        return f"{v/1e9:.2f}B"
    if abs(v) >= 1e6:
        return f"{v/1e6:.2f}M"
    if abs(v) >= 1e3:
        return f"{v/1e3:.2f}K"
    return f"{v:.2f}"


def _fmt_flow_amount(value):
    try:
        v = float(value)
    except Exception:
        return "N/A"
    abs_v = abs(v)
    if abs_v >= 1e6:
        return f"{v/1e6:.2f}M"
    if abs_v >= 1e3:
        return f"{v/1e3:.1f}K"
    return f"{v:.2f}"

# ==================== Key Level Normalization ====================

def _point_time_ms(point):
    if not isinstance(point, dict):
        return 0
    for key in ("time", "ts", "timestamp", "dateTime", "date"):
        value = point.get(key)
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


def _filter_dense_points_by_days(points, days):
    if not points or days <= 0:
        return points
    cutoff_ms = int(time.time() * 1000) - days * 24 * 60 * 60 * 1000
    return [p for p in points if _point_time_ms(p) >= cutoff_ms]


def _dense_point_price(item):
    if not isinstance(item, dict):
        return None
    for key in ("price", "levelPrice", "val", "value", "cost", "priceLevel"):
        value = item.get(key)
        if value is None:
            continue
        try:
            return float(value)
        except Exception:
            continue
    text = item.get("priceRange") or item.get("range") or ""
    if isinstance(text, str) and "-" in text:
        parts = [p.strip() for p in text.split("-", 1)]
        if len(parts) == 2:
            try:
                low = float(parts[0])
                high = float(parts[1])
                return (low + high) / 2
            except Exception:
                return None
    return None


def _dedupe_levels(levels, precision=6):
    seen = set()
    result = []
    for level in levels:
        try:
            price = float(level)
        except Exception:
            continue
        key = round(price, precision)
        if key in seen:
            continue
        seen.add(key)
        result.append(price)
    return result


def _compress_levels(levels, min_gap, max_levels):
    if not levels:
        return []
    levels = sorted(levels)
    if min_gap <= 0:
        trimmed = levels
    else:
        trimmed = []
        for price in levels:
            if not trimmed or abs(price - trimmed[-1]) >= min_gap:
                trimmed.append(price)
    if max_levels and len(trimmed) > max_levels:
        if max_levels == 1:
            return [trimmed[-1]]
        step = (len(trimmed) - 1) / float(max_levels - 1)
        return [trimmed[int(round(i * step))] for i in range(max_levels)]
    return trimmed

# ==================== Core UI Components ====================

def draw_glow_line(ax, x, y, color, lw=1.2, ls='-', label=None):
    """高级发光线条渲染"""
    ax.plot(x, y, color=color, lw=lw, ls=ls, alpha=0.9, zorder=5)
    ax.plot(x, y, color=color, lw=lw*4, alpha=0.15, zorder=4) # Glow layer
    if label:
        ax.text(x[-1], y[-1], f" {label}", color=color, fontsize=8, fontweight='bold', va='center')

def generate_chart_v10(symbol, interval='1h', limit=200, allow_ai_overlays: bool = True):
    cl = ChartGenerationLogger(symbol); cl.log_start()
    try:
        # Step 1: Accurate Docking
        data = get_integrated_data(symbol, interval)
        if not data: return None
        df = data.get('df')
        tick = data.get('tick')
        fund = data.get('fund')
        oi_stats = data.get('oi')
        taker_flow = data.get('taker_flow')
        vs_flow = data.get('vs_flow')
        liq = data.get('liq')
        ls_hist = data.get('ls')
        ai_lvls = data.get('ai_lvls')
        ob = data.get('ob')
        
        curr_p = df['close'].iloc[-1]; atr = (df['high'] - df['low']).rolling(14).mean().iloc[-1]
        df['ema20'] = df['close'].ewm(span=20).mean()
        df['ema50'] = df['close'].ewm(span=50).mean()
        df['vwap'] = ((df['high']+df['low']+df['close'])/3 * df['volume']).cumsum() / df['volume'].cumsum()
        
        # Step 2: Workspace Setup
        configure_matplotlib_fonts([
            'Microsoft YaHei',
            'SimHei',
            'WenQuanYi Micro Hei',
            'Noto Sans CJK SC',
            'Noto Sans CJK',
            'Noto Sans',
            'DejaVu Sans',
            'Arial',
        ])
        dpi = 120; fig = plt.figure(figsize=(16, 10), dpi=dpi)
        
        # Background Gradient
        ax_bg = fig.add_axes([0,0,1,1], zorder=-10); ax_bg.axis('off')
        ax_bg.imshow(np.linspace(0, 1, 256).reshape(-1, 1), cmap=LinearSegmentedColormap.from_list('b', [COLORS['bg_top'], COLORS['bg_bot']]), aspect='auto', extent=[0,1,0,1])

        # Grid Layout (调整布局：减少右侧面板宽度，增加图表空间)
        gs = fig.add_gridspec(2, 3, width_ratios=[0.02, 0.80, 0.18], height_ratios=[0.8, 0.2],
                              wspace=0.04, hspace=0.05, left=0.02, right=0.98, top=0.95, bottom=0.04)
        ax_heat, ax_main, ax_info, ax_flow = fig.add_subplot(gs[0,0]), fig.add_subplot(gs[0,1]), fig.add_subplot(gs[0,2]), fig.add_subplot(gs[1,:])
        for a in [ax_heat, ax_main, ax_info, ax_flow]: a.axis('off')

        p_min, p_max = df['low'].min() - atr, df['high'].max() + atr
        ax_main.set_ylim(p_min, p_max); ax_main.set_xlim(-5, len(df)+22)
        ax_main.grid(True, linestyle=(0, (1, 10)), color=COLORS['grid'], alpha=0.4)

        # --- A. HEATMAP Strip (Price Density) ---
        bins = np.linspace(p_min, p_max, 100); h_v, _ = np.histogram(df['close'], bins=bins, weights=df['volume'])
        h_n = gaussian_filter1d(h_v/h_v.max(), 1.5)
        cmap_h = LinearSegmentedColormap.from_list('h', [COLORS['bg_top'], COLORS['ai_accent'], COLORS['vwap']])
        ax_heat.barh(bins[:-1], h_n, height=(bins[1]-bins[0]), color=[cmap_h(v) for v in h_n], edgecolor='none', alpha=0.8)
        ax_heat.set_ylim(ax_main.get_ylim()); ax_heat.invert_xaxis()

        # --- B. AUXILIARY LINE SYSTEM (ValuScan + AI + LOCAL) ---
        # 优先级: ValuScan > AI > Local
        
        # 1. 检查 ValuScan 主力位配置（最高优先级）
        enable_valuescan_key_levels = True
        valuescan_levels = None
        clean_symbol = symbol.upper().replace("USDT", "").replace("$", "").strip()
        try:
            from ai_key_levels_config import get_ai_levels_config
            ai_levels_cfg = get_ai_levels_config()
            enable_valuescan_key_levels = ai_levels_cfg.get("enable_valuescan", True)
            enable_ai_key_levels = ai_levels_cfg.get("enabled", False)
            use_ai_levels_in_chart = ai_levels_cfg.get("use_in_chart", False)
        except Exception:
            enable_valuescan_key_levels = True
            enable_ai_key_levels = False
            use_ai_levels_in_chart = False

        if enable_valuescan_key_levels and valuescan_levels is None:
            try:
                import sys
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                if base_dir not in sys.path:
                    sys.path.insert(0, base_dir)
                from valuescan_api import get_main_force, get_hold_cost, get_keyword

                keyword = get_keyword(clean_symbol)
                if keyword:
                    mf = get_main_force(clean_symbol, VALUESCAN_KEY_LEVELS_DAYS)
                    hc = get_hold_cost(clean_symbol, VALUESCAN_KEY_LEVELS_DAYS)
                    supports = []
                    resistances = []

                    if mf.get("code") == 200:
                        mf_data = mf.get("data", [])
                        if mf_data:
                            has_ts = any(_point_time_ms(item) > 0 for item in mf_data)
                            if has_ts:
                                mf_data = _filter_dense_points_by_days(mf_data, VALUESCAN_KEY_LEVELS_DAYS)
                            type_values = {
                                item.get("type")
                                for item in mf_data
                                if isinstance(item, dict) and item.get("type") is not None
                            }
                            if type_values:
                                prefer_type = 2 if 2 in type_values else (1 if 1 in type_values else None)
                                if prefer_type is not None:
                                    mf_data = [
                                        item for item in mf_data
                                        if isinstance(item, dict) and item.get("type") == prefer_type
                                    ]
                            for item in mf_data:
                                price = _dense_point_price(item)
                                if price is None:
                                    continue
                                try:
                                    resistances.append(float(price))
                                except Exception:
                                    continue
                    if hc.get("code") == 200:
                        hc_data = hc.get("data", {}).get("holdingPrice", [])
                        if hc_data:
                            supports.append(float(hc_data[-1]["val"]))

                    if supports or resistances:
                        valuescan_levels = {
                            "supports": supports,
                            "resistances": resistances,
                        }
            except Exception as e:
                logger.debug(f"[ValuScan] Failed to get key levels: {e}")
                valuescan_levels = None

        try:
            ai_overlays_cfg = get_ai_overlays_config()
            enable_ai_overlays = ai_overlays_cfg.get("enabled", False)
            prefer_local_overlays = ai_overlays_cfg.get("prefer_local", True)
        except Exception:
            enable_ai_overlays = False
            prefer_local_overlays = True
        if not allow_ai_overlays:
            enable_ai_overlays = False

        logger.info(
            "[Config] ValuScan=%s AI_Levels=%s (chart=%s) Overlays=%s (prefer_local=%s)",
            enable_valuescan_key_levels,
            enable_ai_key_levels,
            use_ai_levels_in_chart,
            enable_ai_overlays,
            prefer_local_overlays,
        )

        # 3. Key Levels - ???????????? ValuScan?????????AI?????????Local
        # ??????????????????????????????????????????????????????????????????????????????
        valuescan_available = bool(
            valuescan_levels
            and (valuescan_levels.get("supports") or valuescan_levels.get("resistances"))
        )
        ai_levels_payload = None
        if isinstance(ai_lvls, dict):
            if ai_lvls.get("meta", {}).get("source") != "valuescan":
                ai_levels_payload = ai_lvls
        elif ai_lvls:
            ai_levels_payload = ai_lvls
        if enable_valuescan_key_levels:
            if valuescan_available:
                s_list = valuescan_levels.get("supports", [])
                r_list = valuescan_levels.get("resistances", [])
                level_meta = {"source": "valuescan", "days": VALUESCAN_KEY_LEVELS_DAYS}
                logger.info(f"[Key Levels] Using ValuScan data: supports={s_list}, resistances={r_list}")
            else:
                s_list = []
                r_list = []
                level_meta = {"source": "valuescan", "days": VALUESCAN_KEY_LEVELS_DAYS, "status": "missing"}
                logger.warning("[Key Levels] ValuScan enabled but no data; skip AI/local fallback.")
        elif enable_ai_key_levels and use_ai_levels_in_chart and ai_levels_payload:
            s_list = ai_levels_payload.get("supports", [])
            r_list = ai_levels_payload.get("resistances", [])
            level_meta = {"source": "ai"}
            logger.info(f"[Key Levels] Using AI data: supports={s_list}, resistances={r_list}")
        else:
            s_list, r_list, level_meta = find_key_levels_enhanced(
                df, curr_p, ob, market_cap=None, ai_levels=None
            )

        level_gap = max((p_max - p_min) * 0.008, (atr or 0) * 0.6, curr_p * 0.0015)
        if level_meta.get("source") == "valuescan":
            s_list = [p for p in s_list if p_min <= p <= p_max]
            r_list = [p for p in r_list if p_min <= p <= p_max]
        else:
            max_levels = int(os.getenv("VALUESCAN_KEY_LEVELS_MAX", "12"))
            s_list = _compress_levels(
                _dedupe_levels([p for p in s_list if p_min <= p <= p_max]),
                level_gap,
                max_levels,
            )
            r_list = _compress_levels(
                _dedupe_levels([p for p in r_list if p_min <= p <= p_max]),
                level_gap,
                max_levels,
            )

        # Label Manager for collision detection
        class LabelManager:
            """管理标签位置，防止重叠"""
            def __init__(self, chart_width, price_range):
                self.chart_width = chart_width
                self.price_range = price_range
                self.placed_labels = []  # [(x, y, height), ...]
                self.min_vertical_spacing = price_range * 0.015  # 1.5% 最小间距

            def can_place_label(self, x, y, height=None):
                """检查是否可以放置标签"""
                if height is None:
                    height = self.min_vertical_spacing

                for placed_x, placed_y, placed_height in self.placed_labels:
                    # 检查垂直重叠
                    if abs(x - placed_x) < 5:  # 水平位置相近
                        if abs(y - placed_y) < height + placed_height:
                            return False
                return True

            def find_best_position(self, x, y, height=None, max_offset=5):
                """找到最佳标签位置（避免重叠）"""
                if height is None:
                    height = self.min_vertical_spacing

                # 尝试原位置
                if self.can_place_label(x, y, height):
                    self.placed_labels.append((x, y, height))
                    return x, y

                # 尝试上下偏移
                for offset in range(1, max_offset + 1):
                    # 向上偏移
                    new_y = y + offset * self.min_vertical_spacing
                    if self.can_place_label(x, new_y, height):
                        self.placed_labels.append((x, new_y, height))
                        return x, new_y

                    # 向下偏移
                    new_y = y - offset * self.min_vertical_spacing
                    if self.can_place_label(x, new_y, height):
                        self.placed_labels.append((x, new_y, height))
                        return x, new_y

                # 如果都不行，使用原位置但记录
                self.placed_labels.append((x, y, height))
                return x, y

        # 初始化标签管理器
        label_manager = LabelManager(len(df) + 22, p_max - p_min)

        def draw_key_line(p, c, label, source, strength=None):
            # 使用增强版汇合检测 - 动态阈值
            confluence_threshold = level_meta.get('confluence_threshold', 0.004)
            confluence_info = check_confluence(p, df, confluence_threshold)

            # 检查是否有汇合
            has_confluence = any(confluence_info.values())

            # 根据强度和汇合调整样式 (降低alpha和线宽以减少视觉混乱)
            if strength and strength > 0.7:
                base_lw, base_alpha = (1.5, 0.85)  # 降低
            elif has_confluence:
                base_lw, base_alpha = (1.2, 0.75)  # 降低
            else:
                base_lw, base_alpha = (0.7, 0.5)   # 降低

            # 绘制主线 (移除发光效果以减少视觉混乱)
            ax_main.axhline(p, color=c, ls='-' if has_confluence else '--', lw=base_lw, alpha=base_alpha)

            # 构建标签
            tag = f"{source}:{label}"
            if strength:
                tag += f" ({strength:.0%})"

            # 添加汇合指标标记
            conf_indicators = [k.upper() for k, v in confluence_info.items() if v]
            if conf_indicators:
                tag += f" [{','.join(conf_indicators)}]"

            # 绘制标签 (使用智能位置管理)
            fontweight = 'bold' if (has_confluence or (strength and strength > 0.7)) else 'normal'
            label_x, label_y = label_manager.find_best_position(len(df)+20, p)
            ax_main.text(label_x, label_y, f"{tag} {p:,.2f}", color=c, fontsize=7,
                        va='center', ha='right', family='monospace', fontweight=fontweight)

        # 获取强度信息
        support_strengths = level_meta.get('support_strengths', [None] * len(s_list))
        resistance_strengths = level_meta.get('resistance_strengths', [None] * len(r_list))
        source = level_meta.get('source', 'QUANT')
        
        # 转换 source 为显示名称
        source_display = {
            'valuescan': 'VS',  # ValuScan
            'ai': 'AI',
            'QUANT': 'Q',
            'LOCAL': 'L',
        }.get(source.lower() if isinstance(source, str) else 'quant', source.upper()[:2])

        # 绘制支撑位 (限制为2个最强的)
        for i, s in enumerate(s_list):
            strength = support_strengths[i] if i < len(support_strengths) else None
            draw_key_line(s, COLORS['up'], "SUP", source_display, strength)

        # 绘制阻力位 (限制为2个最强的)
        for i, r in enumerate(r_list):
            strength = resistance_strengths[i] if i < len(resistance_strengths) else None
            draw_key_line(r, COLORS['down'], "RES", source_display, strength)

        # 2. AI Market Analysis & Auxiliary Lines (New System)
        ai_analysis = None
        try:
            # Always run local algorithm first for speed.
            auxiliary_lines = draw_auxiliary_lines_optimized(df, curr_p, atr, None)
            has_local_lines = any(
                auxiliary_lines.get(key) for key in ("trendlines", "channels", "zones")
            )

            if enable_ai_overlays and (not prefer_local_overlays or not has_local_lines):
                try:
                    ai_config = get_ai_overlays_config()
                    if ai_config and ai_config.get('api_key'):
                        language = os.getenv('VALUESCAN_LANGUAGE', 'zh').lower()
                        logger.info(f"Calling AI for market analysis of {symbol}...")
                        ai_analysis = get_ai_market_analysis(
                            symbol, df, curr_p, ob, None, ai_config, language
                        )
                        if ai_analysis:
                            logger.info(f"AI analysis completed for {symbol}")
                            auxiliary_lines = draw_auxiliary_lines_optimized(df, curr_p, atr, ai_analysis)
                except Exception as e:
                    logger.warning(f"AI market analysis failed: {e}")

            # 绘制趋势线
            for trendline in auxiliary_lines.get('trendlines', []):
                x1 = trendline['x1']
                y1 = trendline['y1']
                x2 = trendline['x2']
                y2 = trendline['y2']
                line_type = trendline['type']
                touches = trendline['touches']
                score = trendline['score']

                # 颜色
                color = COLORS['down'] if line_type == 'resistance' else COLORS['up']

                # 样式（根据得分）- 降低alpha和线宽
                if score >= 50:
                    lw, alpha, ls = 1.3, 0.75, '-'  # 降低
                else:
                    lw, alpha, ls = 1.0, 0.55, '--'  # 降低

                # 绘制主线 (移除发光效果以减少视觉混乱)
                ax_main.plot([x1, x2], [y1, y2], color=color, lw=lw, alpha=alpha, ls=ls, zorder=5)

                # 延伸线
                if x2 > x1:
                    slope = (y2 - y1) / (x2 - x1)
                    x_proj = np.array([x2, min(x2 + 15, len(df) + 20)])
                    y_proj = y2 + slope * (x_proj - x2)
                    ax_main.plot(x_proj, y_proj, color=color, lw=lw*0.7, ls=':', alpha=alpha*0.5, zorder=4)

                # 标签 (使用智能位置管理，缩短文本)
                label_x = x2 - 5
                label_y = y2
                label_text = f"{line_type.upper()[:3]} ({touches})"  # 缩短文本
                final_x, final_y = label_manager.find_best_position(label_x, label_y)
                ax_main.text(final_x, final_y, label_text, color=color, fontsize=6.5,
                            fontweight='bold' if score >= 50 else 'normal',
                            bbox=dict(boxstyle='round,pad=0.15', fc=COLORS['panel'], ec=color, alpha=0.6))

            # 绘制通道
            for channel in auxiliary_lines.get('channels', []):
                subtype = channel['subtype']
                upper = channel['upper']
                lower = channel['lower']
                score = channel['score']

                # 颜色
                if subtype == 'ascending':
                    color = COLORS['up']
                elif subtype == 'descending':
                    color = COLORS['down']
                else:
                    color = COLORS['ai_accent']

                # 样式 - 降低alpha和线宽
                lw, alpha = (1.5, 0.75) if score >= 60 else (1.2, 0.6)  # 降低

                # 绘制上轨 (移除发光效果以减少视觉混乱)
                x1, y1 = upper['x1'], upper['y1']
                x2, y2 = upper['x2'], upper['y2']
                ax_main.plot([x1, x2], [y1, y2], color=color, lw=lw, alpha=alpha, ls='-', zorder=5)

                # 绘制下轨 (移除发光效果以减少视觉混乱)
                x1, y1 = lower['x1'], lower['y1']
                x2, y2 = lower['x2'], lower['y2']
                ax_main.plot([x1, x2], [y1, y2], color=color, lw=lw, alpha=alpha, ls='-', zorder=5)

                # 标签
                mid_x = (upper['x2'] + lower['x2']) / 2
                mid_y = (upper['y2'] + lower['y2']) / 2
                label_text = f"{subtype.upper()} CHANNEL"
                ax_main.text(mid_x, mid_y, label_text, color=color, fontsize=8,
                            fontweight='bold', ha='center',
                            bbox=dict(boxstyle='round,pad=0.3', fc=COLORS['panel'], ec=color, alpha=0.8))

            # 绘制支撑/阻力区域 (先合并重叠区域)
            def merge_overlapping_zones(zones, merge_threshold=0.01):
                """合并重叠的支撑/阻力区域"""
                if not zones:
                    return []

                # 按类型分组
                support_zones = [z for z in zones if z.get('subtype') == 'support']
                resistance_zones = [z for z in zones if z.get('subtype') == 'resistance']

                def merge_group(zone_list):
                    if not zone_list:
                        return []

                    # 按价格排序
                    sorted_zones = sorted(zone_list, key=lambda z: z['price_mid'])
                    merged = []
                    current = sorted_zones[0].copy()

                    for i in range(1, len(sorted_zones)):
                        next_zone = sorted_zones[i]

                        # 检查是否重叠
                        if current['price_max'] >= next_zone['price_min'] * (1 - merge_threshold):
                            # 合并区域
                            current['price_min'] = min(current['price_min'], next_zone['price_min'])
                            current['price_max'] = max(current['price_max'], next_zone['price_max'])
                            current['price_mid'] = (current['price_min'] + current['price_max']) / 2
                            current['strength'] = max(current.get('strength', 50), next_zone.get('strength', 50))
                            # 优先保留AI来源
                            if next_zone.get('source') == 'AI':
                                current['source'] = 'AI'
                                if 'reason' in next_zone:
                                    current['reason'] = next_zone['reason']
                        else:
                            merged.append(current)
                            current = next_zone.copy()

                    merged.append(current)
                    return merged

                # 合并各组
                merged_supports = merge_group(support_zones)
                merged_resistances = merge_group(resistance_zones)

                return merged_supports + merged_resistances

            raw_zones = auxiliary_lines.get('zones', [])
            merged_zones = merge_overlapping_zones(raw_zones, merge_threshold=0.01)

            for zone in merged_zones:
                subtype = zone['subtype']
                price_min = zone['price_min']
                price_max = zone['price_max']
                price_mid = zone['price_mid']
                strength = zone.get('strength', 50)
                source = zone.get('source', 'LOCAL')

                # 颜色
                color = COLORS['down'] if subtype == 'resistance' else COLORS['up']

                # 透明度（根据强度）- 降低基础alpha
                alpha = 0.08 + (strength / 100) * 0.10  # 范围: 0.08-0.18 (原: 0.15-0.30)

                # 绘制区域 (移除中线以减少视觉混乱)
                ax_main.axhspan(price_min, price_max, color=color, alpha=alpha, zorder=3)

                # 标签 (简化并使用智能位置管理)
                label_text = f"{subtype.upper()[:3]}"  # SUP/RES
                if source == 'AI':
                    label_text = f"AI:{label_text}"

                label_x, label_y = label_manager.find_best_position(len(df) + 18, price_mid)
                ax_main.text(label_x, label_y, label_text, color=color, fontsize=6,
                            va='center', ha='right', fontweight='bold' if source == 'AI' else 'normal',
                            bbox=dict(boxstyle='round,pad=0.15', fc=COLORS['panel'], ec=color, alpha=0.5))

        except Exception as e:
            logger.warning(f"Auxiliary line drawing failed: {e}")
            import traceback
            traceback.print_exc()

        # 3. VRVP Overlay removed for clarity (avoid ambiguous bars)

        # --- C. MAIN CHART (Candles & Techs) ---
        x = np.arange(len(df)); o, c, h, l = df['open'], df['close'], df['high'], df['low']
        col_c = np.where(c>=o, COLORS['up'], COLORS['down'])
        ax_main.add_collection(LineCollection(np.stack([np.column_stack([x,l]), np.column_stack([x,h])], axis=1), colors=col_c, lw=0.8))
        verts = [[(i-0.35, min(o[i],c[i])), (i-0.35, max(o[i],c[i])), (i+0.35, max(o[i],c[i])), (i+0.35, min(o[i],c[i]))] for i in x]
        ax_main.add_collection(PolyCollection(verts, facecolors=col_c, edgecolors=None, alpha=0.9))
        
        ax_main.plot(x, df['ema20'], color=COLORS['ema20'], lw=0.9, alpha=0.55)  # 降低
        ax_main.plot(x, df['ema50'], color=COLORS['ema50'], lw=0.9, alpha=0.45)  # 降低
        ax_main.plot(x, df['vwap'], color=COLORS['vwap'], lw=0.7, ls=':', alpha=0.45)  # 降低

        # Dynamic Header & Price
        # 根据主力位数据源显示不同的标题 (使用英文避免字体问题)
        kl_source_name = {
            'valuescan': 'ValuScan',
            'ai': 'AI-QUANT',
            'QUANT': 'QUANT',
            'LOCAL': 'LOCAL',
        }.get(source.lower() if isinstance(source, str) else 'quant', 'QUANT')
        ax_main.text(0, 1.02, f"{symbol.upper()}USDT - {kl_source_name} - O:{o.iloc[-1]:.2f} H:{h.iloc[-1]:.2f} L:{l.iloc[-1]:.2f} C:{c.iloc[-1]:.2f}", transform=ax_main.transAxes, color=COLORS['text'], fontsize=10, family='monospace', fontweight='bold')
        ax_main.text(len(df)+1, curr_p, f" {curr_p:.2f} ", color='white', fontsize=9, fontweight='bold', bbox=dict(fc=COLORS['ai_accent'], ec='none', pad=3))

        # --- D. METRIC DASHBOARD ---
        ax_info.add_patch(mpatches.FancyBboxPatch((0,0), 1, 1, boxstyle="round,pad=0,rounding_size=0.04", fc=COLORS['panel'], alpha=0.7, transform=ax_info.transAxes))
        yp = 0.94
        def row(lbl, val, clr='white', mono=True):
            nonlocal yp
            ax_info.text(0.08, yp, lbl, color=COLORS['text_dim'], fontsize=9, transform=ax_info.transAxes)
            text_val = str(val)
            use_mono = mono and not any(ord(ch) > 127 for ch in text_val)
            family = 'monospace' if use_mono else None
            ax_info.text(0.92, yp, text_val, color=clr, ha='right', fontsize=9, fontweight='bold', family=family, transform=ax_info.transAxes)
            yp -= 0.045

        ax_info.text(0.5, yp, f"${curr_p:,.2f}", ha='center', color='white', fontsize=20, fontweight='bold', transform=ax_info.transAxes); yp -= 0.06
        if tick:
            row("24H涨跌", f"{float(tick['priceChangePercent']):+.2f}%", COLORS['up'] if float(tick['priceChangePercent'])>=0 else COLORS['down'])
            row("24H最高", f"{float(tick['highPrice']):,.2f}", COLORS['text'])
            row("24H最低", f"{float(tick['lowPrice']):,.2f}", COLORS['text'])
            row("24H成交额", _fmt_big(float(tick.get('quoteVolume', 0))), COLORS['text_dim'])
            row("24H开盘", f"{float(tick.get('openPrice', 0)):,.2f}", COLORS['text_dim'])
        if ls_hist:
            row("多空比", f"{float(ls_hist[0]['longShortRatio']):.2f}", COLORS['gold'])
        if fund:
            row("资金费率", f"{float(fund[0]['fundingRate'])*100:.4f}%", COLORS['ema50'])

        oi_val = None
        oi_delta = None
        if isinstance(oi_stats, dict):
            oi_val = oi_stats.get("current")
            oi_delta = oi_stats.get("delta_1h")

        if oi_val is not None:
            row("持仓量OI", _fmt_big(oi_val), COLORS['ai_accent'])
        if oi_delta is not None:
            row("OI 1h变化", f"{float(oi_delta):+.2f}%", COLORS['up'] if float(oi_delta) >= 0 else COLORS['down'])

        if ob:
            bid_notional = sum(p * a for p, a in ob.get("bids", [])[:10])
            ask_notional = sum(p * a for p, a in ob.get("asks", [])[:10])
            total = bid_notional + ask_notional
            if total > 0:
                ratio = bid_notional / total
                row("盘口比例", f"{ratio*100:.1f}% 买盘", COLORS['up'] if ratio >= 0.5 else COLORS['down'])

        # 清算分析部分已删除，为图表腾出更多空间

        # --- E. CAPITAL FLOW ---
        ax_flow.add_patch(mpatches.FancyBboxPatch((0,0), 1, 1, boxstyle="round,pad=0,rounding_size=0.04", fc=COLORS['panel'], alpha=0.7, transform=ax_flow.transAxes))
        ax_flow.text(0.02, 0.85, "资金流入/流出", color=COLORS['ai_accent'], fontsize=10, fontweight='bold', transform=ax_flow.transAxes)
        cols = [0.05, 0.22, 0.40, 0.58, 0.76]; hdrs = ["周期", "流入", "流出", "净流", "强度"]
        for i, h in enumerate(hdrs): ax_flow.text(cols[i], 0.68, h, color=COLORS['text_dim'], fontsize=8, fontweight='bold', transform=ax_flow.transAxes)
            
        flow_periods = ['15m', '1h', '4h', '24h']
        f_data = {}
        flow_source = "Binance"
        if vs_flow:
            flow_periods = ['1h', '4h', '12h', '24h']
            flow_source = "ValuScan"
            for p in flow_periods:
                data = vs_flow.get(p)
                if not isinstance(data, dict):
                    continue
                ratio = data.get('ratio')
                if ratio is None:
                    ratio = 0.5
                f_data[p] = {
                    'in': float(data.get('in', 0) or 0),
                    'out': float(data.get('out', 0) or 0),
                    'net': float(data.get('net', 0) or 0),
                    'ratio': float(ratio),
                }
        elif taker_flow:
            for i, p in enumerate(flow_periods):
                if i < len(taker_flow):
                    r = float(taker_flow[i].get('buySellRatio', 1))
                    vol = float(taker_flow[i].get('buyVol', 0)) * curr_p
                    inf = vol * (r / (1 + r)) if r >= 0 else 0
                    out = max(vol - inf, 0)
                    f_data[p] = {'in': inf, 'out': out, 'net': inf - out, 'ratio': inf / (inf + out) if inf + out > 0 else 0.5}

        ax_flow.text(0.88, 0.85, flow_source, color=COLORS['text_dim'], fontsize=8, transform=ax_flow.transAxes)

        ry = 0.48
        for p in flow_periods:
            d = f_data.get(p, {'in':0, 'out':0, 'net':0, 'ratio':0.5})
            ax_flow.text(cols[0], ry, f"{p.upper()}", color='white', fontweight='bold', fontsize=9, transform=ax_flow.transAxes)
            in_txt = _fmt_flow_amount(d['in'])
            out_txt = _fmt_flow_amount(d['out'])
            net_txt = _fmt_flow_amount(d['net'])
            if net_txt != "N/A" and not str(net_txt).startswith('-'):
                net_txt = f"+{net_txt}"
            ax_flow.text(cols[1], ry, f"${in_txt}", color=COLORS['up'], family='monospace', fontsize=9, transform=ax_flow.transAxes)
            ax_flow.text(cols[2], ry, f"${out_txt}", color=COLORS['down'], family='monospace', fontsize=9, transform=ax_flow.transAxes)
            c_n = COLORS['up'] if d['net']>0 else COLORS['down']
            ax_flow.text(cols[3], ry, f"{net_txt}", color=c_n, fontweight='bold', family='monospace', fontsize=9, transform=ax_flow.transAxes)
            bx, bw = cols[4], 0.18; r = d['ratio']
            ax_flow.add_patch(mpatches.Rectangle((bx, ry), bw*r, 0.03, fc=COLORS['up'], transform=ax_flow.transAxes))
            ax_flow.add_patch(mpatches.Rectangle((bx+bw*r, ry), bw*(1-r), 0.03, fc=COLORS['down'], transform=ax_flow.transAxes, alpha=0.3))
            ry -= 0.14

        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=dpi, facecolor=COLORS['bg_bot'], bbox_inches=None, pad_inches=0)
        buf.seek(0); img_d = buf.read(); buf.close(); plt.close(fig)
        cl.log_complete(len(img_d)); return img_d

    except Exception as e:
        cl.log_error(str(e), e); return None

if __name__ == '__main__':
    test_symbol = 'BTC'
    print(f"Generating Quantum Omni-Intelligence Chart for {test_symbol}...")
    img = generate_chart_v10(test_symbol)
    if img:
        with open(f'output/chart_omni_v20_{test_symbol}.png', 'wb') as f: f.write(img)
        print(f"Success: output/chart_omni_v20_{test_symbol}.png")
