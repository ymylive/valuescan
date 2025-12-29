"""
改进的主力关键位计算算法
基于专业量化交易理论：
1. Market Profile (TPO/POC)
2. Volume-Weighted Support/Resistance
3. Fractal Geometry
4. Order Flow Imbalance
5. VWAP Deviation Bands
"""

import numpy as np
import pandas as pd
from scipy.ndimage import gaussian_filter1d
from scipy.signal import find_peaks, argrelextrema


def calculate_vwap(df):
    """计算成交量加权平均价 (VWAP)"""
    typical_price = (df['high'] + df['low'] + df['close']) / 3
    vwap = (typical_price * df['volume']).cumsum() / df['volume'].cumsum()
    return vwap





def calculate_atr(df, period=14):
    """Average True Range (ATR) for adaptive thresholds."""
    high = df['high']
    low = df['low']
    close = df['close']
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def count_touches(df, level, tolerance):
    """Count how often price closes near a level (support/resistance strength)."""
    if df is None or df.empty:
        return 0
    close = df['close'].values
    return int(np.sum(np.abs(close - level) <= tolerance))


def find_volume_profile_peaks(volume_profile, price_levels, peak_min=0.25, max_peaks=6):
    """Extract prominent peaks from the volume profile."""
    if volume_profile is None or price_levels is None:
        return []
    if len(volume_profile) < 3:
        return []
    peak_idx, props = find_peaks(volume_profile, height=peak_min, distance=2)
    peaks = []
    for idx in peak_idx:
        peaks.append((price_levels[idx], float(volume_profile[idx]), 'VP_Peak'))
    peaks.sort(key=lambda x: -x[1])
    return peaks[:max_peaks]


def find_poc_and_value_area(df, num_levels=100):
    """
    计算POC (Point of Control) 和价值区域
    POC: 成交量最大的价格水平
    Value Area: 包含70%成交量的价格区间
    """
    price_min = df['low'].min()
    price_max = df['high'].max()
    level_width = (price_max - price_min) / num_levels

    # 构建Volume Profile
    volume_profile = np.zeros(num_levels)
    price_levels = np.linspace(price_min, price_max, num_levels)

    for i in range(len(df)):
        low_idx = max(0, int((df['low'].iloc[i] - price_min) / level_width))
        high_idx = min(num_levels - 1, int((df['high'].iloc[i] - price_min) / level_width))
        if low_idx <= high_idx:
            # 使用TPO方法：每个K线在价格区间内的时间权重
            volume_profile[low_idx:high_idx+1] += df['volume'].iloc[i] / max(1, high_idx - low_idx + 1)

    # POC: 成交量最大的价格
    poc_idx = np.argmax(volume_profile)
    poc_price = price_levels[poc_idx]

    # Value Area: 70%成交量区间
    total_volume = volume_profile.sum()
    target_volume = total_volume * 0.70

    # 从POC向两边扩展，直到包含70%成交量
    sorted_indices = np.argsort(volume_profile)[::-1]
    cumsum = 0
    value_area_indices = []

    for idx in sorted_indices:
        cumsum += volume_profile[idx]
        value_area_indices.append(idx)
        if cumsum >= target_volume:
            break

    value_area_high = price_levels[max(value_area_indices)]
    value_area_low = price_levels[min(value_area_indices)]

    return poc_price, value_area_high, value_area_low, volume_profile, price_levels


def find_fractal_levels(df, order=5):
    """
    Williams Fractal 分形支撑阻力
    order: 左右各需要多少根K线来确认分形
    """
    highs = df['high'].values
    lows = df['low'].values

    fractal_highs = []
    fractal_lows = []

    for i in range(order, len(df) - order):
        # 分形高点：中间K线的高点是左右各order根K线中最高的
        is_fractal_high = all(highs[i] >= highs[i-j] for j in range(1, order+1)) and \
                          all(highs[i] >= highs[i+j] for j in range(1, order+1))

        # 分形低点：中间K线的低点是左右各order根K线中最低的
        is_fractal_low = all(lows[i] <= lows[i-j] for j in range(1, order+1)) and \
                         all(lows[i] <= lows[i+j] for j in range(1, order+1))

        if is_fractal_high:
            fractal_highs.append((i, highs[i]))
        if is_fractal_low:
            fractal_lows.append((i, lows[i]))

    return fractal_highs, fractal_lows





