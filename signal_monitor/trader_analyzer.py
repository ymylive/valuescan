"""
交易员数据分析模块
计算核心指标、风格分类、保证金行为检测
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum


class TradingStyle(Enum):
    AGGRESSIVE = "aggressive"
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"


class HoldingStyle(Enum):
    SCALPER = "scalper"
    DAY_TRADER = "day_trader"
    SWING_TRADER = "swing_trader"
    POSITION_TRADER = "position_trader"


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


class MarginBehavior(Enum):
    RARE = "rare"
    OCCASIONAL = "occasional"
    FREQUENT = "frequent"
    EXCESSIVE = "excessive"


@dataclass
class TraderMetrics:
    """交易员分析指标"""
    # 基础信息
    portfolio_id: str
    nickname: str
    follower_count: int = 0
    aum: float = 0.0

    # 表现指标
    roi_7d: float = 0.0
    roi_30d: float = 0.0
    roi_90d: float = 0.0
    total_roi: float = 0.0
    win_rate: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    profit_factor: float = 0.0

    # 交易风格指标
    trade_count: int = 0
    avg_holding_hours: float = 0.0
    trade_frequency: float = 0.0  # 每日交易次数
    avg_leverage: float = 0.0
    max_leverage: float = 0.0
    preferred_pairs: List[str] = field(default_factory=list)
    coin_distribution: List[Dict] = field(default_factory=list)  # 币种分布百分比
    long_ratio: float = 0.5

    # 风险指标
    margin_addition_count: int = 0
    margin_addition_ratio: float = 0.0  # 保证金添加比例
    stop_loss_usage_rate: float = 0.0
    avg_position_size: float = 0.0
    max_position_size: float = 0.0

    # 分类结果
    trading_style: str = ""
    holding_style: str = ""
    risk_level: str = ""
    risk_score: int = 0
    margin_behavior: str = ""
    margin_concern_level: str = ""


@dataclass
class AnalysisResult:
    """分析结果"""
    metrics: TraderMetrics
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)
    summary: str = ""


class TraderAnalyzer:
    """交易员分析器"""

    def analyze(self, trader_data) -> AnalysisResult:
        """分析交易员数据"""
        from .binance_copytrade_api import TraderData

        if not isinstance(trader_data, TraderData):
            raise ValueError("Invalid trader data")

        metrics = self._calculate_metrics(trader_data)
        self._classify_styles(metrics)
        self._assess_risk(metrics)
        self._analyze_margin_behavior(metrics, trader_data)

        result = AnalysisResult(metrics=metrics)
        self._identify_strengths_weaknesses(result)
        self._generate_summary(result)

        return result

    def _calculate_metrics(self, data) -> TraderMetrics:
        """计算核心指标"""
        metrics = TraderMetrics(
            portfolio_id=data.portfolio_id,
            nickname=data.nickname,
            follower_count=data.follower_count,
            aum=data.aum,
            roi_7d=data.roi_7d,
            roi_30d=data.roi_30d,
            roi_90d=data.roi_90d,
            total_roi=data.total_roi,
            win_rate=data.win_rate,
            max_drawdown=data.max_drawdown,
            sharpe_ratio=data.sharpe_ratio,
            trade_count=data.trade_count,
            avg_holding_hours=data.avg_holding_hours,
            avg_leverage=data.avg_leverage,
            preferred_pairs=data.preferred_pairs,
            coin_distribution=data.coin_distribution,
            long_ratio=data.long_ratio,
        )

        # 计算交易频率（假设90天数据）
        if data.trade_count > 0:
            metrics.trade_frequency = data.trade_count / 90.0

        # 计算保证金添加比例
        if data.margin_additions and data.trade_count > 0:
            metrics.margin_addition_count = len(data.margin_additions)
            metrics.margin_addition_ratio = len(data.margin_additions) / data.trade_count

        # 从交易历史计算更多指标
        if data.trade_history:
            self._analyze_trade_history(metrics, data.trade_history)

        return metrics

    def _analyze_trade_history(self, metrics: TraderMetrics, trades: List[Dict]):
        """分析交易历史"""
        if not trades:
            return

        leverages = []
        position_sizes = []
        wins = 0
        losses = 0
        total_profit = 0.0
        total_loss = 0.0

        for trade in trades:
            # 杠杆
            lev = float(trade.get("leverage", 0))
            if lev > 0:
                leverages.append(lev)

            # 仓位大小 - 支持多种字段名
            size = float(trade.get("positionSize") or trade.get("quantity") or trade.get("maxOpenInterest") or trade.get("closedVolume") or 0)
            if size > 0:
                position_sizes.append(size)

            # 盈亏 - 支持多种字段名: closingPnl, pnl, realizedPnl
            pnl = float(trade.get("closingPnl") or trade.get("pnl") or trade.get("realizedPnl") or 0)
            if pnl > 0:
                wins += 1
                total_profit += pnl
            elif pnl < 0:
                losses += 1
                total_loss += abs(pnl)

            # 止损检测
            close_type = trade.get("closeType", "").upper()
            if "STOP" in close_type or "SL" in close_type:
                metrics.stop_loss_usage_rate += 1

        # 计算统计值
        if leverages:
            metrics.max_leverage = max(leverages)
        if position_sizes:
            metrics.avg_position_size = sum(position_sizes) / len(position_sizes)
            metrics.max_position_size = max(position_sizes)
        if trades:
            metrics.stop_loss_usage_rate /= len(trades)

        # 盈亏比
        if total_loss > 0:
            metrics.profit_factor = total_profit / total_loss

    def _classify_styles(self, metrics: TraderMetrics):
        """分类交易风格"""
        # 持仓风格
        hours = metrics.avg_holding_hours
        if hours < 1:
            metrics.holding_style = HoldingStyle.SCALPER.value
        elif hours < 24:
            metrics.holding_style = HoldingStyle.DAY_TRADER.value
        elif hours < 168:  # 7天
            metrics.holding_style = HoldingStyle.SWING_TRADER.value
        else:
            metrics.holding_style = HoldingStyle.POSITION_TRADER.value

        # 交易风格
        if metrics.avg_leverage > 20 or metrics.trade_frequency > 10:
            metrics.trading_style = TradingStyle.AGGRESSIVE.value
        elif metrics.avg_leverage < 5 and metrics.win_rate > 0.6:
            metrics.trading_style = TradingStyle.CONSERVATIVE.value
        else:
            metrics.trading_style = TradingStyle.BALANCED.value

    def _assess_risk(self, metrics: TraderMetrics):
        """评估风险等级"""
        score = 0

        # 杠杆风险 (0-30分)
        if metrics.avg_leverage > 20:
            score += 30
        elif metrics.avg_leverage > 10:
            score += 20
        elif metrics.avg_leverage > 5:
            score += 10

        # 回撤风险 (0-25分)
        if metrics.max_drawdown > 30:
            score += 25
        elif metrics.max_drawdown > 20:
            score += 15
        elif metrics.max_drawdown > 10:
            score += 8

        # 保证金添加风险 (0-25分) - 重点！
        if metrics.margin_addition_ratio > 0.2:
            score += 25
        elif metrics.margin_addition_ratio > 0.1:
            score += 18
        elif metrics.margin_addition_ratio > 0.05:
            score += 10

        # 止损纪律 (0-20分)
        if metrics.stop_loss_usage_rate < 0.1:
            score += 20
        elif metrics.stop_loss_usage_rate < 0.3:
            score += 10

        metrics.risk_score = min(score, 100)

        # 风险等级
        if score >= 60:
            metrics.risk_level = RiskLevel.EXTREME.value
        elif score >= 40:
            metrics.risk_level = RiskLevel.HIGH.value
        elif score >= 20:
            metrics.risk_level = RiskLevel.MEDIUM.value
        else:
            metrics.risk_level = RiskLevel.LOW.value

    def _analyze_margin_behavior(self, metrics: TraderMetrics, data):
        """分析保证金行为 - 关键指标"""
        ratio = metrics.margin_addition_ratio

        if ratio > 0.2:
            metrics.margin_behavior = MarginBehavior.EXCESSIVE.value
            metrics.margin_concern_level = "high"
        elif ratio > 0.1:
            metrics.margin_behavior = MarginBehavior.FREQUENT.value
            metrics.margin_concern_level = "high"
        elif ratio > 0.05:
            metrics.margin_behavior = MarginBehavior.OCCASIONAL.value
            metrics.margin_concern_level = "medium"
        else:
            metrics.margin_behavior = MarginBehavior.RARE.value
            metrics.margin_concern_level = "low" if ratio > 0 else "none"

    def _identify_strengths_weaknesses(self, result: AnalysisResult):
        """识别优势和劣势"""
        m = result.metrics

        # 优势
        if m.win_rate > 0.6:
            result.strengths.append("高胜率交易")
        if m.sharpe_ratio > 1.5:
            result.strengths.append("优秀的风险调整收益")
        if m.max_drawdown < 15:
            result.strengths.append("良好的回撤控制")
        if m.stop_loss_usage_rate > 0.5:
            result.strengths.append("严格的止损纪律")
        if m.margin_behavior == MarginBehavior.RARE.value:
            result.strengths.append("无频繁加保证金行为")
        if m.profit_factor > 2:
            result.strengths.append("高盈亏比")
        if m.follower_count > 1000:
            result.strengths.append("大量跟随者信任")

        # 劣势
        if m.win_rate < 0.4:
            result.weaknesses.append("胜率偏低")
        if m.max_drawdown > 30:
            result.weaknesses.append("最大回撤过大")
        if m.avg_leverage > 20:
            result.weaknesses.append("杠杆使用过高")
        if m.stop_loss_usage_rate < 0.2:
            result.weaknesses.append("止损使用不足")
        if len(m.preferred_pairs) < 3:
            result.weaknesses.append("交易品种单一")

        # 风险因素
        if m.margin_addition_ratio > 0.1:
            result.risk_factors.append(f"频繁添加保证金 ({m.margin_addition_ratio:.1%})")
        if m.max_leverage > 50:
            result.risk_factors.append(f"极端杠杆使用 (最高{m.max_leverage}x)")
        if m.max_drawdown > 40:
            result.risk_factors.append(f"历史大幅回撤 ({m.max_drawdown:.1f}%)")

    def _generate_summary(self, result: AnalysisResult):
        """生成摘要"""
        m = result.metrics

        style_cn = {
            "aggressive": "激进型",
            "conservative": "稳健型",
            "balanced": "均衡型",
        }
        holding_cn = {
            "scalper": "超短线",
            "day_trader": "日内",
            "swing_trader": "波段",
            "position_trader": "中长线",
        }
        risk_cn = {
            "low": "低",
            "medium": "中等",
            "high": "高",
            "extreme": "极高",
        }

        result.summary = (
            f"{m.nickname} 是一位{style_cn.get(m.trading_style, '均衡型')}"
            f"{holding_cn.get(m.holding_style, '波段')}交易员，"
            f"90天收益率 {m.roi_90d:.1f}%，胜率 {m.win_rate:.1%}，"
            f"最大回撤 {m.max_drawdown:.1f}%。"
            f"风险等级：{risk_cn.get(m.risk_level, '中等')}。"
        )

        if m.margin_addition_ratio > 0.05:
            result.summary += f" 注意：存在保证金添加行为 ({m.margin_addition_ratio:.1%})。"


def analyze_trader(trader_data) -> AnalysisResult:
    """便捷函数：分析交易员"""
    return TraderAnalyzer().analyze(trader_data)
