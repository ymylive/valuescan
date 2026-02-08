"""
相关性特征计算器
识别独立行情 - 过滤大盘联动
基于专业建议: BTC相关性 < 0.5 = 独立行情
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import time

from ..config import AnomalyConfig


@dataclass
class CorrelationResult:
    """相关性特征结果"""
    btc_correlation: float = 0.0
    is_independent: bool = False
    beta: float = 0.0


class CorrelationFeatures:
    """
    相关性特征计算器

    识别独立行情:
    - 与BTC相关性 < 0.5 时标记为独立行情 (专业建议)
    - 独立行情 = Smart Money行为
    """

    def __init__(self, config: Optional[AnomalyConfig] = None):
        cfg = config or AnomalyConfig()
        self.window_minutes = cfg.correlation_window_minutes  # 60分钟
        self.independence_threshold = cfg.independence_threshold  # 0.5 (更新)
        self.min_samples = 10

        # 价格历史缓存 {symbol: [(timestamp, price), ...]}
        self._price_history: Dict[str, List[Tuple[float, float]]] = {}
        self._window_sec = self.window_minutes * 60

    def update_price(self, symbol: str, price: float) -> None:
        """更新价格历史"""
        now = time.time()
        if symbol not in self._price_history:
            self._price_history[symbol] = []

        self._price_history[symbol].append((now, price))

        # 清理过期数据
        self._price_history[symbol] = [
            (t, p) for t, p in self._price_history[symbol]
            if now - t <= self._window_sec
        ]

    def _get_returns(self, symbol: str) -> List[float]:
        """计算收益率序列"""
        history = self._price_history.get(symbol, [])
        if len(history) < 2:
            return []

        returns = []
        for i in range(1, len(history)):
            prev_price = history[i - 1][1]
            curr_price = history[i][1]
            if prev_price > 0:
                ret = (curr_price - prev_price) / prev_price
                returns.append(ret)

        return returns

    def compute_correlation(self, symbol: str, btc_symbol: str = "BTC") -> float:
        """
        计算与BTC的滚动相关系数

        使用皮尔逊相关系数
        """
        target_returns = self._get_returns(symbol)
        btc_returns = self._get_returns(btc_symbol)

        if len(target_returns) < 5 or len(btc_returns) < 5:
            return 0.0

        # 对齐长度
        min_len = min(len(target_returns), len(btc_returns))
        target_returns = target_returns[-min_len:]
        btc_returns = btc_returns[-min_len:]

        # 计算皮尔逊相关系数
        n = len(target_returns)
        if n < 2:
            return 0.0

        mean_x = sum(target_returns) / n
        mean_y = sum(btc_returns) / n

        numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(target_returns, btc_returns))

        sum_sq_x = sum((x - mean_x) ** 2 for x in target_returns)
        sum_sq_y = sum((y - mean_y) ** 2 for y in btc_returns)

        denominator = (sum_sq_x * sum_sq_y) ** 0.5

        if denominator == 0:
            return 0.0

        return numerator / denominator

    def compute_beta(self, symbol: str, btc_symbol: str = "BTC") -> float:
        """
        计算Beta系数

        Beta = Cov(target, btc) / Var(btc)
        """
        target_returns = self._get_returns(symbol)
        btc_returns = self._get_returns(btc_symbol)

        if len(target_returns) < 5 or len(btc_returns) < 5:
            return 1.0

        min_len = min(len(target_returns), len(btc_returns))
        target_returns = target_returns[-min_len:]
        btc_returns = btc_returns[-min_len:]

        n = len(target_returns)
        if n < 2:
            return 1.0

        mean_x = sum(target_returns) / n
        mean_y = sum(btc_returns) / n

        covariance = sum((x - mean_x) * (y - mean_y) for x, y in zip(target_returns, btc_returns)) / n
        variance_y = sum((y - mean_y) ** 2 for y in btc_returns) / n

        if variance_y == 0:
            return 1.0

        return covariance / variance_y

    def compute(self, symbol: str, price: float, btc_price: float) -> CorrelationResult:
        """
        计算相关性特征

        Args:
            symbol: 目标币种
            price: 当前价格
            btc_price: BTC当前价格

        Returns:
            CorrelationResult
        """
        symbol = symbol.upper()
        # 更新价格历史
        self.update_price(symbol, price)
        self.update_price("BTC", btc_price)

        result = CorrelationResult()
        if symbol == "BTC":
            result.btc_correlation = 1.0
            result.beta = 1.0
            result.is_independent = False
            return result
        target_returns = self._get_returns(symbol)
        btc_returns = self._get_returns("BTC")
        has_history = len(target_returns) >= self.min_samples and len(btc_returns) >= self.min_samples
        if has_history:
            result.btc_correlation = self.compute_correlation(symbol)
            result.beta = self.compute_beta(symbol)
            result.is_independent = abs(result.btc_correlation) < self.independence_threshold
        else:
            result.btc_correlation = 0.0
            result.beta = 1.0
            result.is_independent = False

        return result

    def is_independent_move(self, symbol: str, has_anomaly: bool) -> bool:
        """
        判断是否为独立行情

        条件:
        1. 检测到异动信号
        2. 与BTC相关性 < threshold

        Returns:
            True = 独立行情 (Smart Money行为)
            False = 大盘联动 (可过滤)
        """
        if not has_anomaly:
            return False

        symbol = symbol.upper()
        if symbol == "BTC":
            return False

        target_returns = self._get_returns(symbol)
        btc_returns = self._get_returns("BTC")
        if len(target_returns) < self.min_samples or len(btc_returns) < self.min_samples:
            return False
        correlation = self.compute_correlation(symbol)
        return abs(correlation) < self.independence_threshold