def find_swing_levels(df, min_prominence):
    """Detect swing highs/lows using adaptive prominence."""
    highs = df['high'].values
    lows = df['low'].values
    if len(highs) < 10 or len(lows) < 10:
        return [], []

    prom = min_prominence if min_prominence > 0 else 0
    swing_high_idx, _ = find_peaks(highs, prominence=prom, distance=3)
    swing_low_idx, _ = find_peaks(-lows, prominence=prom, distance=3)

    swing_highs = [(int(i), float(highs[i])) for i in swing_high_idx]
    swing_lows = [(int(i), float(lows[i])) for i in swing_low_idx]
    return swing_highs, swing_lows



def volume_spike_levels(df, z_threshold=1.5, lookback=120):
    """Use volume spikes to propose levels from bar highs/lows."""
    if df is None or df.empty:
        return []
    recent = df.tail(lookback)
    vols = recent['volume']
    if vols.std() == 0:
        return []
    z = (vols - vols.mean()) / vols.std()
    spike_idx = recent.index[z > z_threshold]
    levels = []
    for idx in spike_idx:
        row = df.loc[idx]
        levels.append(float(row['high']))
        levels.append(float(row['low']))
    return levels


def calculate_order_flow_imbalance(orderbook, current_price):
    """
    订单流失衡分析
    识别买卖盘力量失衡的价格区域
    """
    if not orderbook or 'bids' not in orderbook or 'asks' not in orderbook:
        return [], []

    bids = orderbook.get('bids', [])
    asks = orderbook.get('asks', [])

    if not bids or not asks:
        return [], []

    # 计算每个价格档位的订单金额
    bid_levels = [(price, price * amount) for price, amount in bids[:20]]
    ask_levels = [(price, price * amount) for price, amount in asks[:20]]

    # 识别大单（超过平均值2倍）
    bid_amounts = [amt for _, amt in bid_levels]
    ask_amounts = [amt for _, amt in ask_levels]

    bid_mean = np.mean(bid_amounts) if bid_amounts else 0
    ask_mean = np.mean(ask_amounts) if ask_amounts else 0

    strong_bids = [(price, amt) for price, amt in bid_levels if amt > bid_mean * 2]
    strong_asks = [(price, amt) for price, amt in ask_levels if amt > ask_mean * 2]

    return strong_bids, strong_asks


def get_adaptive_params(current_price, market_cap, df):
    """
    根据币种特征自适应调整参数
    返回: (threshold_pct, num_levels, fractal_order)
    """
    # Normalize market_cap to a numeric value.
    if isinstance(market_cap, dict):
        market_cap = market_cap.get('usd') or market_cap.get('USD')
    if isinstance(market_cap, str):
        try:
            market_cap = float(market_cap)
        except ValueError:
            market_cap = None
    if not isinstance(market_cap, (int, float)):
        market_cap = None

    # 计算波动率 (ATR%)
    high_low = df['high'] - df['low']
    atr = high_low.rolling(14).mean().iloc[-1]
    volatility = (atr / current_price) * 100  # 转换为百分比

    # 基础参数
    if current_price > 10000:  # BTC级别
        base_threshold = 0.005
        base_levels = 120
        base_order = 5
    elif current_price > 1000:  # ETH级别
        base_threshold = 0.008
        base_levels = 100
        base_order = 5
    elif current_price > 10:  # 中等币
        base_threshold = 0.015
        base_levels = 80
        base_order = 4
    elif current_price > 0.1:  # 小币
        base_threshold = 0.025
        base_levels = 60
        base_order = 3
    else:  # 极小币
        base_threshold = 0.04
        base_levels = 50
        base_order = 3

    # 根据市值调整
    if market_cap:
        if market_cap > 100e9:  # >1000亿
            base_threshold *= 0.7
            base_levels = int(base_levels * 1.2)
        elif market_cap > 10e9:  # >100亿
            base_threshold *= 0.85
            base_levels = int(base_levels * 1.1)
        elif market_cap < 100e6:  # <1亿
            base_threshold *= 1.3
            base_levels = int(base_levels * 0.8)

    # 根据波动率调整
    if volatility > 10:  # 高波动
        base_threshold *= 1.2
        base_order = max(3, base_order - 1)
    elif volatility < 2:  # 低波动
        base_threshold *= 0.8
        base_order = min(7, base_order + 1)

    return base_threshold, base_levels, base_order


