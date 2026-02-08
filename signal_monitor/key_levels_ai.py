"""
专业化AI主力位计算模块
核心特性：
1. AI主力位优先 - 使用AI分析作为主要数据源
2. 强弱分级系统 - 区分强力/中等/弱支撑阻力
3. 多因子验证 - 成交量、触碰、时间、汇合等
4. 动态自适应 - 根据波动率调整阈值
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum


class LevelStrength(Enum):
    """主力位强度等级"""
    STRONG = "strong"      # 强力位 (0.7-1.0)
    MEDIUM = "medium"      # 中等位 (0.4-0.7)
    WEAK = "weak"          # 弱位 (0.2-0.4)


@dataclass
class KeyLevel:
    """主力位数据结构"""
    price: float
    strength: float  # 0-1
    level_type: str  # 'support' or 'resistance'
    strength_grade: LevelStrength
    sources: List[str]  # 来源: AI, POC, Fractal, Volume等
    confluence: Dict[str, bool]  # 汇合指标
    touches: int  # 触碰次数
    last_touch_idx: int  # 最近触碰位置


def calculate_atr(df: pd.DataFrame, period: int = 14) -> float:
    """计算ATR"""
    if df is None or len(df) < period:
        return 0.0
    high = df['high']
    low = df['low']
    close = df['close']
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)
    atr = tr.rolling(period).mean().iloc[-1]
    return float(atr) if not pd.isna(atr) else 0.0


def calculate_vwap(df: pd.DataFrame) -> pd.Series:
    """计算VWAP"""
    typical_price = (df['high'] + df['low'] + df['close']) / 3
    return (typical_price * df['volume']).cumsum() / df['volume'].cumsum()


def _normalize_market_cap(market_cap: Optional[float]) -> Optional[float]:
    if isinstance(market_cap, dict):
        market_cap = market_cap.get('usd') or market_cap.get('USD')
    if isinstance(market_cap, str):
        try:
            market_cap = float(market_cap)
        except ValueError:
            market_cap = None
    if isinstance(market_cap, (int, float)):
        return float(market_cap)
    return None


def get_dynamic_thresholds(
    df: pd.DataFrame,
    current_price: float,
    market_cap: Optional[float] = None,
) -> Dict[str, float]:
    """Dynamic thresholds based on recent volatility and liquidity."""
    atr = calculate_atr(df)
    atr_pct = atr / current_price if current_price > 0 else 0.01

    recent_vol = (df['high'].tail(20) - df['low'].tail(20)).mean() / current_price
    vol_factor = max(0.5, min(2.0, (atr_pct + recent_vol) / 0.02))

    cap = _normalize_market_cap(market_cap)
    if cap:
        if cap > 50e9:
            vol_factor *= 0.85
        elif cap < 200e6:
            vol_factor *= 1.15
    vol_factor = max(0.4, min(2.2, vol_factor))

    min_distance = max(0.004 * vol_factor, atr_pct * 0.6)

    return {
        'merge_threshold': 0.008 * vol_factor,
        'touch_tolerance': 0.005 * vol_factor,
        'confluence_threshold': 0.003 * vol_factor,
        'min_distance': min_distance,
    }

def count_level_touches(df: pd.DataFrame, level: float, tolerance: float) -> Tuple[int, int]:
    """
    统计触碰次数和最近触碰位置
    返回: (触碰次数, 最近触碰索引)
    """
    touches = 0
    last_touch = -1

    for i in range(len(df)):
        high = df['high'].iloc[i]
        low = df['low'].iloc[i]

        if abs(high - level) / level <= tolerance or abs(low - level) / level <= tolerance:
            touches += 1
            last_touch = i

    return touches, last_touch


def check_level_confluence(level: float, df: pd.DataFrame, threshold: float) -> Dict[str, bool]:
    """
    检查主力位与技术指标的汇合
    """
    confluence = {
        'ema20': False,
        'ema50': False,
        'ema200': False,
        'vwap': False,
        'round_number': False,
    }

    # EMA计算
    ema20 = df['close'].ewm(span=20, adjust=False).mean().iloc[-1]
    ema50 = df['close'].ewm(span=50, adjust=False).mean().iloc[-1]

    if abs(ema20 - level) / level < threshold:
        confluence['ema20'] = True
    if abs(ema50 - level) / level < threshold:
        confluence['ema50'] = True

    if len(df) >= 200:
        ema200 = df['close'].ewm(span=200, adjust=False).mean().iloc[-1]
        if abs(ema200 - level) / level < threshold:
            confluence['ema200'] = True

    # VWAP
    vwap = calculate_vwap(df).iloc[-1]
    if not pd.isna(vwap) and abs(vwap - level) / level < threshold:
        confluence['vwap'] = True

    # 整数关口检测
    if level > 100:
        round_levels = [round(level, -2), round(level, -3)]  # 百位、千位
        for rl in round_levels:
            if abs(rl - level) / level < threshold * 2:
                confluence['round_number'] = True
                break
    elif level > 1:
        if abs(round(level) - level) / level < threshold * 2:
            confluence['round_number'] = True

    return confluence


def calculate_level_strength_score(
    level: float,
    df: pd.DataFrame,
    current_price: float,
    thresholds: Dict[str, float],
    source_weight: float = 1.0,
    is_ai_source: bool = False
) -> Tuple[float, Dict[str, Any]]:
    """
    计算主力位强度得分 (0-1)

    评分因子：
    1. 触碰次数 (25%)
    2. 成交量集中度 (20%)
    3. 距离适中性 (15%)
    4. 汇合度 (20%)
    5. 来源权重 (10%)
    6. 时间衰减 (10%)
    """
    score = 0.0
    details = {}

    tolerance = thresholds['touch_tolerance']

    # 1. 触碰分析 (25%)
    touches, last_touch = count_level_touches(df, level, tolerance)
    touch_score = min(touches / 5.0, 1.0)  # 5次触碰为满分
    score += touch_score * 0.25
    details['touches'] = touches
    details['last_touch'] = last_touch
    details['touch_score'] = touch_score

    # 2. 成交量集中度 (20%)
    vol_score = 0.0
    for i in range(len(df)):
        high = df['high'].iloc[i]
        low = df['low'].iloc[i]
        if low <= level <= high:
            vol_score += df['volume'].iloc[i]

    total_vol = df['volume'].sum()
    vol_ratio = vol_score / total_vol if total_vol > 0 else 0
    vol_normalized = min(vol_ratio / 0.1, 1.0)  # 10%成交量集中为满分
    score += vol_normalized * 0.20
    details['volume_score'] = vol_normalized

    # 3. 距离适中性 (15%)
    distance_pct = abs(level - current_price) / current_price
    if 0.01 <= distance_pct <= 0.05:
        distance_score = 1.0
    elif distance_pct < 0.01:
        distance_score = distance_pct / 0.01
    else:
        distance_score = max(0, 1.0 - (distance_pct - 0.05) / 0.1)
    score += distance_score * 0.15
    details['distance_score'] = distance_score

    # 4. 汇合度 (20%)
    confluence = check_level_confluence(level, df, thresholds['confluence_threshold'])
    confluence_count = sum(confluence.values())
    confluence_score = min(confluence_count / 3.0, 1.0)  # 3个汇合为满分
    score += confluence_score * 0.20
    details['confluence'] = confluence
    details['confluence_score'] = confluence_score

    # 5. 来源权重 (10%)
    source_score = source_weight
    if is_ai_source:
        source_score = min(source_score * 1.2, 1.0)  # AI来源加成
    score += source_score * 0.10
    details['source_score'] = source_score

    # 6. 时间衰减 (10%)
    if last_touch >= 0:
        recency = (last_touch + 1) / len(df)
        time_score = recency
    else:
        time_score = 0.3  # 无触碰给基础分
    score += time_score * 0.10
    details['time_score'] = time_score

    return min(score, 1.0), details


def grade_strength(score: float) -> LevelStrength:
    """根据得分划分强度等级"""
    if score >= 0.7:
        return LevelStrength.STRONG
    elif score >= 0.4:
        return LevelStrength.MEDIUM
    else:
        return LevelStrength.WEAK


def find_ai_key_levels(
    df: pd.DataFrame,
    current_price: float,
    ai_levels: Optional[Dict[str, Any]] = None,
    orderbook: Optional[Dict] = None,
    market_cap: Optional[float] = None
) -> Dict[str, Any]:
    """
    专业化AI主力位查找

    返回:
    {
        'supports': [KeyLevel, ...],        # 支撑位列表
        'resistances': [KeyLevel, ...],     # 阻力位列表
        'strong_supports': [KeyLevel, ...], # 强支撑位
        'weak_supports': [KeyLevel, ...],   # 弱支撑位
        'strong_resistances': [KeyLevel, ...], # 强阻力位
        'weak_resistances': [KeyLevel, ...],   # 弱阻力位
        'metadata': {...}
    }
    """
    if df is None or df.empty or len(df) < 30:
        return _empty_result()

    thresholds = get_dynamic_thresholds(df, current_price, market_cap)

    support_candidates = []
    resistance_candidates = []

    # 1. AI主力位 (最高优先级)
    ai_confidence = 0.0
    if ai_levels and isinstance(ai_levels, dict):
        ai_supports = ai_levels.get('supports', [])
        ai_resistances = ai_levels.get('resistances', [])
        ai_meta = ai_levels.get('meta', {})
        ai_confidence = ai_meta.get('confidence', 0.8)

        for level in ai_supports:
            try:
                price = float(level)
                if price < current_price * (1 - thresholds['min_distance']):
                    support_candidates.append((price, 1.0, 'AI', True))
            except (TypeError, ValueError):
                continue

        for level in ai_resistances:
            try:
                price = float(level)
                if price > current_price * (1 + thresholds['min_distance']):
                    resistance_candidates.append((price, 1.0, 'AI', True))
            except (TypeError, ValueError):
                continue

    # 2. 量化补充 (当AI数据不足时)
    if len(support_candidates) < 2 or len(resistance_candidates) < 2:
        quant_levels = _find_quant_levels(df, current_price, thresholds, orderbook, market_cap)

        for price, weight, source in quant_levels['supports']:
            if not any(abs(p - price) / price < thresholds['merge_threshold'] for p, _, _, _ in support_candidates):
                support_candidates.append((price, weight, source, False))

        for price, weight, source in quant_levels['resistances']:
            if not any(abs(p - price) / price < thresholds['merge_threshold'] for p, _, _, _ in resistance_candidates):
                resistance_candidates.append((price, weight, source, False))

    # 3. 计算强度并创建KeyLevel对象
    supports = []
    for price, weight, source, is_ai in support_candidates:
        score, details = calculate_level_strength_score(
            price, df, current_price, thresholds, weight, is_ai
        )

        if score >= 0.2:  # 最低阈值
            level = KeyLevel(
                price=price,
                strength=score,
                level_type='support',
                strength_grade=grade_strength(score),
                sources=[source],
                confluence=details.get('confluence', {}),
                touches=details.get('touches', 0),
                last_touch_idx=details.get('last_touch', -1)
            )
            supports.append(level)

    resistances = []
    for price, weight, source, is_ai in resistance_candidates:
        score, details = calculate_level_strength_score(
            price, df, current_price, thresholds, weight, is_ai
        )

        if score >= 0.2:
            level = KeyLevel(
                price=price,
                strength=score,
                level_type='resistance',
                strength_grade=grade_strength(score),
                sources=[source],
                confluence=details.get('confluence', {}),
                touches=details.get('touches', 0),
                last_touch_idx=details.get('last_touch', -1)
            )
            resistances.append(level)

    # 4. 合并相近位置
    supports = _merge_nearby_levels(supports, thresholds['merge_threshold'])
    resistances = _merge_nearby_levels(resistances, thresholds['merge_threshold'])

    # 5. 按强度排序
    supports.sort(key=lambda x: -x.strength)
    resistances.sort(key=lambda x: -x.strength)

    # 6. 分类
    strong_supports = [l for l in supports if l.strength_grade == LevelStrength.STRONG]
    medium_supports = [l for l in supports if l.strength_grade == LevelStrength.MEDIUM]
    weak_supports = [l for l in supports if l.strength_grade == LevelStrength.WEAK]

    strong_resistances = [l for l in resistances if l.strength_grade == LevelStrength.STRONG]
    medium_resistances = [l for l in resistances if l.strength_grade == LevelStrength.MEDIUM]
    weak_resistances = [l for l in resistances if l.strength_grade == LevelStrength.WEAK]

    # 7. 限制数量
    supports = supports[:5]
    resistances = resistances[:5]

    return {
        'supports': supports,
        'resistances': resistances,
        'strong_supports': strong_supports[:2],
        'medium_supports': medium_supports[:2],
        'weak_supports': weak_supports[:2],
        'strong_resistances': strong_resistances[:2],
        'medium_resistances': medium_resistances[:2],
        'weak_resistances': weak_resistances[:2],
        'metadata': {
            'ai_confidence': ai_confidence,
            'source': 'AI' if ai_confidence > 0.5 else 'QUANT',
            'thresholds': thresholds,
            'total_supports': len(supports),
            'total_resistances': len(resistances),
        }
    }


def _find_quant_levels(
    df: pd.DataFrame,
    current_price: float,
    thresholds: Dict[str, float],
    orderbook: Optional[Dict] = None,
    market_cap: Optional[float] = None
) -> Dict[str, List[Tuple[float, float, str]]]:
    """Quant key level candidates from multiple data sources."""
    supports = []
    resistances = []
    min_dist = thresholds['min_distance']

    num_levels = _select_profile_levels(df, current_price, market_cap)
    poc, va_high, va_low, volume_profile, price_levels = _build_volume_profile(df, num_levels)

    if poc is not None:
        if poc < current_price * (1 - min_dist):
            supports.append((poc, 0.95, 'POC'))
        elif poc > current_price * (1 + min_dist):
            resistances.append((poc, 0.95, 'POC'))

    if va_low is not None and va_low < current_price * (1 - min_dist):
        supports.append((va_low, 0.85, 'VA_Low'))
    if va_high is not None and va_high > current_price * (1 + min_dist):
        resistances.append((va_high, 0.85, 'VA_High'))

    peaks = _find_volume_profile_peaks(volume_profile, price_levels, min_ratio=0.25, max_peaks=6)
    max_profile = float(np.max(volume_profile)) if volume_profile is not None and len(volume_profile) else 0.0
    for price, strength in peaks:
        ratio = strength / max_profile if max_profile > 0 else 0.0
        weight = 0.7 + 0.3 * min(1.0, ratio)
        if price < current_price * (1 - min_dist):
            supports.append((price, weight, 'VP_Peak'))
        elif price > current_price * (1 + min_dist):
            resistances.append((price, weight, 'VP_Peak'))

    fractal_highs, fractal_lows = _find_fractals(df)
    for price in fractal_lows[-4:]:
        if price < current_price * (1 - min_dist):
            supports.append((price, 0.7, 'Fractal'))
    for price in fractal_highs[-4:]:
        if price > current_price * (1 + min_dist):
            resistances.append((price, 0.7, 'Fractal'))

    swing_highs, swing_lows = _find_swing_levels(df, window=4)
    for idx, price in swing_lows[-5:]:
        if price < current_price * (1 - min_dist):
            weight = 0.65 + 0.2 * (idx / len(df))
            supports.append((price, weight, 'Swing'))
    for idx, price in swing_highs[-5:]:
        if price > current_price * (1 + min_dist):
            weight = 0.65 + 0.2 * (idx / len(df))
            resistances.append((price, weight, 'Swing'))

    if orderbook:
        ob_supports, ob_resistances = _find_orderbook_levels(orderbook, current_price, min_dist)
        supports.extend(ob_supports)
        resistances.extend(ob_resistances)

    lookback = min(160, len(df)) if df is not None else 120
    spike_levels = _find_volume_spike_levels(df, z_threshold=1.3, lookback=lookback)
    for price in spike_levels:
        if price < current_price * (1 - min_dist):
            supports.append((price, 0.55, 'VolSpike'))
        elif price > current_price * (1 + min_dist):
            resistances.append((price, 0.55, 'VolSpike'))

    indicator_levels = _get_indicator_levels(df)
    vwap_series = calculate_vwap(df)
    current_vwap = vwap_series.iloc[-1] if vwap_series is not None else None
    if current_vwap is not None and not pd.isna(current_vwap):
        indicator_levels.append(('VWAP', float(current_vwap)))

    indicator_weights = {
        'EMA20': 0.55,
        'EMA50': 0.6,
        'EMA100': 0.65,
        'EMA200': 0.7,
        'VWAP': 0.6,
    }
    for label, level in indicator_levels:
        if not level or pd.isna(level):
            continue
        weight = indicator_weights.get(label, 0.6)
        if level < current_price * (1 - min_dist):
            supports.append((level, weight, label))
        elif level > current_price * (1 + min_dist):
            resistances.append((level, weight, label))

    vwap_std = 0.0
    if vwap_series is not None:
        std_val = (df['close'] - vwap_series).rolling(30).std().iloc[-1]
        if not pd.isna(std_val):
            vwap_std = float(std_val)
    if current_vwap is not None and not pd.isna(current_vwap) and vwap_std > 0:
        bands = [
            float(current_vwap - vwap_std),
            float(current_vwap - 2 * vwap_std),
            float(current_vwap + vwap_std),
            float(current_vwap + 2 * vwap_std),
        ]
        for band in bands:
            if band < current_price * (1 - min_dist):
                supports.append((band, 0.6, 'VWAP_Band'))
            elif band > current_price * (1 + min_dist):
                resistances.append((band, 0.6, 'VWAP_Band'))

    for window, weight in [(20, 0.55), (50, 0.6), (120, 0.65)]:
        if len(df) >= window:
            recent_low = float(df['low'].tail(window).min())
            recent_high = float(df['high'].tail(window).max())
            if recent_low < current_price * (1 - min_dist):
                supports.append((recent_low, weight, f'RecentLow{window}'))
            if recent_high > current_price * (1 + min_dist):
                resistances.append((recent_high, weight, f'RecentHigh{window}'))

    return {'supports': supports, 'resistances': resistances}

def _select_profile_levels(df: pd.DataFrame, current_price: float, market_cap: Optional[float]) -> int:
    base = 100
    if current_price > 10000:
        base = 140
    elif current_price > 1000:
        base = 120
    elif current_price > 10:
        base = 100
    elif current_price > 1:
        base = 80
    else:
        base = 60

    cap = _normalize_market_cap(market_cap)
    if cap:
        if cap > 50e9:
            base = int(base * 1.15)
        elif cap < 200e6:
            base = int(base * 0.85)

    base = max(50, min(180, base))
    if df is not None and not df.empty:
        base = min(base, max(50, len(df)))
    return base


def _build_volume_profile(
    df: pd.DataFrame,
    num_levels: int = 120,
) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[np.ndarray], Optional[np.ndarray]]:
    if df is None or df.empty:
        return None, None, None, None, None

    price_min = df['low'].min()
    price_max = df['high'].max()
    level_width = (price_max - price_min) / max(1, num_levels)
    if level_width <= 0:
        return None, None, None, None, None

    volume_profile = np.zeros(num_levels)
    price_levels = np.linspace(price_min, price_max, num_levels)

    for i in range(len(df)):
        low_idx = max(0, int((df['low'].iloc[i] - price_min) / level_width))
        high_idx = min(num_levels - 1, int((df['high'].iloc[i] - price_min) / level_width))
        if low_idx <= high_idx:
            volume_profile[low_idx:high_idx + 1] += df['volume'].iloc[i] / max(1, high_idx - low_idx + 1)

    poc_idx = int(np.argmax(volume_profile))
    poc_price = float(price_levels[poc_idx])

    total_volume = float(volume_profile.sum())
    if total_volume <= 0:
        return poc_price, None, None, volume_profile, price_levels

    target_volume = total_volume * 0.70
    sorted_indices = np.argsort(volume_profile)[::-1]
    cumsum = 0.0
    value_area_indices = []
    for idx in sorted_indices:
        cumsum += float(volume_profile[idx])
        value_area_indices.append(int(idx))
        if cumsum >= target_volume:
            break

    if not value_area_indices:
        return poc_price, None, None, volume_profile, price_levels

    va_high = float(price_levels[max(value_area_indices)])
    va_low = float(price_levels[min(value_area_indices)])
    return poc_price, va_high, va_low, volume_profile, price_levels


def _find_volume_profile_peaks(
    volume_profile: Optional[np.ndarray],
    price_levels: Optional[np.ndarray],
    min_ratio: float = 0.25,
    max_peaks: int = 6,
) -> List[Tuple[float, float]]:
    if volume_profile is None or price_levels is None:
        return []
    if len(volume_profile) < 3:
        return []
    max_val = float(np.max(volume_profile))
    if max_val <= 0:
        return []
    threshold = max_val * min_ratio
    peaks = []
    for i in range(1, len(volume_profile) - 1):
        if volume_profile[i] >= volume_profile[i - 1] and volume_profile[i] >= volume_profile[i + 1] and volume_profile[i] >= threshold:
            peaks.append((float(price_levels[i]), float(volume_profile[i])))
    peaks.sort(key=lambda x: -x[1])
    return peaks[:max_peaks]


def _find_volume_spike_levels(
    df: pd.DataFrame,
    z_threshold: float = 1.3,
    lookback: int = 120,
) -> List[float]:
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


def _find_swing_levels(df: pd.DataFrame, window: int = 4) -> Tuple[List[Tuple[int, float]], List[Tuple[int, float]]]:
    if df is None or df.empty:
        return [], []
    if len(df) < window * 2 + 1:
        return [], []

    highs = df['high'].values
    lows = df['low'].values
    swing_highs = []
    swing_lows = []
    for i in range(window, len(df) - window):
        if highs[i] == highs[i - window:i + window + 1].max():
            swing_highs.append((i, float(highs[i])))
        if lows[i] == lows[i - window:i + window + 1].min():
            swing_lows.append((i, float(lows[i])))
    return swing_highs, swing_lows


def _get_indicator_levels(df: pd.DataFrame) -> List[Tuple[str, float]]:
    levels = []
    if df is None or df.empty:
        return levels
    close = df['close']
    if len(df) >= 20:
        levels.append(('EMA20', float(close.ewm(span=20, adjust=False).mean().iloc[-1])))
    if len(df) >= 50:
        levels.append(('EMA50', float(close.ewm(span=50, adjust=False).mean().iloc[-1])))
    if len(df) >= 100:
        levels.append(('EMA100', float(close.ewm(span=100, adjust=False).mean().iloc[-1])))
    if len(df) >= 200:
        levels.append(('EMA200', float(close.ewm(span=200, adjust=False).mean().iloc[-1])))
    return levels


def _find_poc(df: pd.DataFrame, num_levels: int = 100) -> Optional[float]:
    poc, _, _, _, _ = _build_volume_profile(df, num_levels)
    return poc

def _find_fractals(df: pd.DataFrame, order: int = 5) -> Tuple[List[float], List[float]]:
    """Williams分形"""
    if df is None or len(df) < order * 2 + 1:
        return [], []

    highs = df['high'].values
    lows = df['low'].values

    fractal_highs = []
    fractal_lows = []

    for i in range(order, len(df) - order):
        is_high = all(highs[i] >= highs[i-j] for j in range(1, order+1)) and \
                  all(highs[i] >= highs[i+j] for j in range(1, order+1))
        is_low = all(lows[i] <= lows[i-j] for j in range(1, order+1)) and \
                 all(lows[i] <= lows[i+j] for j in range(1, order+1))

        if is_high:
            fractal_highs.append(float(highs[i]))
        if is_low:
            fractal_lows.append(float(lows[i]))

    return fractal_highs, fractal_lows


def _find_orderbook_levels(
    orderbook: Dict,
    current_price: float,
    min_dist: float
) -> Tuple[List[Tuple[float, float, str]], List[Tuple[float, float, str]]]:
    """Find notable orderbook walls near the price."""
    supports = []
    resistances = []

    bids = orderbook.get('bids', [])
    asks = orderbook.get('asks', [])

    if bids:
        bid_notionals = [price * amount for price, amount in bids[:25]]
        bid_mean = np.mean(bid_notionals) if bid_notionals else 0

        for price, amount in bids[:25]:
            notional = price * amount
            ratio = notional / bid_mean if bid_mean > 0 else 0
            if ratio >= 1.6 and price < current_price * (1 - min_dist):
                weight = min(0.85, 0.55 + 0.08 * ratio)
                supports.append((float(price), weight, 'OrderBook'))

    if asks:
        ask_notionals = [price * amount for price, amount in asks[:25]]
        ask_mean = np.mean(ask_notionals) if ask_notionals else 0

        for price, amount in asks[:25]:
            notional = price * amount
            ratio = notional / ask_mean if ask_mean > 0 else 0
            if ratio >= 1.6 and price > current_price * (1 + min_dist):
                weight = min(0.85, 0.55 + 0.08 * ratio)
                resistances.append((float(price), weight, 'OrderBook'))

    return supports, resistances

def _merge_nearby_levels(levels: List[KeyLevel], threshold: float) -> List[KeyLevel]:
    """合并相近的主力位"""
    if not levels:
        return []

    sorted_levels = sorted(levels, key=lambda x: x.price)
    merged = []
    current_group = [sorted_levels[0]]

    for i in range(1, len(sorted_levels)):
        level = sorted_levels[i]
        last_price = current_group[-1].price

        if abs(level.price - last_price) / last_price < threshold:
            current_group.append(level)
        else:
            merged.append(_merge_level_group(current_group))
            current_group = [level]

    if current_group:
        merged.append(_merge_level_group(current_group))

    return merged


def _merge_level_group(group: List[KeyLevel]) -> KeyLevel:
    """Merge a group of nearby key levels."""
    if len(group) == 1:
        return group[0]

    best = max(group, key=lambda x: x.strength)

    all_sources = []
    total_touches = 0
    latest_touch = best.last_touch_idx
    strength_values = []

    for level in group:
        all_sources.extend(level.sources)
        total_touches += level.touches
        latest_touch = max(latest_touch, level.last_touch_idx)
        strength_values.append(level.strength)
        for key, value in level.confluence.items():
            if value:
                best.confluence[key] = True

    unique_sources = list(dict.fromkeys(all_sources))
    avg_strength = sum(strength_values) / len(strength_values) if strength_values else best.strength
    source_bonus = 0.04 * max(0, len(unique_sources) - 1)
    merged_strength = min(1.0, max(best.strength, avg_strength) + source_bonus)

    best.strength = merged_strength
    best.strength_grade = grade_strength(best.strength)
    best.sources = unique_sources
    best.touches = total_touches
    best.last_touch_idx = latest_touch

    return best

def _empty_result() -> Dict[str, Any]:
    """返回空结果"""
    return {
        'supports': [],
        'resistances': [],
        'strong_supports': [],
        'medium_supports': [],
        'weak_supports': [],
        'strong_resistances': [],
        'medium_resistances': [],
        'weak_resistances': [],
        'metadata': {'source': 'NONE', 'ai_confidence': 0}
    }


# 便捷函数
def get_key_levels_simple(
    df: pd.DataFrame,
    current_price: float,
    ai_levels: Optional[Dict[str, Any]] = None
) -> Tuple[List[float], List[float], Dict[str, Any]]:
    """
    简化接口 - 兼容旧代码
    返回: (supports, resistances, metadata)
    """
    result = find_ai_key_levels(df, current_price, ai_levels)

    supports = [l.price for l in result['supports']]
    resistances = [l.price for l in result['resistances']]

    metadata = result['metadata'].copy()
    metadata['support_strengths'] = [l.strength for l in result['supports']]
    metadata['resistance_strengths'] = [l.strength for l in result['resistances']]
    metadata['strong_support_count'] = len(result['strong_supports'])
    metadata['strong_resistance_count'] = len(result['strong_resistances'])

    return supports, resistances, metadata


def format_levels_for_display(result: Dict[str, Any]) -> str:
    """格式化主力位用于显示"""
    lines = []

    if result['strong_supports']:
        lines.append("🟢 强支撑位:")
        for l in result['strong_supports']:
            conf = [k for k, v in l.confluence.items() if v]
            conf_str = f" [{', '.join(conf)}]" if conf else ""
            lines.append(f"  ${l.price:,.4f} (强度:{l.strength:.0%}){conf_str}")

    if result['medium_supports']:
        lines.append("🔵 中等支撑:")
        for l in result['medium_supports']:
            lines.append(f"  ${l.price:,.4f} (强度:{l.strength:.0%})")

    if result['weak_supports']:
        lines.append("⚪ 弱支撑位:")
        for l in result['weak_supports']:
            lines.append(f"  ${l.price:,.4f} (强度:{l.strength:.0%})")

    if result['strong_resistances']:
        lines.append("🔴 强阻力位:")
        for l in result['strong_resistances']:
            conf = [k for k, v in l.confluence.items() if v]
            conf_str = f" [{', '.join(conf)}]" if conf else ""
            lines.append(f"  ${l.price:,.4f} (强度:{l.strength:.0%}){conf_str}")

    if result['medium_resistances']:
        lines.append("🟠 中等阻力:")
        for l in result['medium_resistances']:
            lines.append(f"  ${l.price:,.4f} (强度:{l.strength:.0%})")

    if result['weak_resistances']:
        lines.append("⚪ 弱阻力位:")
        for l in result['weak_resistances']:
            lines.append(f"  ${l.price:,.4f} (强度:{l.strength:.0%})")

    return "\n".join(lines)
