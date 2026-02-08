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
from data_cleaner import clean_ohlcv_dataframe
from key_levels_enhanced import find_key_levels_enhanced, check_confluence
from ai_market_analysis import get_ai_market_analysis
from auxiliary_line_drawer import draw_auxiliary_lines_optimized
from ai_key_levels_cache import get_levels as get_ai_levels
from ai_market_summary import (
    get_ai_summary_config,
    get_ai_overlays_config,
    get_ai_market_config,
)
from chart_fonts import configure_matplotlib_fonts
from market_data_sources import fetch_market_snapshot

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
    try:
        r = requests.get(url, params=params, headers=headers, timeout=10)
        return r.json() if r.status_code == 200 else None
    except: return None


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


def _normalize_profile(values):
    if values is None:
        return None
    arr = np.asarray(values, dtype=float)
    if arr.size == 0:
        return None
    max_v = float(np.nanmax(arr))
    if not np.isfinite(max_v) or max_v <= 0:
        return None
    return arr / max_v


def _build_liquidity_heatmap(
    df,
    p_min,
    p_max,
    ob,
    ai_lvls,
    level_points,
    level_strengths,
    atr,
    bin_count=120,
):
    bins = np.linspace(p_min, p_max, bin_count)
    centers = (bins[:-1] + bins[1:]) / 2.0

    typical_price = (df["high"] + df["low"] + df["close"]) / 3.0
    vol_profile = np.histogram(typical_price, bins=bins, weights=df["volume"])[0]
    vol_profile = _normalize_profile(vol_profile)

    touch_profile = None
    highs = df["high"].values
    lows = df["low"].values
    volumes = df["volume"].values
    if highs.size and lows.size and volumes.size:
        touch_prices = np.concatenate([highs, lows])
        touch_weights = np.concatenate([volumes, volumes])
        touch_profile = np.histogram(touch_prices, bins=bins, weights=touch_weights)[0]
        touch_profile = _normalize_profile(touch_profile)

    ob_profile = None
    if isinstance(ob, dict):
        prices = []
        weights = []
        for side in ("bids", "asks"):
            for price, amount in ob.get(side, []) or []:
                try:
                    price_f = float(price)
                    amount_f = float(amount)
                except Exception:
                    continue
                prices.append(price_f)
                weights.append(price_f * amount_f)
        if prices:
            ob_profile = np.histogram(prices, bins=bins, weights=weights)[0]
            ob_profile = _normalize_profile(ob_profile)

    level_profile = None
    level_bumps = np.zeros_like(centers)
    sigma = max((atr or 0) * 0.9, (p_max - p_min) * 0.01, 1e-6)
    if level_points:
        for idx, level in enumerate(level_points):
            try:
                lvl = float(level)
            except Exception:
                continue
            weight = 0.45
            if level_strengths and idx < len(level_strengths):
                try:
                    weight = max(0.2, min(float(level_strengths[idx]), 1.0))
                except Exception:
                    pass
            level_bumps += weight * np.exp(-0.5 * ((centers - lvl) / sigma) ** 2)

    if isinstance(ai_lvls, dict):
        for key in ("supports", "resistances"):
            for lvl in ai_lvls.get(key, []) or []:
                try:
                    lvl_f = float(lvl)
                except Exception:
                    continue
                level_bumps += 0.35 * np.exp(-0.5 * ((centers - lvl_f) / sigma) ** 2)

    if np.any(level_bumps > 0):
        level_profile = _normalize_profile(level_bumps)

    profiles = []
    weights = []
    if vol_profile is not None:
        profiles.append(vol_profile)
        weights.append(0.45)
    if ob_profile is not None:
        profiles.append(ob_profile)
        weights.append(0.25)
    if touch_profile is not None:
        profiles.append(touch_profile)
        weights.append(0.15)
    if level_profile is not None:
        profiles.append(level_profile)
        weights.append(0.15)

    if not profiles:
        return np.zeros_like(centers), bins

    weight_sum = sum(weights) or 1.0
    combined = np.zeros_like(centers)
    for weight, profile in zip(weights, profiles):
        combined += profile * (weight / weight_sum)

    combined = gaussian_filter1d(combined, 1.2)
    normalized = _normalize_profile(combined)
    if normalized is None:
        normalized = np.zeros_like(centers)
    return normalized, bins

