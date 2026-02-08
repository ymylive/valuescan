"""
特征引擎 - 统一特征计算入口
基于专业交易员建议的分层阈值策略
"""

from __future__ import annotations

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field

from ..config import AnomalyConfig
from .volume_price import VolumePriceFeatures, VolumePriceResult
from .derivatives import DerivativesFeatures, DerivativesResult
from .correlation import CorrelationFeatures, CorrelationResult
from .orderbook import OrderBookFeatures, OrderBookResult
from .technical_indicators import TechnicalSnapshot, compute_technical_snapshot


@dataclass
class FeatureSnapshot:
    """特征快照 - 包含所有特征"""
    symbol: str
    timestamp: float = 0.0

    # 量价特征
    volume_price: Optional[VolumePriceResult] = None

    # 衍生品特征
    derivatives: Optional[DerivativesResult] = None

    # 相关性特征
    correlation: Optional[CorrelationResult] = None

    # 盘口特征
    orderbook: Optional[OrderBookResult] = None

    # 技术指标特征
    technical: Optional[TechnicalSnapshot] = None

    # 情绪特征
    fear_greed_index: int = 50

    def to_ml_features(self) -> Dict[str, float]:
        """转换为ML特征向量"""
        features = {}

        if self.volume_price:
            features["vol_zscore"] = self.volume_price.vol_zscore
            features["vol_ma_ratio"] = self.volume_price.vol_ma_ratio
            features["price_change_pct"] = self.volume_price.price_change_pct
            features["vol_spike"] = 1.0 if self.volume_price.vol_spike else 0.0
            features["price_vol_divergence"] = 1.0 if self.volume_price.price_vol_divergence else 0.0

        if self.derivatives:
            features["funding_rate"] = self.derivatives.funding_rate * 100
            features["funding_zscore"] = self.derivatives.funding_zscore
            features["oi_change_pct"] = self.derivatives.oi_change_pct
            features["funding_warn"] = 1.0 if self.derivatives.funding_warn else 0.0
            features["funding_extreme"] = 1.0 if self.derivatives.funding_extreme else 0.0

        if self.correlation:
            features["btc_correlation"] = self.correlation.btc_correlation
            features["beta"] = self.correlation.beta
            features["is_independent"] = 1.0 if self.correlation.is_independent else 0.0

        if self.orderbook:
            features["imbalance_ratio"] = self.orderbook.imbalance_ratio
            features["spread_pct"] = self.orderbook.spread_pct
            features["is_imbalanced"] = 1.0 if self.orderbook.is_imbalanced else 0.0

        features["fear_greed_index"] = self.fear_greed_index

        return features


class FeatureEngine:
    """
    特征引擎 - 支持分层阈值

    统一管理所有特征计算器，提供一站式特征计算
    """

    def __init__(self, config: Optional[AnomalyConfig] = None):
        cfg = config or AnomalyConfig()

        # 初始化各特征计算器 (使用新的配置方式)
        self.volume_price = VolumePriceFeatures(
            lookback=20,
            use_dynamic=cfg.use_dynamic_threshold,
        )

        self.derivatives = DerivativesFeatures(config=cfg)
        self.correlation = CorrelationFeatures(config=cfg)
        self.orderbook = OrderBookFeatures(config=cfg)

    def compute_all(
        self,
        symbol: str,
        volumes: List[float],
        closes: List[float],
        funding_rate: float,
        open_interest: float,
        btc_price: float,
        fear_greed_index: int = 50,
        timestamp: float = 0.0,
        orderbook_bids: Optional[List[Tuple[float, float]]] = None,
        orderbook_asks: Optional[List[Tuple[float, float]]] = None,
        highs: Optional[List[float]] = None,
        lows: Optional[List[float]] = None,
    ) -> FeatureSnapshot:
        """
        计算所有特征

        Args:
            symbol: 币种
            volumes: 成交量序列
            closes: 收盘价序列
            funding_rate: 资金费率
            open_interest: 持仓量
            btc_price: BTC价格
            fear_greed_index: 恐惧贪婪指数
            timestamp: 时间戳
            orderbook_bids: 买单列表 [(price, qty), ...]
            orderbook_asks: 卖单列表 [(price, qty), ...]
            highs: 最高价序列 (用于技术指标)
            lows: 最低价序列 (用于技术指标)
        """
        import time
        snapshot = FeatureSnapshot(symbol=symbol, timestamp=timestamp or time.time())

        current_price = closes[-1] if closes else 0.0

        # 量价特征 (使用分层阈值)
        if volumes and closes:
            snapshot.volume_price = self.volume_price.compute(symbol, volumes, closes)

        # 衍生品特征
        price_change = 0.0
        if snapshot.volume_price:
            price_change = snapshot.volume_price.price_change_pct

        snapshot.derivatives = self.derivatives.compute(
            symbol=symbol,
            funding_rate=funding_rate,
            open_interest=open_interest,
            price_change_pct=price_change,
        )

        # 相关性特征
        snapshot.correlation = self.correlation.compute(
            symbol=symbol,
            price=current_price,
            btc_price=btc_price,
        )

        # 盘口特征
        if orderbook_bids and orderbook_asks and current_price > 0:
            snapshot.orderbook = self.orderbook.compute(
                symbol=symbol,
                bids=orderbook_bids,
                asks=orderbook_asks,
                current_price=current_price,
            )

        # 情绪特征
        snapshot.fear_greed_index = fear_greed_index

        # 技术指标特征
        if closes and len(closes) >= 30:
            snapshot.technical = compute_technical_snapshot(
                closes=closes,
                highs=highs,
                lows=lows,
                volumes=volumes,
            )

        return snapshot
