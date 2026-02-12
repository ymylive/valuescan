"""Shared technical analysis utilities for ValuScan QuantRefactorV3"""

from typing import List


def calculate_atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
    """
    Calculate Average True Range

    Args:
        highs: High prices
        lows: Low prices
        closes: Close prices
        period: ATR period (default 14)

    Returns:
        ATR value
    """
    if len(highs) < period + 1:
        return 0.0

    true_ranges = []
    for i in range(1, len(highs)):
        high_low = highs[i] - lows[i]
        high_close = abs(highs[i] - closes[i-1])
        low_close = abs(lows[i] - closes[i-1])
        true_ranges.append(max(high_low, high_close, low_close))

    if len(true_ranges) < period:
        return 0.0

    return sum(true_ranges[-period:]) / period
