"""
Simple validation script for detector_v2.py
Validates the module can be loaded and basic functionality works
"""

import sys
import importlib.util
import numpy as np

# Load detector_v2 module directly without triggering package imports
spec = importlib.util.spec_from_file_location(
    "detector_v2",
    "E:/project/valuescan/signal_monitor/anomaly_detector/detector_v2.py"
)
detector_v2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(detector_v2)

print("=" * 60)
print("Anomaly Detection v2 Validation")
print("=" * 60)

# Test 1: Module imports
print("\n[1/6] Module import... OK")

# Test 2: Class instantiation
detector = detector_v2.AnomalyDetectorV2("BTC")
assert detector.asset == "BTC"
assert detector.is_major_coin is True
print("[2/6] Class instantiation... OK")

# Test 3: Robust z-score
data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
z = detector._robust_zscore(10.0, data)
assert z > 3.0
print(f"[3/6] Robust z-score calculation... OK (z={z:.2f})")

# Test 4: ATR calculation
highs = np.array([102, 103, 104, 105, 106] * 10)
lows = np.array([98, 99, 100, 101, 102] * 10)
closes = np.array([100, 101, 102, 103, 104] * 10)
atr = detector._calculate_atr(highs, lows, closes)
assert atr > 0
print(f"[4/6] ATR calculation... OK (ATR={atr:.2f})")

# Test 5: Composite score
score = detector._composite_score(3.0, 2.0, 4.0)
expected = np.sqrt(3**2 + 2**2 + 4**2)
assert abs(score - expected) < 0.01
print(f"[5/6] Composite score... OK (score={score:.2f})")

# Test 6: Detection with normal data
klines = []
for i in range(200):
    price = 100.0 + np.random.randn() * 0.5
    klines.append({
        "time": 1000000 + i * 60,
        "open": price,
        "high": price + abs(np.random.randn() * 0.2),
        "low": price - abs(np.random.randn() * 0.2),
        "close": price + np.random.randn() * 0.3,
        "volume": 1000.0 + np.random.randn() * 100
    })

signal = detector.detect(klines, "15m")
print(f"[6/6] Detection on normal data... OK (signal={'detected' if signal else 'none'})")

print("\n" + "=" * 60)
print("All validations passed!")
print("=" * 60)
print("\nDeliverables:")
print("1. E:/project/valuescan/signal_monitor/anomaly_detector/detector_v2.py")
print("2. E:/project/valuescan/signal_monitor/anomaly_detector/tests/test_detector_v2.py")
print("3. E:/project/valuescan/docs/anomaly_v2.md")
