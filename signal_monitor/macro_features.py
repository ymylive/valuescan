"""
Multi-timeframe feature engineering for ValuScan QuantRefactorV3
Extracts trend, momentum, volatility, structure, and volume features from 200-kline datasets
"""

import numpy as np
from typing import Dict, List, Any


def validate_klines_input(data: Dict[str, Any]) -> None:
    """Validate multi-timeframe klines input"""
    required_tfs = ["15m", "1h", "4h", "1d"]

    if "asset" not in data:
        raise ValueError("Missing 'asset' field")

    if "timeframes" not in data:
        raise ValueError("Missing 'timeframes' field")

    for tf in required_tfs:
        if tf not in data["timeframes"]:
            raise ValueError(f"Missing timeframe: {tf}")

        klines = data["timeframes"][tf]
        if len(klines) != 200:
            raise ValueError(f"Timeframe {tf} must have exactly 200 klines, got {len(klines)}")


def calculate_ema(prices: List[float], period: int) -> float:
    """Calculate EMA for given period"""
    if len(prices) < period:
        return prices[-1] if prices else 0.0

    multiplier = 2 / (period + 1)
    ema = sum(prices[:period]) / period

    for price in prices[period:]:
        ema = (price - ema) * multiplier + ema

    return ema


def calculate_ema_slope(prices: List[float], period: int, lookback: int = 10) -> float:
    """Calculate EMA slope over lookback period using incremental calculation"""
    if len(prices) < period + lookback:
        return 0.0

    multiplier = 2 / (period + 1)
    ema = sum(prices[:period]) / period
    emas = []

    for i in range(period, len(prices)):
        ema = (prices[i] - ema) * multiplier + ema
        if i >= len(prices) - lookback:
            emas.append(ema)

    if len(emas) < 2:
        return 0.0

    # Linear regression slope
    x = np.arange(len(emas))
    slope = np.polyfit(x, emas, 1)[0]
    return float(slope / emas[0]) if emas[0] != 0 else 0.0