def find_key_levels_professional(df, current_price, orderbook=None, market_cap=None):
    """
    Professional key levels algorithm.
    Returns: (supports, resistances)
    """
    if df is None or df.empty or len(df) < 30:
        return [], []

    # 0) adaptive params
    threshold_pct, num_levels, fractal_order = get_adaptive_params(current_price, market_cap, df)
    atr = calculate_atr(df)
    atr_last = float(atr.iloc[-1]) if not atr.isna().all() else 0.0
    atr_pct = (atr_last / current_price) if current_price else 0.0
    min_distance = max(threshold_pct, atr_pct * 0.5, 0.001)
    merge_threshold = min(max(threshold_pct, atr_pct * 0.8, 0.001), 0.12)
    touch_tolerance = max(atr_last * 0.5, current_price * min_distance * 0.5, 1e-9)

    # 1) Market Profile
    poc_price, va_high, va_low, volume_profile, price_levels = find_poc_and_value_area(df, num_levels)
    vp_peaks = find_volume_profile_peaks(volume_profile, price_levels, peak_min=0.25, max_peaks=6)

    # 2) Fractals
    fractal_highs, fractal_lows = find_fractal_levels(df, order=fractal_order)

    # 3) Order flow
    strong_bids, strong_asks = calculate_order_flow_imbalance(orderbook, current_price)

    # 4) VWAP bands
    vwap = calculate_vwap(df)
    current_vwap = vwap.iloc[-1]
    vwap_std = (df['close'] - vwap).rolling(30).std().iloc[-1]
    vwap_std = float(vwap_std) if not np.isnan(vwap_std) else 0.0

    # 5) Swing + volume spikes
    prominence = max(atr_last * 0.8, current_price * min_distance)
    swing_highs, swing_lows = find_swing_levels(df, prominence)
    spike_levels = volume_spike_levels(df, z_threshold=1.3)

    support_candidates = []
    resistance_candidates = []

    # 6.1 POC (highest weight)
    if poc_price < current_price * (1 - min_distance):
        support_candidates.append((poc_price, 1.2, 'POC'))
    elif poc_price > current_price * (1 + min_distance):
        resistance_candidates.append((poc_price, 1.2, 'POC'))

    # 6.2 Value Area bounds
    if va_low < current_price * (1 - min_distance):
        support_candidates.append((va_low, 0.9, 'VA_Low'))
    if va_high > current_price * (1 + min_distance):
        resistance_candidates.append((va_high, 0.9, 'VA_High'))

    # 6.2.1 Volume profile peaks
    for price, strength, _ in vp_peaks:
        if price < current_price * (1 - min_distance):
            support_candidates.append((price, 0.75 + 0.2 * strength, 'VP_Peak'))
        elif price > current_price * (1 + min_distance):
            resistance_candidates.append((price, 0.75 + 0.2 * strength, 'VP_Peak'))

    # 6.3 Fractals (recent is heavier)
    for idx, price in fractal_lows[-5:]:
        if price < current_price * (1 - min_distance):
            weight = 0.6 + 0.2 * (idx / len(df))
            support_candidates.append((price, weight, 'Fractal'))

    for idx, price in fractal_highs[-5:]:
        if price > current_price * (1 + min_distance):
            weight = 0.6 + 0.2 * (idx / len(df))
            resistance_candidates.append((price, weight, 'Fractal'))

    # 6.4 Order flow
    for price, amt in strong_bids:
        if price < current_price * (1 - min_distance):
            support_candidates.append((price, 0.7, 'OrderFlow'))

    for price, amt in strong_asks:
        if price > current_price * (1 + min_distance):
            resistance_candidates.append((price, 0.7, 'OrderFlow'))

    # 6.5 Swing highs/lows
    for idx, price in swing_lows[-6:]:
        if price < current_price * (1 - min_distance):
            weight = 0.7 + 0.2 * (idx / len(df))
            support_candidates.append((price, weight, 'Swing'))

    for idx, price in swing_highs[-6:]:
        if price > current_price * (1 + min_distance):
            weight = 0.7 + 0.2 * (idx / len(df))
            resistance_candidates.append((price, weight, 'Swing'))

    # 6.6 Volume spike levels
    for price in spike_levels:
        if price < current_price * (1 - min_distance):
            support_candidates.append((price, 0.55, 'VolSpike'))
        elif price > current_price * (1 + min_distance):
            resistance_candidates.append((price, 0.55, 'VolSpike'))

    # 6.7 VWAP deviation bands
    if vwap_std > 0:
        vwap_bands = [
            current_vwap - vwap_std,
            current_vwap - 2 * vwap_std,
            current_vwap + vwap_std,
            current_vwap + 2 * vwap_std,
        ]
        for band in vwap_bands:
            if band < current_price * (1 - min_distance):
                support_candidates.append((band, 0.6, 'VWAP'))
            elif band > current_price * (1 + min_distance):
                resistance_candidates.append((band, 0.6, 'VWAP'))

    # 7) Merge nearby levels
    def merge_nearby_levels(candidates, merge_threshold):
        if not candidates:
            return []
        sorted_candidates = sorted(candidates, key=lambda x: x[0])
        merged = []
        current_group = [sorted_candidates[0]]

        for i in range(1, len(sorted_candidates)):
            price, weight, source = sorted_candidates[i]
            last_price = current_group[-1][0]
            if abs(price - last_price) / last_price < merge_threshold:
                current_group.append((price, weight, source))
            else:
                avg_price = sum(p * w for p, w, _ in current_group) / sum(w for _, w, _ in current_group)
                total_weight = sum(w for _, w, _ in current_group)
                merged.append((avg_price, total_weight))
                current_group = [(price, weight, source)]

        if current_group:
            avg_price = sum(p * w for p, w, _ in current_group) / sum(w for _, w, _ in current_group)
            total_weight = sum(w for _, w, _ in current_group)
            merged.append((avg_price, total_weight))

        return merged

    merged_supports = merge_nearby_levels(support_candidates, merge_threshold)
    merged_resistances = merge_nearby_levels(resistance_candidates, merge_threshold)

    # 7.1 Touch count weighting (refine strength)
    def apply_touch_weight(levels):
        refined = []
        for price, weight in levels:
            touches = count_touches(df, price, touch_tolerance)
            touch_score = min(1.0, touches / 5.0)
            refined.append((price, weight * (1 + 0.25 * touch_score)))
        return refined

    merged_supports = apply_touch_weight(merged_supports)
    merged_resistances = apply_touch_weight(merged_resistances)

    merged_supports.sort(key=lambda x: -x[1])
    merged_resistances.sort(key=lambda x: -x[1])

    final_supports = [price for price, _ in merged_supports[:3]]
    final_resistances = [price for price, _ in merged_resistances[:3]]

    # Fallback to recent extremes if needed.
    if not final_supports:
        final_supports = [float(df['low'].tail(50).min())]
    if not final_resistances:
        final_resistances = [float(df['high'].tail(50).max())]

    return final_supports, final_resistances
