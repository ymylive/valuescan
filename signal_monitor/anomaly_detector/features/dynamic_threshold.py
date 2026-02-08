"""
动态阈值管理器
基于 Z-Score 和 ATR 的自适应阈值调整
"""

from __future__ import annotations

from typing import List, Optional
import statistics


class DynamicThreshold:
    """动态阈值管理器 - 根据市场波动率自适应调整"""

    def __init__(self, zscore_threshold: float = 3.0, atr_multiplier: float = 3.0):
        self.zscore_threshold = zscore_threshold
        self.atr_multiplier = atr_multiplier

    def compute_zscore(self, values: List[float], current: float) -> float:
        """计算 Z-Score: (当前值 - 均值) / 标准差"""
        if len(values) < 2:
            return 0.0
        mean = statistics.mean(values)
        stdev = statistics.stdev(values)
        if stdev == 0:
            return 0.0
        return (current - mean) / stdev

    def is_zscore_anomaly(self, values: List[float], current: float, threshold: Optional[float] = None) -> bool:
        """判断是否为 Z-Score 异常 (偏离 N 个标准差)"""
        threshold = threshold or self.zscore_threshold
        zscore = abs(self.compute_zscore(values, current))
        return zscore > threshold

    def compute_atr(self, highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
        """计算 ATR (Average True Range)"""
        if len(highs) < 2 or len(lows) < 2 or len(closes) < 2:
            return 0.0

        true_ranges = []
        for i in range(1, min(len(highs), len(lows), len(closes))):
            high_low = highs[i] - lows[i]
            high_close = abs(highs[i] - closes[i - 1])
            low_close = abs(lows[i] - closes[i - 1])
            true_ranges.append(max(high_low, high_close, low_close))

        if not true_ranges:
            return 0.0

        # 使用最近 period 个 TR 计算 ATR
        recent_trs = true_ranges[-period:] if len(true_ranges) >= period else true_ranges
        return statistics.mean(recent_trs)

    def is_atr_anomaly(self, price_change: float, atr: float, multiplier: Optional[float] = None) -> bool:
        """判断价格变动是否超过 ATR 倍数阈值"""
        multiplier = multiplier or self.atr_multiplier
        if atr <= 0:
            return False
        return abs(price_change) > multiplier * atr

    def get_adaptive_vol_threshold(self, recent_volumes: List[float], base_threshold: float = 3.5) -> float:
        """根据近期成交量波动率自适应调整阈值"""
        if len(recent_volumes) < 5:
            return base_threshold

        mean_vol = statistics.mean(recent_volumes)
        stdev_vol = statistics.stdev(recent_volumes)

        if mean_vol == 0:
            return base_threshold

        # 波动率系数 = 标准差 / 均值
        cv = stdev_vol / mean_vol

        # 高波动市场 (cv > 0.5) 提高阈值，低波动市场降低阈值
        if cv > 0.5:
            return base_threshold * 1.2
        elif cv < 0.2:
            return base_threshold * 0.8
        return base_threshold

    def get_adaptive_price_threshold(self, recent_changes: List[float], base_threshold: float = 1.2) -> float:
        """根据近期价格波动自适应调整阈值"""
        if len(recent_changes) < 5:
            return base_threshold

        stdev = statistics.stdev(recent_changes)

        # 高波动市场提高阈值
        if stdev > 2.0:
            return base_threshold * 1.5
        elif stdev < 0.5:
            return base_threshold * 0.7
        return base_threshold
