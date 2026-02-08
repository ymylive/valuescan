"""
量价特征计算器
基于专业交易员建议的分层阈值策略
"""

from __future__ import annotations

from typing import Dict, List, Optional
from dataclasses import dataclass
import statistics

from ..config import get_symbol_tier, SymbolTier
from .dynamic_threshold import DynamicThreshold


@dataclass
class VolumePriceResult:
    """量价特征结果"""
    vol_ma_ratio: float = 0.0      # 成交量/MA比率
    vol_zscore: float = 0.0        # 成交量Z-Score
    vol_spike: bool = False        # 是否成交量突刺
    price_change_pct: float = 0.0  # 价格变化百分比
    price_vol_divergence: bool = False  # 量价背离
    is_zscore_anomaly: bool = False     # Z-Score 异常


class VolumePriceFeatures:
    """
    量价特征计算器 - 支持分层阈值

    检测:
    - 异常放量 (BTC/ETH: >3.5x, 山寨币: >5x)
    - 统计异常 (Z-Score > 3)
    - 量价背离 (价格平稳但成交量异常)
    """

    def __init__(self, lookback: int = 20, use_dynamic: bool = True):
        self.lookback = lookback
        self.use_dynamic = use_dynamic
        self.dynamic = DynamicThreshold()

    def compute(self, symbol: str, volumes: List[float], closes: List[float],
                highs: Optional[List[float]] = None, lows: Optional[List[float]] = None) -> VolumePriceResult:
        """
        计算量价特征

        Args:
            symbol: 币种符号
            volumes: 成交量序列 (最新在最后)
            closes: 收盘价序列 (最新在最后)
            highs: 最高价序列 (可选，用于ATR)
            lows: 最低价序列 (可选，用于ATR)
        """
        result = VolumePriceResult()
        tier = get_symbol_tier(symbol)

        if len(volumes) < 2 or len(closes) < 2:
            return result

        current_vol = volumes[-1]
        current_close = closes[-1]
        prev_close = closes[-2]

        # 价格变化
        if prev_close > 0:
            result.price_change_pct = ((current_close - prev_close) / prev_close) * 100

        # 成交量MA比率
        lookback_vols = volumes[-self.lookback:] if len(volumes) >= self.lookback else volumes
        if lookback_vols:
            vol_ma = statistics.mean(lookback_vols)
            if vol_ma > 0:
                result.vol_ma_ratio = current_vol / vol_ma
                # 使用分层阈值判断突刺
                result.vol_spike = result.vol_ma_ratio >= tier.vol_ma_ratio

        # 成交量Z-Score
        if len(lookback_vols) >= 2:
            vol_std = statistics.stdev(lookback_vols)
            vol_mean = statistics.mean(lookback_vols)
            if vol_std > 0:
                result.vol_zscore = (current_vol - vol_mean) / vol_std
                result.is_zscore_anomaly = abs(result.vol_zscore) >= 3.0

        # 量价背离检测 (价格平稳但成交量异常)
        price_flat = abs(result.price_change_pct) < tier.divergence_price
        vol_high = result.vol_ma_ratio >= tier.divergence_vol
        result.price_vol_divergence = price_flat and vol_high

        return result

    def detect_anomaly(self, symbol: str, result: VolumePriceResult) -> Optional[Dict]:
        """
        检测量价异动

        Returns:
            异动信息字典，无异动返回None
        """
        tier = get_symbol_tier(symbol)
        triggers = []
        severity = "warning"

        # 成交量突刺
        if result.vol_spike:
            triggers.append(f"成交量突增 {result.vol_ma_ratio:.1f}x (阈值>{tier.vol_ma_ratio}x)")
            severity = "alert"

        # Z-Score 异常
        if result.is_zscore_anomaly:
            triggers.append(f"成交量Z-Score: {result.vol_zscore:.2f} (>3σ)")

        # 量价背离
        if result.price_vol_divergence:
            triggers.append(f"量价背离: 价格{result.price_change_pct:+.2f}% 量{result.vol_ma_ratio:.1f}x")

        # 价格剧烈波动
        if abs(result.price_change_pct) >= tier.price_change_5m:
            direction = "📈" if result.price_change_pct > 0 else "📉"
            triggers.append(f"价格剧变 {direction} {result.price_change_pct:+.2f}%")
            severity = "alert"

        if triggers:
            return {
                "type": "volume_price_anomaly",
                "triggers": triggers,
                "severity": severity,
                "data": {
                    "vol_ma_ratio": result.vol_ma_ratio,
                    "vol_zscore": result.vol_zscore,
                    "price_change_pct": result.price_change_pct,
                    "tier": tier.tier,
                }
            }

        return None
