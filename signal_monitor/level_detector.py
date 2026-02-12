"""
Support/Resistance level detection for ValuScan QuantRefactorV3
Multi-timeframe level detection with clustering and deduplication
"""

import numpy as np
from typing import Dict, List, Any, Tuple
from scipy.signal import argrelextrema
from collections import Counter


def detect_swing_points(prices: List[float], order: int = 5) -> Tuple[List[int], List[int]]:
    """
    Detect swing highs and lows using local extrema

    Args:
        prices: Price series
        order: Lookback window for local extrema detection

    Returns:
        (swing_high_indices, swing_low_indices)
    """
    if len(prices) < order * 2 + 1:
        return [], []

    arr = np.array(prices)

    # Find local maxima and minima
    high_indices = argrelextrema(arr, np.greater, order=order)[0]
    low_indices = argrelextrema(arr, np.less, order=order)[0]

    return high_indices.tolist(), low_indices.tolist()


def cluster_levels(levels: List[float], tolerance: float) -> List[float]:
    """
    Cluster nearby levels and return representative levels

    Args:
        levels: List of price levels
        tolerance: Clustering tolerance (absolute price difference)

    Returns:
        List of clustered levels
    """
    if not levels:
        return []

    sorted_levels = sorted(levels)
    clusters = []
    current_cluster = [sorted_levels[0]]

    for level in sorted_levels[1:]:
        if level - current_cluster[-1] <= tolerance:
            current_cluster.append(level)
        else:
            # Take median of cluster
            clusters.append(float(np.median(current_cluster)))
            current_cluster = [level]

    # Add last cluster
    if current_cluster:
        clusters.append(float(np.median(current_cluster)))

    return clusters


def calculate_atr_simple(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
    """Calculate ATR for tolerance calculation"""
    if len(highs) < period + 1:
        return (max(highs) - min(lows)) * 0.01  # Fallback to 1% of range

    tr_list = []
    for i in range(1, len(highs)):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
        tr_list.append(tr)

    atr = sum(tr_list[-period:]) / period
    return float(atr)


def extract_levels_from_timeframe(klines: List[Dict[str, Any]], order: int = 5) -> Dict[str, List[float]]:
    """
    Extract support and resistance levels from a single timeframe

    Args:
        klines: List of kline dicts with OHLCV data
        order: Lookback window for swing detection

    Returns:
        {"support": [...], "resistance": [...]}
    """
    if len(klines) < order * 2 + 1:
        return {"support": [], "resistance": []}

    highs = [k["high"] for k in klines]
    lows = [k["low"] for k in klines]
    closes = [k["close"] for k in klines]

    # Detect swing points
    high_indices, low_indices = detect_swing_points(highs, order)

    resistance_levels = [highs[i] for i in high_indices]
    support_levels = [lows[i] for i in low_indices]

    # Calculate clustering tolerance (0.5% * ATR)
    atr = calculate_atr_simple(highs, lows, closes)
    tolerance = atr * 0.5

    # Cluster levels
    resistance = cluster_levels(resistance_levels, tolerance)
    support = cluster_levels(support_levels, tolerance)

    return {
        "support": support,
        "resistance": resistance
    }


def merge_multi_timeframe_levels(
    levels_15m: Dict[str, List[float]],
    levels_1h: Dict[str, List[float]],
    levels_4h: Dict[str, List[float]],
    levels_1d: Dict[str, List[float]],
    current_price: float
) -> Dict[str, List[float]]:
    """
    Merge levels from multiple timeframes with weighting

    Timeframe weights: 1d=4, 4h=3, 1h=2, 15m=1

    Args:
        levels_15m, levels_1h, levels_4h, levels_1d: Level dicts per timeframe
        current_price: Current asset price for tolerance calculation

    Returns:
        Merged {"support": [...], "resistance": [...]}
    """
    # Weight levels by timeframe importance using Counter
    support_weights = Counter()
    resistance_weights = Counter()

    for level in levels_1d["support"]:
        support_weights[level] += 4
    for level in levels_4h["support"]:
        support_weights[level] += 3
    for level in levels_1h["support"]:
        support_weights[level] += 2
    for level in levels_15m["support"]:
        support_weights[level] += 1

    for level in levels_1d["resistance"]:
        resistance_weights[level] += 4
    for level in levels_4h["resistance"]:
        resistance_weights[level] += 3
    for level in levels_1h["resistance"]:
        resistance_weights[level] += 2
    for level in levels_15m["resistance"]:
        resistance_weights[level] += 1

    weighted_support = list(support_weights.elements())
    weighted_resistance = list(resistance_weights.elements())

    # Cluster with tolerance based on current price
    tolerance = current_price * 0.005  # 0.5% of current price

    support = cluster_levels(weighted_support, tolerance)
    resistance = cluster_levels(weighted_resistance, tolerance)

    # Keep only top 5 closest levels to current price
    support = sorted([s for s in support if s < current_price], reverse=True)[:5]
    resistance = sorted([r for r in resistance if r > current_price])[:5]

    return {
        "support": support,
        "resistance": resistance
    }


def detect_levels(data: Dict[str, Any]) -> Dict[str, List[float]]:
    """
    Main entry point for level detection

    Args:
        data: Multi-timeframe klines input (see SCHEMAS_V3.md)

    Returns:
        {"support": [level1, level2, ...], "resistance": [level1, level2, ...]}
    """
    if "timeframes" not in data:
        raise ValueError("Missing 'timeframes' field")

    required_tfs = ["15m", "1h", "4h", "1d"]
    for tf in required_tfs:
        if tf not in data["timeframes"]:
            raise ValueError(f"Missing timeframe: {tf}")

    # Extract levels per timeframe
    levels_15m = extract_levels_from_timeframe(data["timeframes"]["15m"], order=3)
    levels_1h = extract_levels_from_timeframe(data["timeframes"]["1h"], order=5)
    levels_4h = extract_levels_from_timeframe(data["timeframes"]["4h"], order=5)
    levels_1d = extract_levels_from_timeframe(data["timeframes"]["1d"], order=7)

    # Get current price
    current_price = data["timeframes"]["15m"][-1]["close"]

    # Merge with weighting
    merged_levels = merge_multi_timeframe_levels(
        levels_15m, levels_1h, levels_4h, levels_1d, current_price
    )

    return merged_levels
