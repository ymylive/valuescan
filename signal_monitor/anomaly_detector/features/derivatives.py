"""
衍生品特征计算器
基于专业交易员建议的阈值策略
检测主力意图: 轧空、多头过热、上涨无力、强空信号
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import time

from ..config import get_symbol_tier, AnomalyConfig


@dataclass
class DerivativesResult:
    """衍生品特征结果"""
    funding_rate: float = 0.0
    funding_zscore: float = 0.0
    oi_current: float = 0.0
    oi_change_pct: float = 0.0
    price_change_pct: float = 0.0
    # 新增字段
    funding_warn: bool = False      # 资金费率警戒
    funding_extreme: bool = False   # 资金费率极端
    oi_warn: bool = False           # 持仓量警戒
    oi_extreme: bool = False        # 持仓量极端


class DerivativesFeatures:
    """
    衍生品特征计算器 - 支持分层阈值

    检测信号:
    - 轧空预警: 价格跌 + 费率极负
    - 多头过热: 价格涨 + 费率极高
    - 上涨无力: 价格涨 + OI跌
    - 强空信号: 价格跌 + OI涨
    """

    def __init__(self, config: Optional[AnomalyConfig] = None):
        cfg = config or AnomalyConfig()
        # 资金费率阈值 (专业建议)
        self.funding_warn_negative = cfg.funding_warn_negative    # -0.01%
        self.funding_warn_positive = cfg.funding_warn_positive    # 0.03%
        self.funding_extreme_negative = cfg.funding_extreme_negative  # -0.03%
        self.funding_extreme_positive = cfg.funding_extreme_positive  # 0.1%
        # 持仓量阈值
        self.oi_change_warn = cfg.oi_change_warn      # 3%
        self.oi_change_extreme = cfg.oi_change_extreme  # 8%
        self.price_change_threshold = cfg.price_change_threshold

        # OI历史缓存 {symbol: [(timestamp, oi), ...]}
        self._oi_history: Dict[str, List[Tuple[float, float]]] = {}
        self._history_window = 3600  # 1小时窗口 (更新为专业建议)

    def update_oi_history(self, symbol: str, oi: float) -> None:
        """更新OI历史"""
        now = time.time()
        if symbol not in self._oi_history:
            self._oi_history[symbol] = []

        self._oi_history[symbol].append((now, oi))

        # 清理过期数据
        self._oi_history[symbol] = [
            (t, o) for t, o in self._oi_history[symbol]
            if now - t <= self._history_window
        ]

    def get_oi_change_pct(self, symbol: str, current_oi: float) -> float:
        """计算OI变化百分比 (1小时窗口)"""
        history = self._oi_history.get(symbol, [])
        if not history:
            return 0.0

        old_oi = history[0][1]
        if old_oi == 0:
            return 0.0

        return ((current_oi - old_oi) / old_oi) * 100

    def compute(
        self,
        symbol: str,
        funding_rate: float,
        open_interest: float,
        price_change_pct: float,
        funding_history: Optional[List[float]] = None,
    ) -> DerivativesResult:
        """计算衍生品特征"""
        result = DerivativesResult()
        result.funding_rate = funding_rate
        result.oi_current = open_interest
        result.price_change_pct = price_change_pct

        # 更新OI历史并计算变化
        self.update_oi_history(symbol, open_interest)
        result.oi_change_pct = self.get_oi_change_pct(symbol, open_interest)

        # 计算资金费率Z-Score
        if funding_history and len(funding_history) >= 2:
            import statistics
            mean = statistics.mean(funding_history)
            std = statistics.stdev(funding_history)
            if std > 0:
                result.funding_zscore = (funding_rate - mean) / std

        # 资金费率警戒/极端判断
        result.funding_warn = (funding_rate < self.funding_warn_negative or
                               funding_rate > self.funding_warn_positive)
        result.funding_extreme = (funding_rate < self.funding_extreme_negative or
                                  funding_rate > self.funding_extreme_positive)

        # 持仓量警戒/极端判断
        result.oi_warn = abs(result.oi_change_pct) > self.oi_change_warn
        result.oi_extreme = abs(result.oi_change_pct) > self.oi_change_extreme

        return result

    def detect_signals(self, symbol: str, result: DerivativesResult) -> List[Dict]:
        """检测衍生品信号"""
        signals = []
        fr = result.funding_rate
        oi_change = result.oi_change_pct
        price_change = result.price_change_pct
        tier = get_symbol_tier(symbol)

        # 轧空预警: 价格跌 + 费率极负
        if price_change < -tier.price_change_5m and fr < self.funding_extreme_negative:
            signals.append({
                "type": "short_squeeze_warning",
                "direction": "bullish",
                "severity": "alert",
                "description": "轧空预警: 做空拥挤，可能反转上涨",
                "triggers": [
                    f"价格变动: {price_change:.2f}%",
                    f"资金费率: {fr*100:.4f}% (极度负值<{self.funding_extreme_negative*100}%)",
                ],
            })

        # 多头过热: 价格涨 + 费率极高
        if price_change > tier.price_change_5m and fr > self.funding_extreme_positive:
            signals.append({
                "type": "long_crowded",
                "direction": "bearish",
                "severity": "alert",
                "description": "多头过热: FOMO过度，主力可能收割",
                "triggers": [
                    f"价格变动: +{price_change:.2f}%",
                    f"资金费率: {fr*100:.4f}% (极高>{self.funding_extreme_positive*100}%)",
                ],
            })

        # 上涨无力: 价格涨 + OI跌 (极端)
        if price_change > tier.price_change_5m and oi_change < -self.oi_change_extreme:
            signals.append({
                "type": "weak_rally",
                "direction": "bearish",
                "severity": "alert",
                "description": "上涨无力: 空头平仓推动，非新资金入场",
                "triggers": [
                    f"价格变动: +{price_change:.2f}%",
                    f"持仓量变化: {oi_change:.2f}% (极端下降)",
                ],
            })

        # 强空信号: 价格跌 + OI涨 (极端)
        if price_change < -tier.price_change_5m and oi_change > self.oi_change_extreme:
            signals.append({
                "type": "strong_short",
                "direction": "bearish",
                "severity": "alert",
                "description": "强空信号: 主力开空打压，趋势可能延续",
                "triggers": [
                    f"价格变动: {price_change:.2f}%",
                    f"持仓量变化: +{oi_change:.2f}% (极端上升)",
                ],
            })

        # 资金费率警戒 (非极端但异常)
        if result.funding_warn and not result.funding_extreme:
            direction = "bearish" if fr > 0 else "bullish"
            signals.append({
                "type": "funding_rate_warning",
                "direction": direction,
                "severity": "warning",
                "description": f"资金费率异常: {'多头拥挤' if fr > 0 else '空头拥挤'}",
                "triggers": [f"资金费率: {fr*100:.4f}%"],
            })

        return signals
