"""
盘口微观结构分析
检测: 买卖失衡、大单墙、流动性枯竭
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from ..config import AnomalyConfig, get_symbol_tier


@dataclass
class OrderBookResult:
    """盘口分析结果"""
    bid_depth: float = 0.0          # 买单深度 (USD)
    ask_depth: float = 0.0          # 卖单深度 (USD)
    imbalance_ratio: float = 1.0    # 买卖失衡率
    spread_pct: float = 0.0         # 价差百分比
    whale_wall: Optional[Dict] = None  # 大单墙信息
    is_imbalanced: bool = False     # 是否失衡
    is_spread_wide: bool = False    # 价差是否过大


class OrderBookFeatures:
    """
    盘口微观结构分析

    检测:
    - 买卖失衡 (>3:1)
    - 大单墙 (>$2M USD)
    - 流动性枯竭 (价差>0.05%)
    """

    def __init__(self, config: Optional[AnomalyConfig] = None):
        cfg = config or AnomalyConfig()
        self.imbalance_threshold = cfg.imbalance_threshold  # 3.0
        self.whale_wall_usd = cfg.whale_wall_usd  # 2,000,000
        self.spread_warn = cfg.spread_warn  # 0.0005 (0.05%)

    def compute(
        self,
        symbol: str,
        bids: List[Tuple[float, float]],  # [(price, qty), ...]
        asks: List[Tuple[float, float]],
        current_price: float,
        depth_pct: float = 1.0,  # 统计 ±1% 范围内的深度
    ) -> OrderBookResult:
        """
        计算盘口特征

        Args:
            symbol: 币种
            bids: 买单列表 [(price, qty), ...]
            asks: 卖单列表 [(price, qty), ...]
            current_price: 当前价格
            depth_pct: 深度统计范围 (%)
        """
        result = OrderBookResult()

        if not bids or not asks or current_price <= 0:
            return result

        # 计算价差
        best_bid = bids[0][0] if bids else 0
        best_ask = asks[0][0] if asks else 0
        if best_bid > 0 and best_ask > 0:
            result.spread_pct = (best_ask - best_bid) / current_price
            result.is_spread_wide = result.spread_pct > self.spread_warn

        # 计算深度范围
        price_range = current_price * (depth_pct / 100)
        min_bid_price = current_price - price_range
        max_ask_price = current_price + price_range

        # 统计买单深度 (USD)
        for price, qty in bids:
            if price >= min_bid_price:
                result.bid_depth += price * qty

        # 统计卖单深度 (USD)
        for price, qty in asks:
            if price <= max_ask_price:
                result.ask_depth += price * qty

        # 计算失衡率
        if result.ask_depth > 0:
            result.imbalance_ratio = result.bid_depth / result.ask_depth
        elif result.bid_depth > 0:
            result.imbalance_ratio = float('inf')

        result.is_imbalanced = (result.imbalance_ratio >= self.imbalance_threshold or
                                result.imbalance_ratio <= 1 / self.imbalance_threshold)

        # 检测大单墙
        result.whale_wall = self._detect_whale_wall(bids, asks, current_price)

        return result

    def _detect_whale_wall(
        self,
        bids: List[Tuple[float, float]],
        asks: List[Tuple[float, float]],
        current_price: float,
    ) -> Optional[Dict]:
        """检测大单墙"""
        # 检查买单墙
        for price, qty in bids:
            usd_value = price * qty
            if usd_value >= self.whale_wall_usd:
                distance_pct = ((current_price - price) / current_price) * 100
                return {
                    "side": "bid",
                    "price": price,
                    "qty": qty,
                    "usd_value": usd_value,
                    "distance_pct": distance_pct,
                }

        # 检查卖单墙
        for price, qty in asks:
            usd_value = price * qty
            if usd_value >= self.whale_wall_usd:
                distance_pct = ((price - current_price) / current_price) * 100
                return {
                    "side": "ask",
                    "price": price,
                    "qty": qty,
                    "usd_value": usd_value,
                    "distance_pct": distance_pct,
                }

        return None

    def detect_signals(self, symbol: str, result: OrderBookResult) -> List[Dict]:
        """检测盘口信号"""
        signals = []

        # 买卖失衡
        if result.is_imbalanced:
            if result.imbalance_ratio > self.imbalance_threshold:
                signals.append({
                    "type": "orderbook_imbalance",
                    "direction": "bullish",
                    "severity": "warning",
                    "description": "买单深度远超卖单，可能有护盘",
                    "triggers": [
                        f"买卖比: {result.imbalance_ratio:.1f}:1",
                        f"买单深度: ${result.bid_depth:,.0f}",
                        f"卖单深度: ${result.ask_depth:,.0f}",
                    ],
                })
            else:
                signals.append({
                    "type": "orderbook_imbalance",
                    "direction": "bearish",
                    "severity": "warning",
                    "description": "卖单深度远超买单，可能有压盘",
                    "triggers": [
                        f"买卖比: 1:{1/result.imbalance_ratio:.1f}",
                        f"买单深度: ${result.bid_depth:,.0f}",
                        f"卖单深度: ${result.ask_depth:,.0f}",
                    ],
                })

        # 大单墙
        if result.whale_wall:
            wall = result.whale_wall
            side_text = "托底" if wall["side"] == "bid" else "压顶"
            direction = "bullish" if wall["side"] == "bid" else "bearish"
            signals.append({
                "type": "whale_wall",
                "direction": direction,
                "severity": "alert",
                "description": f"检测到大单{side_text}",
                "triggers": [
                    f"价格: ${wall['price']:,.2f}",
                    f"金额: ${wall['usd_value']:,.0f}",
                    f"距离: {wall['distance_pct']:.2f}%",
                ],
            })

        # 流动性枯竭
        if result.is_spread_wide:
            signals.append({
                "type": "liquidity_dry",
                "direction": "neutral",
                "severity": "alert",
                "description": "流动性枯竭，价格可能剧烈跳变",
                "triggers": [
                    f"价差: {result.spread_pct*100:.3f}% (>{self.spread_warn*100:.2f}%)",
                ],
            })

        return signals