def calculate_adx(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
    """Calculate ADX (Average Directional Index)"""
    if len(highs) < period + 1:
        return 0.0

    tr_list = []
    plus_dm = []
    minus_dm = []

    for i in range(1, len(highs)):
        h_diff = highs[i] - highs[i-1]
        l_diff = lows[i-1] - lows[i]

        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
        tr_list.append(tr)

        plus_dm.append(h_diff if h_diff > l_diff and h_diff > 0 else 0)
        minus_dm.append(l_diff if l_diff > h_diff and l_diff > 0 else 0)

    if len(tr_list) < period:
        return 0.0

    atr = sum(tr_list[-period:]) / period
    plus_di = (sum(plus_dm[-period:]) / period / atr * 100) if atr > 0 else 0
    minus_di = (sum(minus_dm[-period:]) / period / atr * 100) if atr > 0 else 0

    dx = abs(plus_di - minus_di) / (plus_di + minus_di) * 100 if (plus_di + minus_di) > 0 else 0
    return float(dx)


def calculate_rsi(prices: List[float], period: int = 14) -> float:
    """Calculate RSI"""
    if len(prices) < period + 1:
        return 50.0

    changes = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    gains = [c if c > 0 else 0 for c in changes]
    losses = [-c if c < 0 else 0 for c in changes]

    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return float(rsi)


def calculate_macd(prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> float:
    """Calculate MACD histogram"""
    if len(prices) < slow:
        return 0.0

    # Calculate MACD values for all periods
    macd_values = []
    multiplier_fast = 2 / (fast + 1)
    multiplier_slow = 2 / (slow + 1)

    for i in range(slow, len(prices) + 1):
        ema_fast = sum(prices[:fast]) / fast
        for p in prices[fast:i]:
            ema_fast = (p - ema_fast) * multiplier_fast + ema_fast

        ema_slow = sum(prices[:slow]) / slow
        for p in prices[slow:i]:
            ema_slow = (p - ema_slow) * multiplier_slow + ema_slow

        macd_values.append(ema_fast - ema_slow)

    # Signal line is 9-period EMA of MACD
    if len(macd_values) >= signal:
        macd_signal = calculate_ema(macd_values, signal)
    else:
        macd_signal = macd_values[-1] if macd_values else 0.0

    macd_line = macd_values[-1] if macd_values else 0.0
    histogram = macd_line - macd_signal

    return float(histogram)


def calculate_atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
    """Calculate ATR"""
    if len(highs) < period + 1:
        return 0.0

    tr_list = []
    for i in range(1, len(highs)):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
        tr_list.append(tr)

    atr = sum(tr_list[-period:]) / period
    return float(atr)


def calculate_bb_width(prices: List[float], period: int = 20, std_dev: int = 2) -> float:
    """Calculate Bollinger Band width"""
    if len(prices) < period:
        return 0.0

    recent = prices[-period:]
    sma = sum(recent) / period
    variance = sum((p - sma) ** 2 for p in recent) / period
    std = variance ** 0.5

    upper = sma + (std_dev * std)
    lower = sma - (std_dev * std)
    width = (upper - lower) / sma if sma > 0 else 0.0

    return float(width)


def calculate_realized_volatility(prices: List[float], period: int = 20) -> float:
    """Calculate realized volatility"""
    if len(prices) < period + 1:
        return 0.0

    returns = [(prices[i] / prices[i-1] - 1) for i in range(-period, 0)]
    variance = sum(r ** 2 for r in returns) / period
    vol = (variance ** 0.5) * (252 ** 0.5)  # Annualized

    return float(vol)


def detect_structure(highs: List[float], lows: List[float], lookback: int = 20) -> Dict[str, Any]:
    """Detect price structure patterns"""
    if len(highs) < lookback * 2:
        return {
            "higher_highs": False,
            "higher_lows": False,
            "retracement_depth": 0.0,
            "breakout_detected": False
        }

    recent_highs = highs[-lookback:]
    recent_lows = lows[-lookback:]
    prev_highs = highs[-lookback*2:-lookback]
    prev_lows = lows[-lookback*2:-lookback]

    higher_highs = max(recent_highs) > max(prev_highs)
    higher_lows = min(recent_lows) > min(prev_lows)

    swing_high = max(recent_highs)
    swing_low = min(recent_lows)
    current = highs[-1]

    retracement = (swing_high - current) / (swing_high - swing_low) if swing_high > swing_low else 0.0

    breakout = current > max(highs[-lookback:-1]) * 1.02

    return {
        "higher_highs": bool(higher_highs),
        "higher_lows": bool(higher_lows),
        "retracement_depth": float(retracement),
        "breakout_detected": bool(breakout)
    }


def calculate_volume_features(volumes: List[float], period: int = 20) -> Dict[str, Any]:
    """Calculate volume-based features"""
    if len(volumes) < period + 1:
        return {
            "volume_ma_ratio": 1.0,
            "obv_trend": "neutral"
        }

    volume_ma = sum(volumes[-period:]) / period
    current_volume = volumes[-1]
    volume_ratio = current_volume / volume_ma if volume_ma > 0 else 1.0

    # Simple OBV trend
    recent_volumes = volumes[-10:]
    obv_trend = "up" if sum(recent_volumes[-5:]) > sum(recent_volumes[:5]) else "down"
    if abs(sum(recent_volumes[-5:]) - sum(recent_volumes[:5])) / sum(recent_volumes[:5]) < 0.1:
        obv_trend = "neutral"

    return {
        "volume_ma_ratio": float(volume_ratio),
        "obv_trend": obv_trend
    }


def extract_timeframe_features(klines: List[Dict[str, Any]], arrays: Dict[str, List[float]] = None) -> Dict[str, Any]:
    """Extract all features for a single timeframe"""
    if arrays is None:
        closes = [k["close"] for k in klines]
        highs = [k["high"] for k in klines]
        lows = [k["low"] for k in klines]
        volumes = [k["volume"] for k in klines]
    else:
        closes = arrays["closes"]
        highs = arrays["highs"]
        lows = arrays["lows"]
        volumes = arrays["volumes"]

    return {
        "trend": {
            "ema_7_slope": calculate_ema_slope(closes, 7),
            "ema_21_slope": calculate_ema_slope(closes, 21),
            "ema_50_slope": calculate_ema_slope(closes, 50),
            "ema_200_slope": calculate_ema_slope(closes, 200),
            "adx": calculate_adx(highs, lows, closes)
        },
        "momentum": {
            "rsi": calculate_rsi(closes),
            "macd_histogram": calculate_macd(closes),
            "rate_of_change": float((closes[-1] / closes[-20] - 1) * 100) if len(closes) >= 20 else 0.0
        },
        "volatility": {
            "atr": calculate_atr(highs, lows, closes),
            "bb_width": calculate_bb_width(closes),
            "realized_vol": calculate_realized_volatility(closes)
        },
        "structure": detect_structure(highs, lows),
        "volume": calculate_volume_features(volumes)
    }


def compute_macro_features(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main entry point for macro feature extraction

    Args:
        data: Multi-timeframe klines input (see SCHEMAS_V3.md)

    Returns:
        Structured features dict per timeframe
    """
    validate_klines_input(data)

    result = {
        "asset": data["asset"],
        "timeframes": {}
    }

    for tf in ["15m", "1h", "4h", "1d"]:
        klines = data["timeframes"][tf]
        # Pre-extract arrays once
        arrays = {
            "closes": [k["close"] for k in klines],
            "highs": [k["high"] for k in klines],
            "lows": [k["low"] for k in klines],
            "volumes": [k["volume"] for k in klines]
        }
        result["timeframes"][tf] = extract_timeframe_features(klines, arrays)

    return result
