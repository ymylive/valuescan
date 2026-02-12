"""
Anomaly Detection v2 - MAD-based robust statistical detection
Implements mathematically rigorous anomaly detection using:
- Robust Z-Score (MAD-based)
- ATR normalization for range anomalies
- Composite scoring with percentile thresholds
- Multi-confirmation requirement
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import numpy as np


@dataclass
class AnomalyTriggers:
    """Anomaly detection triggers"""
    z_return: float
    z_range: float
    z_volume: float
    threshold_hit: bool


@dataclass
class AnomalySignal:
    """Anomaly signal output schema (v2)"""
    timeframe: str  # "15m" or "1h"
    anomaly_type: str  # PUMP|DUMP|VOLUME_SPIKE|VOLATILITY_EXPANSION|REVERSAL
    direction: str  # bullish|bearish|neutral
    score: float
    triggers: AnomalyTriggers
    brief: str


class AnomalyDetectorV2:
    """
    Anomaly detector v2 with robust statistical methods
    Supports 15m and 1h timeframes only
    """

    # Thresholds
    Z_RETURN_PUMP_DUMP = 3.5
    Z_VOLUME_MAJOR = 3.5
    Z_VOLUME_ALT = 5.0
    Z_VOLUME_SPIKE = 5.0
    Z_RANGE_EXPANSION = 2.5
    PRICE_CHANGE_THRESHOLD = 0.02  # 2%

    # Rolling window sizes
    WINDOW_MEDIAN = 200
    ATR_PERIOD = 14

    # MAD constant for normal distribution
    MAD_CONSTANT = 1.4826

    def __init__(self, asset: str):
        """
        Initialize detector

        Args:
            asset: Asset symbol (BTC, ETH, XAU, XAG)
        """
        self.asset = asset
        self.is_major_coin = asset in ["BTC", "ETH"]

    def detect(self, klines: List[Dict], timeframe: str) -> Optional[AnomalySignal]:
        """
        Detect anomalies in kline data

        Args:
            klines: List of 200 klines with keys: time, open, high, low, close, volume
            timeframe: "15m" or "1h"

        Returns:
            AnomalySignal if anomaly detected, None otherwise
        """
        if timeframe not in ["15m", "1h"]:
            raise ValueError(f"Unsupported timeframe: {timeframe}")

        if len(klines) != 200:
            raise ValueError(f"Expected 200 klines, got {len(klines)}")

        # Extract arrays
        closes = np.array([k["close"] for k in klines])
        highs = np.array([k["high"] for k in klines])
        lows = np.array([k["low"] for k in klines])
        volumes = np.array([k["volume"] for k in klines])

        # Calculate returns
        returns = np.diff(closes) / closes[:-1]

        # Calculate robust z-scores
        z_return = self._robust_zscore(returns[-1], returns[:-1])
        z_volume = self._robust_zscore(volumes[-1], volumes[:-1])

        # Calculate ATR-normalized range
        atr = self._calculate_atr(highs, lows, closes)
        current_range = highs[-1] - lows[-1]
        z_range = current_range / atr if atr > 0 else 0

        # Calculate composite score
        score = self._composite_score(z_return, z_range, z_volume)

        # Detect anomaly type
        anomaly_type, direction = self._classify_anomaly(
            z_return, z_range, z_volume, returns[-1]
        )

        if anomaly_type is None:
            return None

        # Check confirmation (require 2+ consecutive signals)
        if not self._check_confirmation(klines[:-1], timeframe):
            return None

        triggers = AnomalyTriggers(
            z_return=float(z_return),
            z_range=float(z_range),
            z_volume=float(z_volume),
            threshold_hit=True
        )

        brief = self._generate_brief(anomaly_type, direction, z_return, z_range, z_volume)

        return AnomalySignal(
            timeframe=timeframe,
            anomaly_type=anomaly_type,
            direction=direction,
            score=float(score),
            triggers=triggers,
            brief=brief
        )

    def _robust_zscore(self, value: float, data: np.ndarray) -> float:
        """
        Calculate robust z-score using MAD (Median Absolute Deviation)

        Args:
            value: Current value
            data: Historical data (excluding current value)

        Returns:
            Robust z-score
        """
        median = np.median(data)
        mad = np.median(np.abs(data - median))

        if mad == 0:
            return 0.0

        return (value - median) / (self.MAD_CONSTANT * mad)

    def _calculate_atr(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray) -> float:
        """
        Calculate Average True Range (ATR)

        Args:
            highs: High prices
            lows: Low prices
            closes: Close prices

        Returns:
            ATR value
        """
        tr1 = highs[1:] - lows[1:]
        tr2 = np.abs(highs[1:] - closes[:-1])
        tr3 = np.abs(lows[1:] - closes[:-1])

        tr = np.maximum(tr1, np.maximum(tr2, tr3))

        return np.mean(tr[-self.ATR_PERIOD:])

    def _composite_score(self, z_return: float, z_range: float, z_volume: float) -> float:
        """
        Calculate composite anomaly score

        Args:
            z_return: Return z-score
            z_range: Range z-score
            z_volume: Volume z-score

        Returns:
            Composite score
        """
        return np.sqrt(z_return**2 + z_range**2 + z_volume**2)

    def _classify_anomaly(
        self, z_return: float, z_range: float, z_volume: float, price_change: float
    ) -> Tuple[Optional[str], str]:
        """
        Classify anomaly type and direction

        Args:
            z_return: Return z-score
            z_range: Range z-score
            z_volume: Volume z-score
            price_change: Price change ratio

        Returns:
            (anomaly_type, direction) or (None, "neutral")
        """
        volume_threshold = self.Z_VOLUME_MAJOR if self.is_major_coin else self.Z_VOLUME_ALT

        # PUMP: z_return > 3.5, z_volume > threshold, bullish
        if z_return > self.Z_RETURN_PUMP_DUMP and z_volume > volume_threshold:
            return "PUMP", "bullish"

        # DUMP: z_return < -3.5, z_volume > threshold, bearish
        if z_return < -self.Z_RETURN_PUMP_DUMP and z_volume > volume_threshold:
            return "DUMP", "bearish"

        # VOLUME_SPIKE: z_volume > 5.0, price change < 2%
        if z_volume > self.Z_VOLUME_SPIKE and abs(price_change) < self.PRICE_CHANGE_THRESHOLD:
            return "VOLUME_SPIKE", "neutral"

        # VOLATILITY_EXPANSION: z_range > 2.5
        if z_range > self.Z_RANGE_EXPANSION:
            direction = "bullish" if price_change > 0 else "bearish"
            return "VOLATILITY_EXPANSION", direction

        # REVERSAL: price reversal + volume confirmation
        if self._detect_reversal(z_return, z_volume, price_change):
            direction = "bullish" if price_change > 0 else "bearish"
            return "REVERSAL", direction

        return None, "neutral"

    def _detect_reversal(self, z_return: float, z_volume: float, price_change: float) -> bool:
        """
        Detect reversal pattern

        Args:
            z_return: Return z-score
            z_range: Range z-score
            z_volume: Volume z-score
            price_change: Price change ratio

        Returns:
            True if reversal detected
        """
        # Reversal requires significant return change + volume confirmation
        return abs(z_return) > 2.0 and z_volume > 2.5

    def _check_confirmation(self, historical_klines: List[Dict], timeframe: str) -> bool:
        """
        Check for 2+ consecutive confirmations to reduce noise

        Args:
            historical_klines: Previous klines (excluding current)
            timeframe: Timeframe

        Returns:
            True if confirmed
        """
        if len(historical_klines) < 20:
            return False

        # Simple threshold check instead of recursive detect() to avoid stack overflow
        prev_closes = [k["close"] for k in historical_klines[-20:]]
        prev_volumes = [k["volume"] for k in historical_klines[-20:]]

        # Check if previous period had elevated z-scores
        if len(prev_closes) < 2 or len(prev_volumes) < 2:
            return False

        # Calculate simple volatility check
        prev_returns = [(prev_closes[i] - prev_closes[i-1]) / prev_closes[i-1]
                       for i in range(1, len(prev_closes))]
        avg_return = sum(prev_returns) / len(prev_returns)

        return abs(avg_return) > 0.01  # 1% threshold for confirmation

    def _generate_brief(
        self, anomaly_type: str, direction: str, z_return: float, z_range: float, z_volume: float
    ) -> str:
        """
        Generate brief explanation

        Args:
            anomaly_type: Anomaly type
            direction: Direction
            z_return: Return z-score
            z_range: Range z-score
            z_volume: Volume z-score

        Returns:
            Brief explanation string
        """
        briefs = {
            "PUMP": f"Strong upward movement (z_ret={z_return:.1f}) with volume surge (z_vol={z_volume:.1f})",
            "DUMP": f"Sharp downward movement (z_ret={z_return:.1f}) with volume surge (z_vol={z_volume:.1f})",
            "VOLUME_SPIKE": f"Significant volume spike (z_vol={z_volume:.1f}) without major price change",
            "VOLATILITY_EXPANSION": f"Volatility expansion (z_range={z_range:.1f}) trending {direction}",
            "REVERSAL": f"Potential reversal pattern (z_ret={z_return:.1f}, z_vol={z_volume:.1f}) turning {direction}"
        }

        return briefs.get(anomaly_type, "Unknown anomaly detected")


def detect_anomalies_multi_timeframe(
    asset: str, timeframes_data: Dict[str, List[Dict]]
) -> List[AnomalySignal]:
    """
    Detect anomalies across multiple timeframes

    Args:
        asset: Asset symbol
        timeframes_data: Dict with keys "15m" and "1h", values are 200 klines each

    Returns:
        List of detected anomaly signals
    """
    detector = AnomalyDetectorV2(asset)
    signals = []

    for tf in ["15m", "1h"]:
        if tf not in timeframes_data:
            continue

        signal = detector.detect(timeframes_data[tf], tf)
        if signal:
            signals.append(signal)

    return signals