def get_integrated_data(symbol, interval):
    base = symbol.upper().replace('$', '').replace('USDT', '').strip()
    fs = f"{base}USDT"
    
    # 1. Primary Market
    k_raw = _req(f"{BINANCE_FUT_BASE}/fapi/v1/klines", {'symbol': fs, 'interval': interval, 'limit': 200})
    if not k_raw: return None
    df = pd.DataFrame(
        k_raw,
        columns=['timestamp','open','high','low','close','volume','ct','qv','t','tbb','tbq','i'],
    ).iloc[:, :6]
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
    for c in df.columns[1:]:
        df[c] = df[c].astype(float)
    df = clean_ohlcv_dataframe(df, interval, base, fill_missing=True, drop_incomplete=True)
    if df is None or df.empty:
        return None
    
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
    
    taker_flow = _req(f"{BINANCE_FUT_BASE}/futures/data/takerlongshortRatio", {'symbol': fs, 'period': '15m', 'limit': 24})
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
        'df': df, 'tick': tick, 'fund': fund, 'oi': oi_stats, 'taker_flow': taker_flow,
        'liq': liq_stats, 'ls': ls_hist, 'ai_lvls': ai_lvls,
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
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
    for c in df.columns[1:]:
        df[c] = df[c].astype(float)
    cleaned = clean_ohlcv_dataframe(df, timeframe, base, fill_missing=True, drop_incomplete=True)
    return cleaned


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

# ==================== Core UI Components ====================

def draw_glow_line(ax, x, y, color, lw=1.2, ls='-', label=None):
    """高级发光线条渲染"""
    ax.plot(x, y, color=color, lw=lw, ls=ls, alpha=0.9, zorder=5)
    ax.plot(x, y, color=color, lw=lw*4, alpha=0.15, zorder=4) # Glow layer
    if label:
        ax.text(x[-1], y[-1], f" {label}", color=color, fontsize=8, fontweight='bold', va='center')

