"""
信号检测器 - 综合异动信号检测
基于专业交易员建议的分层阈值策略 + 多维度加权评分
"""

from __future__ import annotations

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
import time

from .config import AnomalyConfig
from .features.engine import FeatureEngine, FeatureSnapshot
from .features.scorer import AnomalyScorer, AnomalyScore

# 资金流异动检测


@dataclass
class Signal:
    """异动信号"""
    symbol: str
    signal_type: str
    direction: str  # bullish / bearish / neutral
    severity: str   # alert / warning / info
    description: str
    triggers: List[str] = field(default_factory=list)
    is_independent: bool = False  # 是否独立行情
    timestamp: float = field(default_factory=time.time)
    data: Dict[str, Any] = field(default_factory=dict)
    score: Optional[float] = None  # 综合评分

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "type": self.signal_type,
            "direction": self.direction,
            "severity": self.severity,
            "description": self.description,
            "triggers": self.triggers,
            "is_independent": self.is_independent,
            "timestamp": self.timestamp,
            "data": self.data,
            "score": self.score,
        }


class SignalDetector:
    """
    信号检测器 - 支持分层阈值 + 多维度加权评分

    综合量价、衍生品、盘口、相关性特征，生成异动信号
    """

    def __init__(self, config: Optional[AnomalyConfig] = None):
        self.config = config or AnomalyConfig()
        self.feature_engine = FeatureEngine(self.config)
        self.scorer = AnomalyScorer()

        # 更新评分器配置
        if hasattr(self.config, 'scoring_weights'):
            self.scorer.WEIGHTS = self.config.scoring_weights
        if hasattr(self.config, 'scoring_thresholds'):
            self.scorer.THRESHOLDS = self.config.scoring_thresholds

        # 情绪阈值
        self.fear_extreme = self.config.fear_extreme
        self.greed_extreme = self.config.greed_extreme

    def _count_active_dimensions(self, result: AnomalyScore) -> int:
        thresholds = {
            "volume_price": 10,
            "derivatives": 10,
            "fund_flow": 10,
            "orderbook": 8,
            "sentiment": 5,
            "technical": 10,
        }
        active = 0
        for dim, score in result.dimension_scores.items():
            if score >= thresholds.get(dim, 0):
                active += 1
        return active

    def _has_core_movement(self, snapshot: FeatureSnapshot) -> bool:
        vp = snapshot.volume_price
        if vp:
            if abs(vp.price_change_pct) >= self.config.price_change_threshold:
                return True
            if vp.vol_ma_ratio >= self.config.vol_spike_threshold:
                return True
            if abs(vp.vol_zscore) >= self.config.vol_zscore_threshold:
                return True
            if vp.price_vol_divergence:
                return True
        deriv = snapshot.derivatives
        if deriv:
            if abs(deriv.oi_change_pct) >= self.config.oi_change_warn:
                return True
            if deriv.funding_extreme:
                return True
        return False

    def detect(self, snapshot: FeatureSnapshot) -> List[Signal]:
        """检测异动信号（使用加权评分）"""
        signals = []
        symbol = snapshot.symbol

        # 使用加权评分系统
        if self.config.scoring_enabled:
            score_signal = self._detect_by_score(snapshot)
            if score_signal:
                signals.append(score_signal)

        # 保留原有规则检测作为补充（仅检测极端情况）
        extreme_signals = self._detect_extreme_cases(snapshot)
        signals.extend(extreme_signals)

        # 标记独立行情（需要核心波动且非BTC）
        if (
            snapshot.correlation
            and snapshot.correlation.is_independent
            and self._has_core_movement(snapshot)
            and snapshot.symbol.upper() != "BTC"
        ):
            for sig in signals:
                sig.is_independent = True

        return signals

    def _detect_by_score(self, snapshot: FeatureSnapshot) -> Optional[Signal]:
        """基于加权评分检测异动"""
        symbol = snapshot.symbol

        # 构建评分输入
        volume_price = None
        if snapshot.volume_price:
            vp = snapshot.volume_price
            volume_price = {
                "vol_ratio": vp.vol_ma_ratio,
                "price_change_pct": vp.price_change_pct,
                "is_divergence": vp.price_vol_divergence,
            }

        derivatives = None
        if snapshot.derivatives:
            deriv = snapshot.derivatives
            derivatives = {
                "funding_rate": deriv.funding_rate,
                "oi_change_pct": deriv.oi_change_pct,
                "long_short_ratio": getattr(deriv, 'long_short_ratio', 1.0),
                "price_change_pct": snapshot.volume_price.price_change_pct if snapshot.volume_price else 0,
            }

        fund_flow = None
        if hasattr(snapshot, 'fund_flow') and snapshot.fund_flow:
            ff = snapshot.fund_flow
            fund_flow = {
                "taker_ratio": ff.get("taker_ratio", 0.5),
                "net_inflow_trend": ff.get("trend", "none"),
            }

        orderbook = None
        if snapshot.orderbook:
            ob = snapshot.orderbook
            orderbook = {
                "imbalance_ratio": ob.imbalance_ratio,
                "whale_wall_side": ob.whale_wall.get("side") if ob.whale_wall else None,
                "spread_pct": ob.spread_pct,
            }

        # 计算综合评分
        current_price = 0.0
        if snapshot.technical and snapshot.technical.ema7 > 0:
            current_price = snapshot.technical.ema7  # 使用EMA7近似当前价格

        result = self.scorer.compute_total_score(
            volume_price=volume_price,
            derivatives=derivatives,
            fund_flow=fund_flow,
            orderbook=orderbook,
            fear_greed_index=snapshot.fear_greed_index,
            technical_snapshot=snapshot.technical,
            current_price=current_price,
        )

        # 根据评分生成信号
        if result.severity == "none":
            return None
        active_dims = self._count_active_dimensions(result)
        core_ok = self._has_core_movement(snapshot)
        if result.severity == "info":
            return None
        if result.severity == "warning" and (not core_ok or active_dims < 2):
            return None
        if result.severity == "alert" and (not core_ok and active_dims < 2):
            return None

        direction_label = {"bullish": "看涨", "bearish": "看跌", "neutral": "中性"}.get(result.direction, "中性")
        severity_label = {"alert": "警报", "warning": "警告", "info": "提示"}.get(result.severity, "提示")

        description = f"【{direction_label}信号】综合评分 {result.total_score:.1f}分 ({severity_label}级)"

        return Signal(
            symbol=symbol,
            signal_type="weighted_anomaly",
            direction=result.direction,
            severity=result.severity,
            description=description,
            triggers=result.triggers,
            data={
                "total_score": result.total_score,
                "dimension_scores": result.dimension_scores,
                "bullish_votes": result.bullish_votes,
                "bearish_votes": result.bearish_votes,
            },
            score=result.total_score,
        )

    def _detect_extreme_cases(self, snapshot: FeatureSnapshot) -> List[Signal]:
        """检测极端情况（作为评分系统的补充）"""
        signals = []
        symbol = snapshot.symbol
        fgi = snapshot.fear_greed_index
        core_ok = self._has_core_movement(snapshot)

        # 极度恐惧
        if fgi <= self.fear_extreme and core_ok:
            signals.append(Signal(
                symbol=symbol,
                signal_type="extreme_fear",
                direction="bullish",
                severity="alert",
                description=f"市场极度恐惧 (FGI={fgi})，异动信号",
                triggers=[f"恐惧贪婪指数: {fgi}"],
            ))
        # 极度贪婪
        elif fgi >= self.greed_extreme and core_ok:
            signals.append(Signal(
                symbol=symbol,
                signal_type="extreme_greed",
                direction="bearish",
                severity="alert",
                description=f"市场极度贪婪 (FGI={fgi})，异动信号",
                triggers=[f"恐惧贪婪指数: {fgi}"],
            ))

        # 资金流异动检测

        return signals

    def detect_from_raw(
        self,
        symbol: str,
        volumes: List[float],
        closes: List[float],
        funding_rate: float,
        open_interest: float,
        btc_price: float,
        fear_greed_index: int = 50,
        orderbook_bids: Optional[List[Tuple[float, float]]] = None,
        orderbook_asks: Optional[List[Tuple[float, float]]] = None,
        highs: Optional[List[float]] = None,
        lows: Optional[List[float]] = None,
    ) -> List[Signal]:
        """从原始数据检测信号"""
        snapshot = self.feature_engine.compute_all(
            symbol=symbol,
            volumes=volumes,
            closes=closes,
            funding_rate=funding_rate,
            open_interest=open_interest,
            btc_price=btc_price,
            fear_greed_index=fear_greed_index,
            orderbook_bids=orderbook_bids,
            orderbook_asks=orderbook_asks,
            highs=highs,
            lows=lows,
        )
        return self.detect(snapshot)
