"""
多维度加权评分器 - 综合异动信号评分系统
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any

from .technical_indicators import TechnicalSnapshot, score_technical_indicators


@dataclass
class AnomalyScore:
    """异动评分结果"""
    total_score: float  # 0-100
    direction: str  # bullish/bearish/neutral
    severity: str  # none/info/warning/alert
    dimension_scores: Dict[str, float] = field(default_factory=dict)
    bullish_votes: int = 0
    bearish_votes: int = 0
    triggers: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_score": self.total_score,
            "direction": self.direction,
            "severity": self.severity,
            "dimension_scores": self.dimension_scores,
            "bullish_votes": self.bullish_votes,
            "bearish_votes": self.bearish_votes,
            "triggers": self.triggers,
        }


class AnomalyScorer:
    """多维度加权评分器"""

    # 权重配置
    WEIGHTS = {
        "volume_price": 0.25,
        "derivatives": 0.20,
        "fund_flow": 0.15,
        "orderbook": 0.15,
        "sentiment": 0.10,
        "technical": 0.15,
    }

    # 信号阈值
    THRESHOLDS = {
        "info": 40,
        "warning": 60,
        "alert": 75,
    }

    def score_volume_price(
        self,
        vol_ratio: float,
        price_change_pct: float,
        is_divergence: bool = False,
    ) -> Tuple[float, str]:
        """
        量价评分 (0-30分)
        返回 (分数, 方向)
        """
        score = 0.0
        direction = "neutral"

        # 成交量倍数评分 (0-15分)
        if vol_ratio >= 5:
            score += 15
        elif vol_ratio >= 3:
            score += 10
        elif vol_ratio >= 2:
            score += 5

        # 价格变动评分 (0-15分)
        abs_change = abs(price_change_pct)
        if abs_change >= 3:
            score += 15
        elif abs_change >= 2:
            score += 10
        elif abs_change >= 1:
            score += 5

        # 量价背离额外加分
        if is_divergence:
            score = min(score + 5, 30)

        # 方向判断
        if price_change_pct > 0.5:
            direction = "bullish"
        elif price_change_pct < -0.5:
            direction = "bearish"

        return score, direction

    def score_derivatives(
        self,
        funding_rate: float,
        oi_change_pct: float,
        long_short_ratio: float = 1.0,
        price_change_pct: float = 0.0,
    ) -> Tuple[float, str]:
        """
        衍生品评分 (0-25分)
        返回 (分数, 方向)
        """
        score = 0.0
        bullish = 0
        bearish = 0

        # 资金费率评分 (0-10分)
        fr_pct = funding_rate * 100  # 转为百分比
        if fr_pct < -0.03:
            score += 10
            bullish += 1  # 空头拥挤，看涨
        elif fr_pct < -0.01:
            score += 5
            bullish += 1
        elif fr_pct > 0.1:
            score += 10
            bearish += 1  # 多头过热，看跌
        elif fr_pct > 0.03:
            score += 5
            bearish += 1

        # 持仓量变化评分 (0-10分)
        abs_oi = abs(oi_change_pct)
        if abs_oi > 5:
            score += 10
        elif abs_oi > 3:
            score += 5

        # OI + 价格组合判断方向
        if oi_change_pct > 3 and price_change_pct > 1:
            bullish += 1  # 新多入场
        elif oi_change_pct > 3 and price_change_pct < -1:
            bearish += 1  # 新空入场
        elif oi_change_pct < -3 and price_change_pct > 1:
            bearish += 1  # 空头平仓推动，后续可能回落
        elif oi_change_pct < -3 and price_change_pct < -1:
            bullish += 1  # 多头平仓，可能见底

        # 多空比偏离评分 (0-5分)
        if long_short_ratio < 0.6 or long_short_ratio > 1.5:
            score += 5
            if long_short_ratio < 0.6:
                bullish += 1  # 空头拥挤
            else:
                bearish += 1  # 多头拥挤
        elif long_short_ratio < 0.8 or long_short_ratio > 1.2:
            score += 3

        direction = "bullish" if bullish > bearish else "bearish" if bearish > bullish else "neutral"
        return score, direction

    def score_fund_flow(
        self,
        taker_ratio: float,
        net_inflow_trend: str = "none",
    ) -> Tuple[float, str]:
        """
        资金流向评分 (0-20分)
        taker_ratio: Taker买卖比 (买/总)
        net_inflow_trend: "positive" / "negative" / "none"
        返回 (分数, 方向)
        """
        score = 0.0
        direction = "neutral"

        # Taker买卖比评分 (0-10分)
        if taker_ratio > 0.6 or taker_ratio < 0.4:
            score += 10
            direction = "bullish" if taker_ratio > 0.6 else "bearish"
        elif taker_ratio > 0.55 or taker_ratio < 0.45:
            score += 5
            direction = "bullish" if taker_ratio > 0.55 else "bearish"

        # 净流入趋势评分 (0-10分)
        if net_inflow_trend == "positive":
            score += 10
            if direction == "neutral":
                direction = "bullish"
        elif net_inflow_trend == "negative":
            score += 10
            if direction == "neutral":
                direction = "bearish"
        elif net_inflow_trend == "mixed":
            score += 5

        return score, direction

    def score_orderbook(
        self,
        imbalance_ratio: float,
        whale_wall_side: Optional[str] = None,
        spread_pct: float = 0.0,
    ) -> Tuple[float, str]:
        """
        盘口评分 (0-15分)
        imbalance_ratio: 买/卖失衡比
        whale_wall_side: "bid" / "ask" / None
        spread_pct: 价差百分比
        返回 (分数, 方向)
        """
        score = 0.0
        direction = "neutral"

        # 买卖失衡评分 (0-8分)
        if imbalance_ratio >= 3 or imbalance_ratio <= 0.33:
            score += 8
            direction = "bullish" if imbalance_ratio >= 3 else "bearish"
        elif imbalance_ratio >= 2 or imbalance_ratio <= 0.5:
            score += 4
            direction = "bullish" if imbalance_ratio >= 2 else "bearish"

        # 大单墙评分 (0-7分)
        if whale_wall_side == "bid":
            score += 7
            if direction == "neutral":
                direction = "bullish"
        elif whale_wall_side == "ask":
            score += 7
            if direction == "neutral":
                direction = "bearish"

        # 流动性枯竭 (价差过大) - 不影响方向，但增加异动分数
        if spread_pct > 0.05:
            score = min(score + 3, 15)

        return score, direction

    def score_sentiment(self, fear_greed_index: int) -> Tuple[float, str]:
        """
        情绪评分 (0-10分)
        返回 (分数, 方向)
        """
        score = 0.0
        direction = "neutral"

        if fear_greed_index <= 20:
            score = 10
            direction = "bullish"  # 极度恐惧，逆向看涨
        elif fear_greed_index <= 30:
            score = 5
            direction = "bullish"
        elif fear_greed_index >= 80:
            score = 10
            direction = "bearish"  # 极度贪婪，逆向看跌
        elif fear_greed_index >= 70:
            score = 5
            direction = "bearish"

        return score, direction

    def score_technical(
        self,
        technical_snapshot: Optional[TechnicalSnapshot],
        current_price: float,
    ) -> Tuple[float, str, List[str]]:
        """
        技术指标评分 (0-25分)
        返回 (分数, 方向, 触发原因列表)
        """
        if not technical_snapshot:
            return 0.0, "neutral", []
        return score_technical_indicators(technical_snapshot, current_price)

    def compute_total_score(
        self,
        volume_price: Optional[Dict] = None,
        derivatives: Optional[Dict] = None,
        fund_flow: Optional[Dict] = None,
        orderbook: Optional[Dict] = None,
        fear_greed_index: int = 50,
        technical_snapshot: Optional[TechnicalSnapshot] = None,
        current_price: float = 0.0,
    ) -> AnomalyScore:
        """
        计算综合评分
        """
        dimension_scores = {}
        triggers = []
        bullish_votes = 0
        bearish_votes = 0

        # 1. 量价评分
        if volume_price:
            vp_score, vp_dir = self.score_volume_price(
                vol_ratio=volume_price.get("vol_ratio", 1.0),
                price_change_pct=volume_price.get("price_change_pct", 0.0),
                is_divergence=volume_price.get("is_divergence", False),
            )
            dimension_scores["volume_price"] = vp_score
            if vp_score >= 10:
                triggers.append(f"量价异动: 成交量{volume_price.get('vol_ratio', 1):.1f}x, 价格{volume_price.get('price_change_pct', 0):.2f}%")
            if vp_dir == "bullish":
                bullish_votes += 1
            elif vp_dir == "bearish":
                bearish_votes += 1

        # 2. 衍生品评分
        if derivatives:
            deriv_score, deriv_dir = self.score_derivatives(
                funding_rate=derivatives.get("funding_rate", 0.0),
                oi_change_pct=derivatives.get("oi_change_pct", 0.0),
                long_short_ratio=derivatives.get("long_short_ratio", 1.0),
                price_change_pct=derivatives.get("price_change_pct", 0.0),
            )
            dimension_scores["derivatives"] = deriv_score
            if deriv_score >= 10:
                fr = derivatives.get("funding_rate", 0) * 100
                triggers.append(f"衍生品异动: 费率{fr:.4f}%, OI变化{derivatives.get('oi_change_pct', 0):.2f}%")
            if deriv_dir == "bullish":
                bullish_votes += 1
            elif deriv_dir == "bearish":
                bearish_votes += 1

        # 3. 资金流向评分
        if fund_flow:
            flow_score, flow_dir = self.score_fund_flow(
                taker_ratio=fund_flow.get("taker_ratio", 0.5),
                net_inflow_trend=fund_flow.get("net_inflow_trend", "none"),
            )
            dimension_scores["fund_flow"] = flow_score
            if flow_score >= 10:
                triggers.append(f"资金流向: Taker比{fund_flow.get('taker_ratio', 0.5):.2f}")
            if flow_dir == "bullish":
                bullish_votes += 1
            elif flow_dir == "bearish":
                bearish_votes += 1

        # 4. 盘口评分
        if orderbook:
            ob_score, ob_dir = self.score_orderbook(
                imbalance_ratio=orderbook.get("imbalance_ratio", 1.0),
                whale_wall_side=orderbook.get("whale_wall_side"),
                spread_pct=orderbook.get("spread_pct", 0.0),
            )
            dimension_scores["orderbook"] = ob_score
            if ob_score >= 8:
                triggers.append(f"盘口异动: 失衡比{orderbook.get('imbalance_ratio', 1):.2f}")
            if ob_dir == "bullish":
                bullish_votes += 1
            elif ob_dir == "bearish":
                bearish_votes += 1

        # 5. 情绪评分
        sent_score, sent_dir = self.score_sentiment(fear_greed_index)
        dimension_scores["sentiment"] = sent_score
        if sent_score >= 5:
            triggers.append(f"情绪极端: FGI={fear_greed_index}")
        if sent_dir == "bullish":
            bullish_votes += 1
        elif sent_dir == "bearish":
            bearish_votes += 1

        # 6. 技术指标评分
        if technical_snapshot:
            tech_score, tech_dir, tech_triggers = self.score_technical(technical_snapshot, current_price)
            dimension_scores["technical"] = tech_score
            triggers.extend(tech_triggers)
            if tech_dir == "bullish":
                bullish_votes += 1
            elif tech_dir == "bearish":
                bearish_votes += 1

        # 计算加权总分
        total_score = 0.0
        for dim, weight in self.WEIGHTS.items():
            dim_score = dimension_scores.get(dim, 0.0)
            # 将各维度分数标准化到100分制后加权
            max_scores = {"volume_price": 30, "derivatives": 25, "fund_flow": 20, "orderbook": 15, "sentiment": 10, "technical": 25}
            normalized = (dim_score / max_scores.get(dim, 1)) * 100
            total_score += normalized * weight

        # 确定信号级别
        if total_score >= self.THRESHOLDS["alert"]:
            severity = "alert"
        elif total_score >= self.THRESHOLDS["warning"]:
            severity = "warning"
        elif total_score >= self.THRESHOLDS["info"]:
            severity = "info"
        else:
            severity = "none"

        # 确定方向
        if bullish_votes > bearish_votes:
            direction = "bullish"
        elif bearish_votes > bullish_votes:
            direction = "bearish"
        else:
            direction = "neutral"

        return AnomalyScore(
            total_score=round(total_score, 2),
            direction=direction,
            severity=severity,
            dimension_scores=dimension_scores,
            bullish_votes=bullish_votes,
            bearish_votes=bearish_votes,
            triggers=triggers,
        )