def generate_chart_v10(symbol, interval='1h', limit=200):
    cl = ChartGenerationLogger(symbol); cl.log_start()
    try:
        # Step 1: Accurate Docking
        data = get_integrated_data(symbol, interval)
        if not data: return None
        df, tick, fund, oi_stats, taker_flow, liq, ls_hist, ai_lvls, ob = data.values()
        
        curr_p = df['close'].iloc[-1]; atr = (df['high'] - df['low']).rolling(14).mean().iloc[-1]
        df['ema20'] = df['close'].ewm(span=20).mean()
        df['ema50'] = df['close'].ewm(span=50).mean()
        df['vwap'] = ((df['high']+df['low']+df['close'])/3 * df['volume']).cumsum() / df['volume'].cumsum()
        
        # Step 2: Workspace Setup
        selected_fonts = configure_matplotlib_fonts([
            'Microsoft YaHei',
            'SimHei',
            'WenQuanYi Micro Hei',
            'Noto Sans CJK SC',
            'Noto Sans CJK',
            'Noto Sans',
            'DejaVu Sans',
            'Arial',
        ]) or []
        cjk_fonts = {
            'Microsoft YaHei',
            'SimHei',
            'WenQuanYi Micro Hei',
            'Noto Sans CJK SC',
            'Noto Sans CJK',
            'PingFang SC',
        }
        has_cjk_font = any(font in cjk_fonts for font in selected_fonts)
        labels = {
            "change_24h": ("24H涨跌", "24H Change"),
            "high_24h": ("24H最高", "24H High"),
            "low_24h": ("24H最低", "24H Low"),
            "volume_24h": ("24H成交额", "24H Volume"),
            "open_24h": ("24H开盘", "24H Open"),
            "long_short_ratio": ("多空比", "Long/Short Ratio"),
            "funding_rate": ("资金费率", "Funding Rate"),
            "open_interest": ("持仓量OI", "Open Interest"),
            "oi_change_1h": ("OI 1h变化", "OI 1h Change"),
            "orderbook_bias": ("盘口比例", "Orderbook Bias"),
            "buy_side": ("买盘", "Buy Side"),
            "flow_title": ("资金流入/流出", "Capital Flow In/Out"),
            "period": ("周期", "Period"),
            "inflow": ("流入", "Inflow"),
            "outflow": ("流出", "Outflow"),
            "netflow": ("净流", "Net Flow"),
            "strength": ("强度", "Strength"),
        }

        def _label(key):
            zh, en = labels[key]
            return zh if has_cjk_font else en
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

        # --- B. AUXILIARY LINE SYSTEM (AI + LOCAL) ---
        # 从 JSON 配置文件读取 AI 模块启用状态
        try:
            from ai_key_levels_config import get_ai_levels_config
            ai_levels_cfg = get_ai_levels_config()
            enable_ai_key_levels = ai_levels_cfg.get("enabled", False)
        except Exception:
            enable_ai_key_levels = False
        
        try:
            ai_overlays_cfg = get_ai_overlays_config()
            enable_ai_overlays = ai_overlays_cfg.get("enabled", False)
        except Exception:
            enable_ai_overlays = False
        
        ai_lvls_for_fallback = ai_lvls
        if not enable_ai_key_levels:
            ai_lvls = None
        logger.info(f"[AI Config] Key Levels: {enable_ai_key_levels}, Overlays: {enable_ai_overlays}")

        # 1. Key Levels - 使用新的AI主力位系统
        # 导入新的AI主力位模块
        try:
            from key_levels_ai import find_ai_key_levels, LevelStrength
        except ImportError:
            find_ai_key_levels = None
            LevelStrength = None

        level_result = None
        s_list = []
        r_list = []
        level_meta = {"source": "QUANT"}
        strong_supports = []
        strong_resistances = []
        weak_supports = []
        weak_resistances = []
        vs_level_list = []

        if find_ai_key_levels:
            # 使用新的AI主力位系统
            level_result = find_ai_key_levels(df, curr_p, ai_lvls_for_fallback, ob)
            s_list = [l.price for l in level_result.get('supports', [])]
            r_list = [l.price for l in level_result.get('resistances', [])]
            strong_supports = level_result.get('strong_supports', [])
            strong_resistances = level_result.get('strong_resistances', [])
            weak_supports = level_result.get('weak_supports', [])
            weak_resistances = level_result.get('weak_resistances', [])
            level_meta = level_result.get('metadata', {"source": "AI"})
            level_meta['support_strengths'] = [l.strength for l in level_result.get('supports', [])]
            level_meta['resistance_strengths'] = [l.strength for l in level_result.get('resistances', [])]
            logger.info("[AI Levels] Found %d supports (%d strong), %d resistances (%d strong)",
                       len(s_list), len(strong_supports), len(r_list), len(strong_resistances))
        else:
            # 回退到增强版算法
            s_list, r_list, level_meta = find_key_levels_enhanced(
                df, curr_p, ob, market_cap=None,
                ai_levels=ai_lvls_for_fallback
            )

        # 过滤在价格范围内的主力位
        s_list = [p for p in s_list if p_min <= p <= p_max]
        r_list = [p for p in r_list if p_min <= p <= p_max]

        # --- A. HEATMAP Strip (Liquidity Density) ---
        level_points = []
        level_strengths = []
        if s_list:
            support_strengths = level_meta.get("support_strengths", [None] * len(s_list))
            for i, level in enumerate(s_list):
                level_points.append(level)
                strength = support_strengths[i] if i < len(support_strengths) else None
                level_strengths.append(strength)
        if r_list:
            resistance_strengths = level_meta.get("resistance_strengths", [None] * len(r_list))
            for i, level in enumerate(r_list):
                level_points.append(level)
                strength = resistance_strengths[i] if i < len(resistance_strengths) else None
                level_strengths.append(strength)
        if vs_level_list:
            for level in vs_level_list:
                level_points.append(level)
                level_strengths.append(0.35)

        heatmap, heat_bins = _build_liquidity_heatmap(
            df, p_min, p_max, ob, ai_lvls, level_points, level_strengths, atr
        )
        cmap_h = LinearSegmentedColormap.from_list('h', [COLORS['bg_top'], COLORS['ai_accent'], COLORS['vwap']])
        ax_heat.barh(
            heat_bins[:-1],
            heatmap,
            height=(heat_bins[1] - heat_bins[0]),
            color=[cmap_h(v) for v in heatmap],
            edgecolor='none',
            alpha=0.85,
        )
        ax_heat.set_ylim(ax_main.get_ylim()); ax_heat.invert_xaxis()

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

        def draw_key_line(p, c, label, source, strength=None, is_strong=False, is_weak=False):
            # 使用增强版汇合检测 - 动态阈值
            confluence_threshold = level_meta.get('confluence_threshold', 0.004)
            confluence_info = check_confluence(p, df, confluence_threshold)

            # 检查是否有汇合
            has_confluence = any(confluence_info.values())

            # 根据强弱等级调整样式
            if is_strong:
                # 强主力位 - 实线、粗线、高透明度
                base_lw, base_alpha = (2.0, 0.9)
                line_style = '-'
                label_prefix = "★"
            elif is_weak:
                # 弱主力位 - 虚线、细线、低透明度
                base_lw, base_alpha = (0.6, 0.4)
                line_style = ':'
                label_prefix = "○"
            elif strength and strength > 0.7:
                base_lw, base_alpha = (1.5, 0.85)
                line_style = '-'
                label_prefix = ""
            elif has_confluence:
                base_lw, base_alpha = (1.2, 0.75)
                line_style = '--'
                label_prefix = ""
            else:
                base_lw, base_alpha = (0.8, 0.55)
                line_style = '--'
                label_prefix = ""

            # 绘制主线
            ax_main.axhline(p, color=c, ls=line_style, lw=base_lw, alpha=base_alpha)

            # 构建标签
            tag = f"{label_prefix}{source}:{label}"
            if strength:
                tag += f" ({strength:.0%})"

            # 添加汇合指标标记
            conf_indicators = [k.upper() for k, v in confluence_info.items() if v]
            if conf_indicators:
                tag += f" [{','.join(conf_indicators)}]"

            # 绘制标签 (使用智能位置管理)
            fontweight = 'bold' if is_strong or (has_confluence and strength and strength > 0.6) else 'normal'
            label_x, label_y = label_manager.find_best_position(len(df)+20, p)
            ax_main.text(label_x, label_y, f"{tag} {p:,.2f}", color=c, fontsize=7,
                        va='center', ha='right', family='monospace', fontweight=fontweight)

        # 绘制主力位 - 区分强弱
        source = level_meta.get('source', 'AI')

        # 绘制强支撑位 (绿色实线)
        for level in strong_supports[:2]:
            p = level.price if hasattr(level, 'price') else level
            s = level.strength if hasattr(level, 'strength') else 0.8
            if p_min <= p <= p_max:
                draw_key_line(p, COLORS['up'], "SUP", source, s, is_strong=True)

        # 绘制强阻力位 (红色实线)
        for level in strong_resistances[:2]:
            p = level.price if hasattr(level, 'price') else level
            s = level.strength if hasattr(level, 'strength') else 0.8
            if p_min <= p <= p_max:
                draw_key_line(p, COLORS['down'], "RES", source, s, is_strong=True)

        # 绘制弱支撑位 (绿色虚线)
        for level in weak_supports[:1]:
            p = level.price if hasattr(level, 'price') else level
            s = level.strength if hasattr(level, 'strength') else 0.3
            if p_min <= p <= p_max:
                draw_key_line(p, COLORS['up'], "SUP", source, s, is_weak=True)

        # 绘制弱阻力位 (红色虚线)
        for level in weak_resistances[:1]:
            p = level.price if hasattr(level, 'price') else level
            s = level.strength if hasattr(level, 'strength') else 0.3
            if p_min <= p <= p_max:
                draw_key_line(p, COLORS['down'], "RES", source, s, is_weak=True)

        # 2. AI Market Analysis & Auxiliary Lines (New System)
        ai_analysis = None
        try:
            # 如果启用AI，进行全面市场分析
            if enable_ai_overlays:
                try:
                    ai_config = get_ai_market_config()
                    if ai_config and ai_config.get("api_key"):
                        import os
                        language = os.getenv("NOFX_LANGUAGE", "zh").lower()
                        logger.info(f"Calling AI for market analysis of {symbol}...")
                        ai_analysis = get_ai_market_analysis(
                            symbol, df, curr_p, ob, None, ai_config, language
                        )
                        if ai_analysis:
                            logger.info(f"AI analysis completed for {symbol}")
                except Exception as e:
                    logger.warning(f"AI market analysis failed: {e}")

            # 使用优化的辅助线绘制算法
            if isinstance(ai_analysis, dict):
                ai_analysis.pop("key_levels", None)
            auxiliary_lines = draw_auxiliary_lines_optimized(df, curr_p, atr, ai_analysis)

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
        ax_main.text(0, 1.02, f"{symbol.upper()}USDT - AI-QUANT OMNI - O:{o.iloc[-1]:.2f} H:{h.iloc[-1]:.2f} L:{l.iloc[-1]:.2f} C:{c.iloc[-1]:.2f}", transform=ax_main.transAxes, color=COLORS['text'], fontsize=10, family='monospace', fontweight='bold')
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
            row(_label("change_24h"), f"{float(tick['priceChangePercent']):+.2f}%", COLORS['up'] if float(tick['priceChangePercent'])>=0 else COLORS['down'])
            row(_label("high_24h"), f"{float(tick['highPrice']):,.2f}", COLORS['text'])
            row(_label("low_24h"), f"{float(tick['lowPrice']):,.2f}", COLORS['text'])
            row(_label("volume_24h"), _fmt_big(float(tick.get('quoteVolume', 0))), COLORS['text_dim'])
            row(_label("open_24h"), f"{float(tick.get('openPrice', 0)):,.2f}", COLORS['text_dim'])
        if ls_hist:
            row(_label("long_short_ratio"), f"{float(ls_hist[0]['longShortRatio']):.2f}", COLORS['gold'])
        if fund:
            row(_label("funding_rate"), f"{float(fund[0]['fundingRate'])*100:.4f}%", COLORS['ema50'])

        oi_val = None
        oi_delta = None
        if isinstance(oi_stats, dict):
            oi_val = oi_stats.get("current")
            oi_delta = oi_stats.get("delta_1h")

        if oi_val is not None:
            row(_label("open_interest"), _fmt_big(oi_val), COLORS['ai_accent'])
        if oi_delta is not None:
            row(_label("oi_change_1h"), f"{float(oi_delta):+.2f}%", COLORS['up'] if float(oi_delta) >= 0 else COLORS['down'])

        if ob:
            bid_notional = sum(p * a for p, a in ob.get("bids", [])[:10])
            ask_notional = sum(p * a for p, a in ob.get("asks", [])[:10])
            total = bid_notional + ask_notional
            if total > 0:
                ratio = bid_notional / total
                row(_label("orderbook_bias"), f"{ratio*100:.1f}% {_label('buy_side')}", COLORS['up'] if ratio >= 0.5 else COLORS['down'])

        # 清算分析部分已删除，为图表腾出更多空间

        # --- E. CAPITAL FLOW ---
        ax_flow.add_patch(mpatches.FancyBboxPatch((0,0), 1, 1, boxstyle="round,pad=0,rounding_size=0.04", fc=COLORS['panel'], alpha=0.7, transform=ax_flow.transAxes))
        ax_flow.text(0.02, 0.85, _label("flow_title"), color=COLORS['ai_accent'], fontsize=10, fontweight='bold', transform=ax_flow.transAxes)
        cols = [0.05, 0.22, 0.40, 0.58, 0.76]; hdrs = [_label("period"), _label("inflow"), _label("outflow"), _label("netflow"), _label("strength")]
        for i, h in enumerate(hdrs): ax_flow.text(cols[i], 0.68, h, color=COLORS['text_dim'], fontsize=8, fontweight='bold', transform=ax_flow.transAxes)
            
        # Unified Flow Processing (force Binance taker flow)
        f_data = {}
        if taker_flow:
            for i, p in enumerate(['15m', '1h', '4h', '24h']):
                if i < len(taker_flow):
                    r = float(taker_flow[i].get('buySellRatio', 1))
                    vol = float(taker_flow[i].get('buyVol', 0)) * curr_p
                    inf = vol * (r / (1 + r)) if r >= 0 else 0
                    out = max(vol - inf, 0)
                    f_data[p] = {'in': inf, 'out': out, 'net': inf - out, 'ratio': inf / (inf + out) if inf + out > 0 else 0.5}

        ry = 0.48
        for p in ['15m', '1h', '4h', '24h']:
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
        fig.savefig(buf, format='png', dpi=dpi, bbox_inches='tight', facecolor=COLORS['bg_bot'])
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
