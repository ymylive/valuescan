"""
Unit tests for Anomaly Detection v2
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

import pytest
import numpy as np


def generate_klines(n: int, base_price: float = 100.0, base_volume: float = 1000.0) -> list:
    """Generate synthetic kline data for testing"""
    klines = []
    for i in range(n):
        price = base_price + np.random.randn() * 0.5
        klines.append({
            "time": 1000000 + i * 60,
            "open": price,
            "high": price + abs(np.random.randn() * 0.2),
            "low": price - abs(np.random.randn() * 0.2),
            "close": price + np.random.randn() * 0.3,
            "volume": base_volume + np.random.randn() * 100
        })
    return klines


class TestAnomalyDetectorV2:
    """Test suite for AnomalyDetectorV2"""

    def test_initialization(self):
        """Test detector initialization"""
        from signal_monitor.anomaly_detector.detector_v2 import AnomalyDetectorV2

        detector = AnomalyDetectorV2("BTC")
        assert detector.asset == "BTC"
        assert detector.is_major_coin is True

        detector_alt = AnomalyDetectorV2("DOGE")
        assert detector_alt.is_major_coin is False

    def test_invalid_timeframe(self):
        """Test that invalid timeframes raise error"""
        from signal_monitor.anomaly_detector.detector_v2 import AnomalyDetectorV2

        detector = AnomalyDetectorV2("BTC")
        klines = generate_klines(200)

        with pytest.raises(ValueError, match="Unsupported timeframe"):
            detector.detect(klines, "5m")

    def test_invalid_kline_count(self):
        """Test that wrong kline count raises error"""
        from signal_monitor.anomaly_detector.detector_v2 import AnomalyDetectorV2

        detector = AnomalyDetectorV2("BTC")
        klines = generate_klines(100)

        with pytest.raises(ValueError, match="Expected 200 klines"):
            detector.detect(klines, "15m")

    def test_robust_zscore(self):
        """Test MAD-based robust z-score calculation"""
        from signal_monitor.anomaly_detector.detector_v2 import AnomalyDetectorV2

        detector = AnomalyDetectorV2("BTC")

        # Normal data
        data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        z = detector._robust_zscore(10.0, data)
        assert z > 3.0  # Should be high z-score

        # Zero MAD case
        data_constant = np.array([5.0, 5.0, 5.0, 5.0, 5.0])
        z_zero = detector._robust_zscore(5.0, data_constant)
        assert z_zero == 0.0

    def test_atr_calculation(self):
        """Test ATR calculation"""
        from signal_monitor.anomaly_detector.detector_v2 import AnomalyDetectorV2

        detector = AnomalyDetectorV2("BTC")

        highs = np.array([102, 103, 104, 105, 106] * 10)
        lows = np.array([98, 99, 100, 101, 102] * 10)
        closes = np.array([100, 101, 102, 103, 104] * 10)

        atr = detector._calculate_atr(highs, lows, closes)
        assert atr > 0
        assert atr < 10  # Reasonable range

    def test_composite_score(self):
        """Test composite score calculation"""
        from signal_monitor.anomaly_detector.detector_v2 import AnomalyDetectorV2

        detector = AnomalyDetectorV2("BTC")

        score = detector._composite_score(3.0, 2.0, 4.0)
        expected = np.sqrt(3**2 + 2**2 + 4**2)
        assert abs(score - expected) < 0.01

    def test_no_anomaly(self):
        """Test that normal data produces no signal"""
        from signal_monitor.anomaly_detector.detector_v2 import AnomalyDetectorV2

        detector = AnomalyDetectorV2("BTC")

        # Generate completely normal data
        klines = generate_klines(200, base_price=100.0, base_volume=1000.0)

        signal = detector.detect(klines, "15m")

        # Should not detect anomaly in random normal data
        assert signal is None

    def test_multi_timeframe_detection(self):
        """Test multi-timeframe anomaly detection"""
        from signal_monitor.anomaly_detector.detector_v2 import (
            detect_anomalies_multi_timeframe,
            AnomalySignal
        )

        timeframes_data = {
            "15m": generate_klines(200, base_price=100.0),
            "1h": generate_klines(200, base_price=100.0)
        }

        signals = detect_anomalies_multi_timeframe("BTC", timeframes_data)

        # Should return list (may be empty for normal data)
        assert isinstance(signals, list)
        assert all(isinstance(s, AnomalySignal) for s in signals)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
