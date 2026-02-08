"""
技术指标计算模块 - 用于异动检测
包含RSI、MACD、布林带、ATR等专业指标
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass


@dataclass
class TechnicalSnapshot:
    """技术指标快照"""
    # 趋势指标
    ema7: float = 0.0
    ema21: float = 0.0
    ema50: float = 0.0
    ema200: float = 0.0
    ema_trend: str = "neutral"  # bullish/bearish/neutral

    # 动量指标
    rsi: float = 50.0
    rsi_divergence: str = "none"  # bullish/bearish/none
    macd: float = 0.0
    macd_signal: float = 0.0
    macd_histogram: float = 0.0
    macd_cross: str = "none"  # golden/death/none

    # 波动率指标
    bb_upper: float = 0.0
    bb_middle: float = 0.0
    bb_lower: float = 0.0
    bb_width: float = 0.0
    bb_position: str = "middle"  # above_upper/below_lower/middle
    atr: float = 0.0
    atr_pct: float = 0.0

    # 成交量指标
    volume_ma20: float = 0.0
    volume_ratio: float = 1.0
    obv_trend: str = "neutral"  # up/down/neutral

    # 价格结构
    higher_high: bool = False
    higher_low: bool = False
    lower_high: bool = False
    lower_low: bool = False


def calculate_ema(prices: List[float], period: int) -> float:
    """计算EMA"""
    if len(prices) < period:
        return prices[-1] if prices else 0.0

    multiplier = 2 / (period + 1)
    ema = sum(prices[:period]) / period

    for price in prices[period:]:
        ema = (price - ema) * multiplier + ema

    return ema


def calculate_rsi(prices: List[float], period: int = 14) -> float:
    """计算RSI"""
    if len(prices) < period + 1:
        return 50.0

    deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]

    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def calculate_macd(prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[float, float, float]:
    """计算MACD"""
    if len(prices) < slow:
        return 0.0, 0.0, 0.0

    ema_fast = calculate_ema(prices, fast)
    ema_slow = calculate_ema(prices, slow)
    macd_line = ema_fast - ema_slow

    # 计算信号线需要历史MACD值
    macd_values = []
    for i in range(slow, len(prices) + 1):
        subset = prices[:i]
        ef = calculate_ema(subset, fast)
        es = calculate_ema(subset, slow)
        macd_values.append(ef - es)

    signal_line = calculate_ema(macd_values, signal) if len(macd_values) >= signal else macd_line
    histogram = macd_line - signal_line

    return macd_line, signal_line, histogram


def calculate_bollinger_bands(prices: List[float], period: int = 20, std_dev: float = 2.0) -> Tuple[float, float, float, float]:
    """计算布林带"""
    if len(prices) < period:
        return prices[-1], prices[-1], prices[-1], 0.0

    recent = prices[-period:]
    middle = sum(recent) / period
    std = np.std(recent)

    upper = middle + std_dev * std
    lower = middle - std_dev * std
    width = (upper - lower) / middle * 100  # 带宽百分比

    return upper, middle, lower, width


def calculate_atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
    """计算ATR"""
    if len(closes) < period + 1:
        return 0.0

    true_ranges = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i-1]),
            abs(lows[i] - closes[i-1])
        )
        true_ranges.append(tr)

    return sum(true_ranges[-period:]) / period


def detect_divergence(prices: List[float], indicator: List[float], lookback: int = 14) -> str:
    """检测背离"""
    if len(prices) < lookback or len(indicator) < lookback:
        return "none"

    recent_prices = prices[-lookback:]
    recent_indicator = indicator[-lookback:]

    # 找价格高低点
    price_high_idx = recent_prices.index(max(recent_prices))
    price_low_idx = recent_prices.index(min(recent_prices))

    # 找指标高低点
    ind_high_idx = recent_indicator.index(max(recent_indicator))
    ind_low_idx = recent_indicator.index(min(recent_indicator))

    # 看涨背离：价格创新低但指标未创新低
    if price_low_idx > lookback // 2 and ind_low_idx < lookback // 2:
        if recent_prices[-1] < recent_prices[0] and recent_indicator[-1] > recent_indicator[0]:
            return "bullish"

    # 看跌背离：价格创新高但指标未创新高
    if price_high_idx > lookback // 2 and ind_high_idx < lookback // 2:
        if recent_prices[-1] > recent_prices[0] and recent_indicator[-1] < recent_indicator[0]:
            return "bearish"

    return "none"


def analyze_price_structure(highs: List[float], lows: List[float], lookback: int = 10) -> Dict[str, bool]:
    """分析价格结构（高低点）"""
    if len(highs) < lookback or len(lows) < lookback:
        return {"higher_high": False, "higher_low": False, "lower_high": False, "lower_low": False}

    recent_highs = highs[-lookback:]
    recent_lows = lows[-lookback:]

    # 找最近的两个高点和低点
    mid = lookback // 2

    first_high = max(recent_highs[:mid])
    second_high = max(recent_highs[mid:])
    first_low = min(recent_lows[:mid])
    second_low = min(recent_lows[mid:])

    return {
        "higher_high": second_high > first_high,
        "higher_low": second_low > first_low,
        "lower_high": second_high < first_high,
        "lower_low": second_low < first_low,
    }


def calculate_obv_trend(closes: List[float], volumes: List[float], lookback: int = 20) -> str:
    """计算OBV趋势"""
    if len(closes) < lookback or len(volumes) < lookback:
        return "neutral"

    obv = 0
    obv_values = []

    for i in range(1, len(closes)):
        if closes[i] > closes[i-1]:
            obv += volumes[i]
        elif closes[i] < closes[i-1]:
            obv -= volumes[i]
        obv_values.append(obv)

    if len(obv_values) < lookback:
        return "neutral"

    recent_obv = obv_values[-lookback:]
    obv_change = recent_obv[-1] - recent_obv[0]

    if obv_change > 0:
        return "up"
    elif obv_change < 0:
        return "down"
    return "neutral"


def compute_technical_snapshot(
    closes: List[float],
    highs: Optional[List[float]] = None,
    lows: Optional[List[float]] = None,
    volumes: Optional[List[float]] = None,
) -> TechnicalSnapshot:
    """计算完整的技术指标快照"""
    if not closes or len(closes) < 30:
        return TechnicalSnapshot()

    current_price = closes[-1]
    highs = highs or closes
    lows = lows or closes
    volumes = volumes or [1.0] * len(closes)

    snapshot = TechnicalSnapshot()

    # EMA
    snapshot.ema7 = calculate_ema(closes, 7)
    snapshot.ema21 = calculate_ema(closes, 21)
    snapshot.ema50 = calculate_ema(closes, 50) if len(closes) >= 50 else snapshot.ema21
    snapshot.ema200 = calculate_ema(closes, 200) if len(closes) >= 200 else snapshot.ema50

    # EMA趋势判断
    if snapshot.ema7 > snapshot.ema21 > snapshot.ema50:
        snapshot.ema_trend = "bullish"
    elif snapshot.ema7 < snapshot.ema21 < snapshot.ema50:
        snapshot.ema_trend = "bearish"
    else:
        snapshot.ema_trend = "neutral"

    # RSI
    snapshot.rsi = calculate_rsi(closes)

    # RSI背离
    rsi_values = []
    for i in range(14, len(closes) + 1):
        rsi_values.append(calculate_rsi(closes[:i]))
    if len(rsi_values) >= 14:
        snapshot.rsi_divergence = detect_divergence(closes[-14:], rsi_values[-14:])

    # MACD
    snapshot.macd, snapshot.macd_signal, snapshot.macd_histogram = calculate_macd(closes)

    # MACD交叉
    if len(closes) >= 27:
        prev_macd, prev_signal, _ = calculate_macd(closes[:-1])
        if prev_macd < prev_signal and snapshot.macd > snapshot.macd_signal:
            snapshot.macd_cross = "golden"
        elif prev_macd > prev_signal and snapshot.macd < snapshot.macd_signal:
            snapshot.macd_cross = "death"

    # 布林带
    snapshot.bb_upper, snapshot.bb_middle, snapshot.bb_lower, snapshot.bb_width = calculate_bollinger_bands(closes)

    if current_price > snapshot.bb_upper:
        snapshot.bb_position = "above_upper"
    elif current_price < snapshot.bb_lower:
        snapshot.bb_position = "below_lower"
    else:
        snapshot.bb_position = "middle"

    # ATR
    snapshot.atr = calculate_atr(highs, lows, closes)
    snapshot.atr_pct = (snapshot.atr / current_price * 100) if current_price > 0 else 0

    # 成交量
    snapshot.volume_ma20 = sum(volumes[-20:]) / min(20, len(volumes))
    snapshot.volume_ratio = volumes[-1] / snapshot.volume_ma20 if snapshot.volume_ma20 > 0 else 1.0

    # OBV趋势
    snapshot.obv_trend = calculate_obv_trend(closes, volumes)

    # 价格结构
    structure = analyze_price_structure(highs, lows)
    snapshot.higher_high = structure["higher_high"]
    snapshot.higher_low = structure["higher_low"]
    snapshot.lower_high = structure["lower_high"]
    snapshot.lower_low = structure["lower_low"]

    return snapshot


def score_technical_indicators(snapshot: TechnicalSnapshot, current_price: float) -> Tuple[float, str, List[str]]:
    """
    技术指标评分 (0-25分)
    返回: (分数, 方向, 触发原因列表)
    """
    score = 0.0
    bullish = 0
    bearish = 0
    triggers = []

    # 1. RSI评分 (0-8分)
    if snapshot.rsi >= 80:
        score += 8
        bearish += 1
        triggers.append(f"RSI超买: {snapshot.rsi:.1f}")
    elif snapshot.rsi >= 70:
        score += 5
        bearish += 1
        triggers.append(f"RSI偏高: {snapshot.rsi:.1f}")
    elif snapshot.rsi <= 20:
        score += 8
        bullish += 1
        triggers.append(f"RSI超卖: {snapshot.rsi:.1f}")
    elif snapshot.rsi <= 30:
        score += 5
        bullish += 1
        triggers.append(f"RSI偏低: {snapshot.rsi:.1f}")

    # RSI背离加分
    if snapshot.rsi_divergence == "bullish":
        score += 3
        bullish += 1
        triggers.append("RSI看涨背离")
    elif snapshot.rsi_divergence == "bearish":
        score += 3
        bearish += 1
        triggers.append("RSI看跌背离")

    # 2. MACD评分 (0-6分)
    if snapshot.macd_cross == "golden":
        score += 6
        bullish += 1
        triggers.append("MACD金叉")
    elif snapshot.macd_cross == "death":
        score += 6
        bearish += 1
        triggers.append("MACD死叉")
    elif abs(snapshot.macd_histogram) > abs(snapshot.macd) * 0.5:
        score += 3
        if snapshot.macd_histogram > 0:
            bullish += 1
        else:
            bearish += 1

    # 3. 布林带评分 (0-6分)
    if snapshot.bb_position == "above_upper":
        score += 6
        bearish += 1
        triggers.append("突破布林上轨")
    elif snapshot.bb_position == "below_lower":
        score += 6
        bullish += 1
        triggers.append("跌破布林下轨")

    # 布林带收窄（即将突破）
    if snapshot.bb_width < 3:
        score += 3
        triggers.append(f"布林带收窄: {snapshot.bb_width:.1f}%")

    # 4. EMA趋势评分 (0-5分)
    if snapshot.ema_trend == "bullish":
        score += 3
        bullish += 1
    elif snapshot.ema_trend == "bearish":
        score += 3
        bearish += 1

    # 价格与EMA200的偏离
    if snapshot.ema200 > 0:
        deviation = (current_price - snapshot.ema200) / snapshot.ema200 * 100
        if abs(deviation) > 20:
            score += 5
            triggers.append(f"偏离EMA200: {deviation:.1f}%")
            if deviation > 0:
                bearish += 1  # 过度偏离可能回归
            else:
                bullish += 1

    # 确定方向
    if bullish > bearish:
        direction = "bullish"
    elif bearish > bullish:
        direction = "bearish"
    else:
        direction = "neutral"

    return min(score, 25), direction, triggers
