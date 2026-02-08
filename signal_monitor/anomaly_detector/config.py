"""
异动检测系统配置
基于专业交易员建议的分层阈值策略
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SymbolTier:
    """币种分层阈值配置"""
    tier: str  # "major" | "alt"
    price_change_5m: float      # 5分钟价格变动阈值 (%)
    vol_ma_ratio: float         # 成交量/MA20 倍数阈值
    divergence_price: float     # 量价背离-价格阈值 (%)
    divergence_vol: float       # 量价背离-成交量倍数
    liquidation_warn: float     # 爆仓量警戒 (USD)
    liquidation_extreme: float  # 爆仓量极端 (USD)


# 币种分层配置
SYMBOL_TIERS: Dict[str, SymbolTier] = {
    # 超大市值 - 更敏感的阈值
    "BTC": SymbolTier("major", 1.8, 4.5, 0.3, 4.0, 5_000_000, 20_000_000),
    "ETH": SymbolTier("major", 1.8, 4.5, 0.3, 4.0, 5_000_000, 20_000_000),
    # 高波动主流币 - 更宽容的阈值
    "SOL": SymbolTier("alt", 3.5, 6.0, 0.6, 5.0, 1_000_000, 4_000_000),
    "BNB": SymbolTier("alt", 3.5, 6.0, 0.6, 5.0, 1_000_000, 4_000_000),
    "DOGE": SymbolTier("alt", 3.5, 6.0, 0.6, 5.0, 1_000_000, 4_000_000),
    "XRP": SymbolTier("alt", 3.5, 6.0, 0.6, 5.0, 1_000_000, 4_000_000),
    "ADA": SymbolTier("alt", 3.5, 6.0, 0.6, 5.0, 1_000_000, 4_000_000),
    "LTC": SymbolTier("alt", 3.5, 6.0, 0.6, 5.0, 1_000_000, 4_000_000),
}

# 默认分层 (未配置的币种)
DEFAULT_TIER = SymbolTier("alt", 3.5, 6.0, 0.6, 5.0, 1_000_000, 4_000_000)


def get_symbol_tier(symbol: str) -> SymbolTier:
    """获取币种的分层配置"""
    return SYMBOL_TIERS.get(symbol.upper(), DEFAULT_TIER)


@dataclass
class AnomalyConfig:
    """异动检测配置"""

    # 监控币种
    symbols: List[str] = field(default_factory=lambda: ["BTC", "ETH", "SOL", "BNB"])

    # 量价检测 (基础阈值，实际使用分层配置)
    vol_spike_threshold: float = 6.0      # 成交量突刺阈值 (MA倍数)
    vol_zscore_threshold: float = 3.5     # 成交量Z-Score阈值
    price_change_threshold: float = 3.5   # 价格变化阈值 (%)

    # 衍生品检测 - 更新为专业阈值
    funding_warn_negative: float = -0.015   # 资金费率警戒负值 (%)
    funding_warn_positive: float = 0.05    # 资金费率警戒正值 (%)
    funding_extreme_negative: float = -0.04  # 资金费率极端负值 (%)
    funding_extreme_positive: float = 0.12    # 资金费率极端正值 (%)
    oi_change_warn: float = 5.0            # 持仓量变化警戒 (%)
    oi_change_extreme: float = 12.0         # 持仓量变化极端 (%)
    oi_change_threshold: float = 5.0       # 兼容旧配置

    # 盘口分析
    imbalance_threshold: float = 4.0       # 买卖失衡率阈值 (3:1)
    whale_wall_usd: float = 4_000_000      # 大单墙阈值 (USD)
    spread_warn: float = 0.001            # 价差警戒 (0.05%)

    # 相关性过滤
    correlation_window_minutes: int = 60     # 相关性计算窗口
    independence_threshold: float = 0.6      # 独立行情阈值 (更新为0.5)

    # 情绪检测
    fear_extreme: int = 20   # 极度恐惧阈值
    greed_extreme: int = 80  # 极度贪婪阈值

    # 动态阈值设置
    use_dynamic_threshold: bool = True     # 启用动态阈值
    zscore_threshold: float = 3.5          # Z-Score 阈值
    atr_multiplier: float = 3.5            # ATR 倍数

    # 多维度加权评分配置
    scoring_enabled: bool = True           # 启用加权评分
    scoring_weights: Dict[str, float] = field(default_factory=lambda: {
        "volume_price": 0.30,
        "derivatives": 0.25,
        "fund_flow": 0.20,
        "orderbook": 0.15,
        "sentiment": 0.10,
    })
    scoring_thresholds: Dict[str, int] = field(default_factory=lambda: {
        "info": 55,
        "warning": 70,
        "alert": 85,
    })

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "symbols": self.symbols,
            "volume_price": {
                "vol_spike_threshold": self.vol_spike_threshold,
                "vol_zscore_threshold": self.vol_zscore_threshold,
                "lookback": 20,
            },
            "derivatives": {
                "funding_warn_negative": self.funding_warn_negative,
                "funding_warn_positive": self.funding_warn_positive,
                "funding_extreme_negative": self.funding_extreme_negative,
                "funding_extreme_positive": self.funding_extreme_positive,
                "oi_change_warn": self.oi_change_warn,
                "oi_change_extreme": self.oi_change_extreme,
                "oi_change_threshold": self.oi_change_threshold,
                "price_change_threshold": self.price_change_threshold,
            },
            "orderbook": {
                "imbalance_threshold": self.imbalance_threshold,
                "whale_wall_usd": self.whale_wall_usd,
                "spread_warn": self.spread_warn,
            },
            "correlation": {
                "window_minutes": self.correlation_window_minutes,
                "independence_threshold": self.independence_threshold,
            },
            "sentiment": {
                "fear_extreme": self.fear_extreme,
                "greed_extreme": self.greed_extreme,
            },
            "dynamic": {
                "enabled": self.use_dynamic_threshold,
                "zscore_threshold": self.zscore_threshold,
                "atr_multiplier": self.atr_multiplier,
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AnomalyConfig":
        """从字典创建"""
        config = cls()
        config.symbols = data.get("symbols", config.symbols)

        vp = data.get("volume_price", {})
        config.vol_spike_threshold = vp.get("vol_spike_threshold", config.vol_spike_threshold)
        config.vol_zscore_threshold = vp.get("vol_zscore_threshold", config.vol_zscore_threshold)

        deriv = data.get("derivatives", {})
        config.funding_warn_negative = deriv.get("funding_warn_negative", config.funding_warn_negative)
        config.funding_warn_positive = deriv.get("funding_warn_positive", config.funding_warn_positive)
        config.funding_extreme_negative = deriv.get("funding_extreme_negative", config.funding_extreme_negative)
        config.funding_extreme_positive = deriv.get("funding_extreme_positive", config.funding_extreme_positive)
        config.oi_change_warn = deriv.get("oi_change_warn", config.oi_change_warn)
        config.oi_change_extreme = deriv.get("oi_change_extreme", config.oi_change_extreme)
        config.oi_change_threshold = deriv.get("oi_change_threshold", config.oi_change_threshold)

        ob = data.get("orderbook", {})
        config.imbalance_threshold = ob.get("imbalance_threshold", config.imbalance_threshold)
        config.whale_wall_usd = ob.get("whale_wall_usd", config.whale_wall_usd)
        config.spread_warn = ob.get("spread_warn", config.spread_warn)

        corr = data.get("correlation", {})
        config.correlation_window_minutes = corr.get("window_minutes", config.correlation_window_minutes)
        config.independence_threshold = corr.get("independence_threshold", config.independence_threshold)

        sent = data.get("sentiment", {})
        config.fear_extreme = sent.get("fear_extreme", config.fear_extreme)
        config.greed_extreme = sent.get("greed_extreme", config.greed_extreme)

        dyn = data.get("dynamic", {})
        config.use_dynamic_threshold = dyn.get("enabled", config.use_dynamic_threshold)
        config.zscore_threshold = dyn.get("zscore_threshold", config.zscore_threshold)
        config.atr_multiplier = dyn.get("atr_multiplier", config.atr_multiplier)

        return config
