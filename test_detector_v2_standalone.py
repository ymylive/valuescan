"""
Standalone unit tests for Anomaly Detection v2
Run with: python test_detector_v2_standalone.py
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np

# Direct import of detector_v2 module
from signal_monitor.anomaly_detector.detector_v2 import (
    AnomalyDetectorV2,
    AnomalySignal,
    detect_anomalies_multi_timeframe
)


def generate_klines(n: int, base_price: float = 100.0, base_volume: float = 1000.0):
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


def test_initialization():
    """Test detector initialization"""
    print("Testing initialization...")
    detector = AnomalyDetectorV2("BTC")
    assert detector.asset == "BTC"
    assert detector.is_major_coin is True

    detector_alt = AnomalyDetectorV2("DOGE")
    assert detector_alt.is_major_coin is False
    print("✓ Initialization test passed")


def test_invalid_timeframe():
    """Test that invalid timeframes raise error"""
    print("Testing invalid timeframe...")
    detector = AnomalyDetectorV2("BTC")
    klines = generate_klines(200)

    try:
        detector.detect(klines, "5m")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Unsupported timeframe" in str(e)
    print("✓ Invalid timeframe test passed")


def test_invalid_kline_count():
    """Test that wrong kline count raises error"""
    print("Testing invalid kline count...")
    detector = AnomalyDetectorV2("BTC")
    klines = generate_klines(100)

    try:
        detector.detect(klines, "15m")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Expected 200 klines" in str(e)
    print("✓ Invalid kline count test passed")


def test_robust_zscore():
    """Test MAD-based robust z-score calculation"""
    print("Testing robust z-score...")
    detector = AnomalyDetectorV2("BTC")

    # Normal data
    data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    z = detector._robust_zscore(10.0, data)
    assert z > 3.0, f"Expected z > 3.0, got {z}"

    # Zero MAD case
    data_constant = np.array([5.0, 5.0, 5.0, 5.0, 5.0])
    z_zero = detector._robust_zscore(5.0, data_constant)
    assert z_zero == 0.0, f"Expected z = 0.0, got {z_zero}"
    print("✓ Robust z-score test passed")


def test_atr_calculation():
    """Test ATR calculation"""
    print("Testing ATR calculation...")
    detector = AnomalyDetectorV2("BTC")

    highs = np.array([102, 103, 104, 105, 106] * 10)
    lows = np.array([98, 99, 100, 101, 102] * 10)
    closes = np.array([100, 101, 102, 103, 104] * 10)

    atr = detector._calculate_atr(highs, lows, closes)
    assert atr > 0, f"Expected ATR > 0, got {atr}"
    assert atr < 10, f"Expected ATR < 10, got {atr}"
    print(f"✓ ATR calculation test passed (ATR={atr:.2f})")


def test_composite_score():
    """Test composite score calculation"""
    print("Testing composite score...")
    detector = AnomalyDetectorV2("BTC")

    score = detector._composite_score(3.0, 2.0, 4.0)
    expected = np.sqrt(3**2 + 2**2 + 4**2)
    assert abs(score - expected) < 0.01, f"Expected {expected}, got {score}"
    print(f"✓ Composite score test passed (score={score:.2f})")


def test_no_anomaly():
    """Test that normal data produces no signal"""
    print("Testing no anomaly detection...")
    detector = AnomalyDetectorV2("BTC")

    # Generate completely normal data
    klines = generate_klines(200, base_price=100.0, base_volume=1000.0)

    signal = detector.detect(klines, "15m")

    # Should not detect anomaly in random normal data
    assert signal is None, "Expected no signal for normal data"
    print("✓ No anomaly test passed")


def test_multi_timeframe_detection():
    """Test multi-timeframe anomaly detection"""
    print("Testing multi-timeframe detection...")
    timeframes_data = {
        "15m": generate_klines(200, base_price=100.0),
        "1h": generate_klines(200, base_price=100.0)
    }

    signals = detect_anomalies_multi_timeframe("BTC", timeframes_data)

    # Should return list (may be empty for normal data)
    assert isinstance(signals, list), "Expected list of signals"
    assert all(isinstance(s, AnomalySignal) for s in signals), "All items should be AnomalySignal"
    print(f"✓ Multi-timeframe test passed (detected {len(signals)} signals)")


def test_extreme_pump():
    """Test extreme pump detection"""
    print("Testing extreme pump detection...")
    detector = AnomalyDetectorV2("BTC")

    # Generate normal data
    klines = generate_klines(199, base_price=100.0, base_volume=1000.0)

    # Add extreme pump candle
    pump_candle = {
        "time": 1000000 + 199 * 60,
        "open": 100.0,
        "high": 120.0,
        "low": 100.0,
        "close": 118.0,  # 18% pump
        "volume": 10000.0  # 10x volume
    }
    klines.append(pump_candle)

    signal = detector.detect(klines, "15m")

    if signal:
        print(f"  Detected: {signal.anomaly_type} ({signal.direction})")
        print(f"  Score: {signal.score:.2f}")
        print(f"  Z-scores: return={signal.triggers.z_return:.2f}, range={signal.triggers.z_range:.2f}, volume={signal.triggers.z_volume:.2f}")
        print(f"  Brief: {signal.brief}")
    else:
        print("  No signal detected (may need confirmation)")
    print("✓ Extreme pump test completed")


def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("Running Anomaly Detection v2 Tests")
    print("=" * 60)

    tests = [
        test_initialization,
        test_invalid_timeframe,
        test_invalid_kline_count,
        test_robust_zscore,
        test_atr_calculation,
        test_composite_score,
        test_no_anomaly,
        test_multi_timeframe_detection,
        test_extreme_pump
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ {test.__name__} failed: {e}")
            failed += 1

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
