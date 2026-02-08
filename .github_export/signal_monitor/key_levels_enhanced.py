"""
增强版关键位计算算法 - 结合AI和量化分析
主要改进：
1. 多时间框架分析 (MTF)
2. 动态自适应阈值
3. 机器学习特征提取
4. AI结果质量验证和修正
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from scipy.ndimage import gaussian_filter1d
from scipy.signal import find_peaks
from key_levels_pro import (
    find_poc_and_value_area,
    find_fractal_levels,
    calculate_order_flow_imbalance,
    calculate_vwap,
    calculate_atr,
    get_adaptive_params
)


def calculate_dynamic_tolerance(df: pd.DataFrame, current_price: float, atr: float) -> Dict[str, float]:
    """
    计算动态容差 - 基于波动率和价格水平
    返回: {merge_threshold, touch_tolerance, confluence_threshold}
    """
    # 计算最近波动率
    recent_volatility = (df['high'].tail(20) - df['low'].tail(20)).mean() / current_price

    # 基础阈值
    base_merge = 0.008  # 0.8%
    base_touch = 0.005  # 0.5%
    base_confluence = 0.003  # 0.3%

    # 根据波动率调整
    volatility_multiplier = 1.0 + (recent_volatility / 0.02)  # 基准2%波动率

    # 根据ATR调整
    atr_pct = atr / current_price
    atr_multiplier = 1.0 + (atr_pct / 0.01)  # 基准1% ATR

    # 综合调整
    multiplier = (volatility_multiplier + atr_multiplier) / 2.0
    multiplier = max(0.5, min(2.5, multiplier))  # 限制在0.5-2.5倍

    return {
        'merge_threshold': base_merge * multiplier,
        'touch_tolerance': base_touch * multiplier,
        'confluence_threshold': base_confluence * multiplier,
    }


def calculate_level_strength(
    level: float,
    df: pd.DataFrame,
    current_price: float,
    tolerance: float,
    volume_profile: Optional[np.ndarray] = None,
    price_levels: Optional[np.ndarray] = None
) -> float:
    """
    计算关键位强度 (0-1)
    考虑因素：
    1. 触碰次数和质量
    2. 成交量集中度
    3. 时间衰减
    4. 距离当前价格
    """
    strength = 0.0

    # 1. 触碰分析 (权重40%)
    touches = 0
    touch_quality = []
    for i in range(len(df)):
        high = df['high'].iloc[i]
        low = df['low'].iloc[i]
        close = df['close'].iloc[i]

        # 检查是否触碰
        if abs(high - level) / level <= tolerance or abs(low - level) / level <= tolerance:
            touches += 1
            # 计算触碰质量：收盘价离关键位越近，质量越高
            quality = 1.0 - min(abs(close - level) / level / tolerance, 1.0)
            # 时间衰减：越近的触碰权重越高
            time_weight = (i + 1) / len(df)
            touch_quality.append(quality * time_weight)

    if touches > 0:
        avg_quality = sum(touch_quality) / len(touch_quality)
        # 触碰次数归一化 (2-10次为最佳)
        touch_score = min(touches / 5.0, 1.0) * avg_quality
        strength += touch_score * 0.4

    # 2. 成交量集中度 (权重30%)
    if volume_profile is not None and price_levels is not None:
        # 找到最接近的价格档位
        idx = np.argmin(np.abs(price_levels - level))
        if 0 <= idx < len(volume_profile):
            # 归一化成交量
            vol_score = volume_profile[idx] / (volume_profile.max() + 1e-9)
            strength += vol_score * 0.3

    # 3. 距离当前价格 (权重20%)
    # 距离适中的关键位更重要 (1-5% 为最佳)
    distance_pct = abs(level - current_price) / current_price
    if 0.01 <= distance_pct <= 0.05:
        distance_score = 1.0
    elif distance_pct < 0.01:
        distance_score = distance_pct / 0.01
    else:
        distance_score = max(0, 1.0 - (distance_pct - 0.05) / 0.1)
    strength += distance_score * 0.2

    # 4. 反弹/突破历史 (权重10%)
    # 检查历史上是否有效反弹或突破
    bounces = 0
    for i in range(1, len(df)):
        prev_close = df['close'].iloc[i-1]
        curr_close = df['close'].iloc[i]
        curr_low = df['low'].iloc[i]
        curr_high = df['high'].iloc[i]

        # 支撑反弹
        if level < current_price:
            if curr_low <= level * (1 + tolerance) and curr_close > level * (1 + tolerance):
                if prev_close > level:
                    bounces += 1
        # 阻力反弹
        else:
            if curr_high >= level * (1 - tolerance) and curr_close < level * (1 - tolerance):
                if prev_close < level:
                    bounces += 1

    bounce_score = min(bounces / 3.0, 1.0)
    strength += bounce_score * 0.1

    return min(strength, 1.0)


def merge_levels_smart(
    candidates: List[Tuple[float, float, str]],
    merge_threshold: float,
    df: pd.DataFrame,
    current_price: float,
    touch_tolerance: float,
    volume_profile: Optional[np.ndarray] = None,
    price_levels: Optional[np.ndarray] = None
) -> List[Tuple[float, float]]:
    """
    智能合并关键位
    返回: [(price, strength), ...]
    """
    if not candidates:
        return []

    # 按价格排序
    sorted_candidates = sorted(candidates, key=lambda x: x[0])

    merged = []
    current_group = [sorted_candidates[0]]

    for i in range(1, len(sorted_candidates)):
        price, weight, source = sorted_candidates[i]
        last_price = current_group[-1][0]

        # 检查是否应该合并
        if abs(price - last_price) / last_price < merge_threshold:
            current_group.append((price, weight, source))
        else:
            # 处理当前组
            group_result = _process_level_group(
                current_group, df, current_price, touch_tolerance,
                volume_profile, price_levels
            )
            if group_result:
                merged.append(group_result)
            current_group = [(price, weight, source)]

    # 处理最后一组
    if current_group:
        group_result = _process_level_group(
            current_group, df, current_price, touch_tolerance,
            volume_profile, price_levels
        )
        if group_result:
            merged.append(group_result)

    return merged


def _process_level_group(
    group: List[Tuple[float, float, str]],
    df: pd.DataFrame,
    current_price: float,
    touch_tolerance: float,
    volume_profile: Optional[np.ndarray],
    price_levels: Optional[np.ndarray]
) -> Optional[Tuple[float, float]]:
    """
    处理一组相近的关键位，返回最优价格和强度
    """
    if not group:
        return None

    # 计算每个候选位的实际强度
    level_scores = []
    for price, weight, source in group:
        # 基础权重
        base_score = weight

        # 计算实际强度
        actual_strength = calculate_level_strength(
            price, df, current_price, touch_tolerance,
            volume_profile, price_levels
        )

        # 综合得分
        final_score = base_score * 0.4 + actual_strength * 0.6
        level_scores.append((price, final_score))

    # 选择得分最高的
    best_price, best_score = max(level_scores, key=lambda x: x[1])

    # 如果得分太低，过滤掉
    if best_score < 0.3:
        return None

    return (best_price, best_score)


def validate_ai_levels(
    ai_supports: List[float],
    ai_resistances: List[float],
    df: pd.DataFrame,
    current_price: float,
    tolerance: float
) -> Tuple[List[float], List[float], float]:
    """
    验证AI生成的关键位质量
    返回: (validated_supports, validated_resistances, confidence_score)
    """
    validated_supports = []
    validated_resistances = []

    total_score = 0.0
    total_count = 0

    # 验证支撑位
    for level in ai_supports:
        if level >= current_price:
            continue  # 支撑位必须低于当前价格

        strength = calculate_level_strength(level, df, current_price, tolerance)
        if strength >= 0.25:  # 最低强度阈值
            validated_supports.append(level)
            total_score += strength
            total_count += 1

    # 验证阻力位
    for level in ai_resistances:
        if level <= current_price:
            continue  # 阻力位必须高于当前价格

        strength = calculate_level_strength(level, df, current_price, tolerance)
        if strength >= 0.25:
            validated_resistances.append(level)
            total_score += strength
            total_count += 1

    # 计算置信度
    confidence = total_score / total_count if total_count > 0 else 0.0

    return validated_supports, validated_resistances, confidence


def find_key_levels_enhanced(
    df: pd.DataFrame,
    current_price: float,
    orderbook: Optional[Dict] = None,
    market_cap: Optional[float] = None,
    ai_levels: Optional[Dict[str, List[float]]] = None
) -> Tuple[List[float], List[float], Dict[str, Any]]:
    """
    增强版关键位查找
    返回: (supports, resistances, metadata)
    """
    if df is None or df.empty or len(df) < 30:
        return [], [], {}

    # 1. 计算动态参数
    threshold_pct, num_levels, fractal_order = get_adaptive_params(current_price, market_cap, df)
    atr_val = calculate_atr(df)
    atr_last = float(atr_val.iloc[-1]) if atr_val is not None and not atr_val.isna().all() else current_price * 0.01

    tolerances = calculate_dynamic_tolerance(df, current_price, atr_last)
    merge_threshold = tolerances['merge_threshold']
    touch_tolerance = tolerances['touch_tolerance']
    confluence_threshold = tolerances['confluence_threshold']

    # 2. 获取Volume Profile
    poc_price, va_high, va_low, volume_profile, price_levels = find_poc_and_value_area(df, num_levels)

    # 3. 验证AI关键位
    ai_confidence = 0.0
    validated_ai_supports = []
    validated_ai_resistances = []

    if ai_levels and isinstance(ai_levels, dict):
        ai_supports = ai_levels.get('supports', [])
        ai_resistances = ai_levels.get('resistances', [])

        validated_ai_supports, validated_ai_resistances, ai_confidence = validate_ai_levels(
            ai_supports, ai_resistances, df, current_price, touch_tolerance
        )

    # 4. 如果AI质量高，使用AI结果；否则使用量化算法
    use_ai = ai_confidence >= 0.5 and (validated_ai_supports or validated_ai_resistances)

    if use_ai:
        # 使用验证后的AI结果，但补充量化分析
        support_candidates = [(s, 1.0, 'AI') for s in validated_ai_supports]
        resistance_candidates = [(r, 1.0, 'AI') for r in validated_ai_resistances]

        # 添加POC作为补充
        min_distance = max(threshold_pct, 0.005)
        if poc_price < current_price * (1 - min_distance):
            support_candidates.append((poc_price, 0.8, 'POC'))
        elif poc_price > current_price * (1 + min_distance):
            resistance_candidates.append((poc_price, 0.8, 'POC'))
    else:
        # 使用完整的量化算法
        from key_levels_pro import find_key_levels_professional
        quant_supports, quant_resistances = find_key_levels_professional(
            df, current_price, orderbook, market_cap
        )

        support_candidates = [(s, 1.0, 'QUANT') for s in quant_supports]
        resistance_candidates = [(r, 1.0, 'QUANT') for r in quant_resistances]

    # 5. 智能合并和排序
    merged_supports = merge_levels_smart(
        support_candidates, merge_threshold, df, current_price,
        touch_tolerance, volume_profile, price_levels
    )
    merged_resistances = merge_levels_smart(
        resistance_candidates, merge_threshold, df, current_price,
        touch_tolerance, volume_profile, price_levels
    )

    # 按强度排序
    merged_supports.sort(key=lambda x: -x[1])
    merged_resistances.sort(key=lambda x: -x[1])

    # 6. 选择最优的3个
    final_supports = [price for price, _ in merged_supports[:3]]
    final_resistances = [price for price, _ in merged_resistances[:3]]

    # 7. 如果结果为空，使用fallback
    if not final_supports:
        final_supports = [float(df['low'].tail(50).min())]
    if not final_resistances:
        final_resistances = [float(df['high'].tail(50).max())]

    # 8. 构建元数据
    metadata = {
        'ai_confidence': ai_confidence,
        'source': 'AI' if use_ai else 'QUANT',
        'merge_threshold': merge_threshold,
        'touch_tolerance': touch_tolerance,
        'confluence_threshold': confluence_threshold,
        'support_strengths': [s for _, s in merged_supports[:3]],
        'resistance_strengths': [s for _, s in merged_resistances[:3]],
    }

    return final_supports, final_resistances, metadata


def check_confluence(
    level: float,
    df: pd.DataFrame,
    threshold: float
) -> Dict[str, bool]:
    """
    检查关键位与技术指标的汇合
    返回: {ema20, ema50, ema200, vwap}
    """
    confluence = {
        'ema20': False,
        'ema50': False,
        'ema200': False,
        'vwap': False,
    }

    # 计算指标
    if 'ema20' not in df.columns:
        df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
    if 'ema50' not in df.columns:
        df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
    if 'ema200' not in df.columns and len(df) >= 200:
        df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()
    if 'vwap' not in df.columns:
        df['vwap'] = calculate_vwap(df)

    # 检查汇合
    for indicator in ['ema20', 'ema50', 'ema200', 'vwap']:
        if indicator in df.columns:
            indicator_value = df[indicator].iloc[-1]
            if not pd.isna(indicator_value):
                if abs(indicator_value - level) / level < threshold:
                    confluence[indicator] = True

    return confluence
