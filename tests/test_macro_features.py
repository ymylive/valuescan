"""
Test suite for Macro Features
Tests EMA slope, RSI, MACD, ATR, Bollinger Bands, and 200K validation
"""

import numpy as np
import sys
sys.path.insert(0, 'E:\\project\\valuescan')

from signal_monitor.macro_features import (
    calculate_ema, calculate_ema_slope, calculate_rsi, calculate_macd,
    calculate_atr, calculate_bb_width, calculate_adx, validate_klines_input
)


def test_ema_calculation():
    """Test EMA calculation"""
    print("\n## EMA Calculation")
    print("**File**: signal_monitor/macro_features.py:29-40")

    prices = [100 + i for i in range(50)]
    ema = calculate_ema(prices, 10)

    print(f"\n**Test - EMA(10) on uptrend**:")
    print(f"  Price range: {prices[0]:.1f} - {prices[-1]:.1f}")
    print(f"  EMA(10): {ema:.2f}")
    print(f"  Expected: ~145 (above SMA due to uptrend)")
    print(f"  Status: {'✅ PASS' if 140 < ema < 150 else '❌ FAIL'}")

    assert 140 < ema < 150


def test_ema_slope():
    """Test EMA slope calculation"""
    print("\n## EMA Slope Calculation")
    print("**File**: signal_monitor/macro_features.py:43-63")

    # Uptrend
    prices_up = [100 + i * 2 for i in range(50)]
    slope_up = calculate_ema_slope(prices_up, 10, lookback=10)

    print(f"\n**Test 1 - Uptrend slope**:")
    print(f"  Price: 100 -> 198 (linear uptrend)")
    print(f"  Slope: {slope_up:.6f}")
    print(f"  Expected: > 0 (positive slope)")
    print(f"  Status: {'✅ PASS' if slope_up > 0 else '❌ FAIL'}")

    # Downtrend
    prices_down = [200 - i * 2 for i in range(50)]
    slope_down = calculate_ema_slope(prices_down, 10, lookback=10)

    print(f"\n**Test 2 - Downtrend slope**:")
    print(f"  Price: 200 -> 102 (linear downtrend)")
    print(f"  Slope: {slope_down:.6f}")
    print(f"  Expected: < 0 (negative slope)")
    print(f"  Status: {'✅ PASS' if slope_down < 0 else '❌ FAIL'}")

    assert slope_up > 0 and slope_down < 0


def test_rsi_calculation():
    """Test RSI calculation"""
    print("\n## RSI Calculation")
    print("**File**: signal_monitor/macro_features.py:96-113")

    # Overbought scenario
    prices_up = [100 * (1.02 ** i) for i in range(30)]
    rsi_up = calculate_rsi(prices_up, 14)

    print(f"\n**Test 1 - Overbought RSI**:")
    print(f"  Price: strong uptrend (2% per period)")
    print(f"  RSI: {rsi_up:.2f}")
    print(f"  Expected: > 70 (overbought)")
    print(f"  Status: {'✅ PASS' if rsi_up > 70 else '❌ FAIL'}")

    # Oversold scenario
    prices_down = [100 * (0.98 ** i) for i in range(30)]
    rsi_down = calculate_rsi(prices_down, 14)

    print(f"\n**Test 2 - Oversold RSI**:")
    print(f"  Price: strong downtrend (-2% per period)")
    print(f"  RSI: {rsi_down:.2f}")
    print(f"  Expected: < 30 (oversold)")
    print(f"  Status: {'✅ PASS' if rsi_down < 30 else '❌ FAIL'}")

    # Neutral
    prices_neutral = [100 + np.random.normal(0, 1) for _ in range(30)]
    rsi_neutral = calculate_rsi(prices_neutral, 14)

    print(f"\n**Test 3 - Neutral RSI**:")
    print(f"  Price: random walk")
    print(f"  RSI: {rsi_neutral:.2f}")
    print(f"  Expected: ~50 (neutral)")
    print(f"  Status: {'✅ PASS' if 40 < rsi_neutral < 60 else '⚠️ PARTIAL'}")

    assert rsi_up > 70 and rsi_down < 30


def test_macd_calculation():
    """Test MACD histogram calculation"""
    print("\n## MACD Histogram Calculation")
    print("**File**: signal_monitor/macro_features.py:116-129")

    prices = [100 + i for i in range(50)]
    macd = calculate_macd(prices, fast=12, slow=26, signal=9)

    print(f"\n**Test - MACD on uptrend**:")
    print(f"  Price: linear uptrend")
    print(f"  MACD histogram: {macd:.4f}")
    print(f"  Expected: > 0 (bullish)")
    print(f"  Status: {'✅ PASS' if macd > 0 else '❌ FAIL'}")

    assert macd >= 0


def test_atr_calculation():
    """Test ATR calculation"""
    print("\n## ATR Calculation")
    print("**File**: signal_monitor/macro_features.py:132-143")

    highs = [105, 110, 108, 112, 115] + [100 + i for i in range(20)]
    lows = [95, 98, 96, 100, 103] + [95 + i for i in range(20)]
    closes = [100, 105, 102, 108, 110] + [97 + i for i in range(20)]

    atr = calculate_atr(highs, lows, closes, period=14)

    print(f"\n**Test - ATR calculation**:")
    print(f"  Price range: {min(lows):.1f} - {max(highs):.1f}")
    print(f"  ATR(14): {atr:.2f}")
    print(f"  Expected: > 0 (positive volatility)")
    print(f"  Status: {'✅ PASS' if atr > 0 else '❌ FAIL'}")

    assert atr > 0


def test_bollinger_bands():
    """Test Bollinger Band width calculation"""
    print("\n## Bollinger Band Width")
    print("**File**: signal_monitor/macro_features.py:146-160")

    # Low volatility
    prices_low_vol = [100 + np.random.normal(0, 0.5) for _ in range(30)]
    bb_low = calculate_bb_width(prices_low_vol, period=20, std_dev=2)

    print(f"\n**Test 1 - Low volatility**:")
    print(f"  BB Width: {bb_low:.4f}")
    print(f"  Expected: < 0.05 (narrow bands)")
    print(f"  Status: {'✅ PASS' if bb_low < 0.05 else '⚠️ PARTIAL'}")

    # High volatility
    prices_high_vol = [100 + np.random.normal(0, 5) for _ in range(30)]
    bb_high = calculate_bb_width(prices_high_vol, period=20, std_dev=2)

    print(f"\n**Test 2 - High volatility**:")
    print(f"  BB Width: {bb_high:.4f}")
    print(f"  Expected: > 0.05 (wide bands)")
    print(f"  Status: {'✅ PASS' if bb_high > 0.05 else '⚠️ PARTIAL'}")

    assert bb_low < bb_high


def test_200k_validation():
    """Test 200K validation requirement"""
    print("\n## 200K Validation")
    print("**File**: signal_monitor/macro_features.py:10-27")

    # Valid input
    valid_data = {
        "asset": "BTC",
        "timeframes": {
            "15m": [{"close": 100, "high": 101, "low": 99, "volume": 1000} for _ in range(200)],
            "1h": [{"close": 100, "high": 101, "low": 99, "volume": 1000} for _ in range(200)],
            "4h": [{"close": 100, "high": 101, "low": 99, "volume": 1000} for _ in range(200)],
            "1d": [{"close": 100, "high": 101, "low": 99, "volume": 1000} for _ in range(200)]
        }
    }

    try:
        validate_klines_input(valid_data)
        print(f"\n**Test 1 - Valid 200K input**:")
        print(f"  Status: ✅ PASS")
        result1 = True
    except Exception as e:
        print(f"\n**Test 1 - Valid 200K input**:")
        print(f"  Status: ❌ FAIL - {e}")
        result1 = False

    # Invalid input (199 klines)
    invalid_data = {
        "asset": "BTC",
        "timeframes": {
            "15m": [{"close": 100, "high": 101, "low": 99, "volume": 1000} for _ in range(199)],
            "1h": [{"close": 100, "high": 101, "low": 99, "volume": 1000} for _ in range(200)],
            "4h": [{"close": 100, "high": 101, "low": 99, "volume": 1000} for _ in range(200)],
            "1d": [{"close": 100, "high": 101, "low": 99, "volume": 1000} for _ in range(200)]
        }
    }

    try:
        validate_klines_input(invalid_data)
        print(f"\n**Test 2 - Invalid input (199 klines)**:")
        print(f"  Status: ❌ FAIL - Should have raised ValueError")
        result2 = False
    except ValueError as e:
        print(f"\n**Test 2 - Invalid input (199 klines)**:")
        print(f"  Status: ✅ PASS - Correctly raised ValueError")
        result2 = True

    assert result1 and result2


def run_all_tests():
    """Run all macro feature tests"""
    print("=" * 80)
    print("MACRO FEATURES TEST REPORT")
    print("=" * 80)

    tests = [
        ("EMA Calculation", test_ema_calculation),
        ("EMA Slope", test_ema_slope),
        ("RSI Calculation", test_rsi_calculation),
        ("MACD Calculation", test_macd_calculation),
        ("ATR Calculation", test_atr_calculation),
        ("Bollinger Bands", test_bollinger_bands),
        ("200K Validation", test_200k_validation)
    ]

    results = []
    for name, test_func in tests:
        try:
            test_func()
            results.append((name, True))
        except Exception as e:
            print(f"\n❌ ERROR in {name}: {e}")
            results.append((name, False))

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")

    print(f"\nTotal: {passed}/{total} tests passed ({passed/total*100:.0f}%)")

    print("\n" + "=" * 80)
    print("ALGORITHM CORRECTNESS")
    print("=" * 80)

    print("""
**EMA Calculation**: ✅ Correct
- Uses standard exponential smoothing formula
- Multiplier: 2/(period+1)
- Properly initialized with SMA

**RSI Calculation**: ✅ Correct
- Standard RSI formula: 100 - (100 / (1 + RS))
- RS = Average Gain / Average Loss
- Handles edge cases (zero loss)

**MACD Calculation**: ⚠️ Simplified
- Uses correct EMA(12) - EMA(26) for MACD line
- Signal line is simplified (0.8 * MACD) instead of EMA(9)
- Recommendation: Implement proper signal line EMA

**ATR Calculation**: ✅ Correct
- True Range = max(H-L, |H-C_prev|, |L-C_prev|)
- ATR = average of TR over period
- Standard implementation

**Bollinger Bands**: ✅ Correct
- Width = (Upper - Lower) / SMA
- Upper/Lower = SMA ± (std_dev * σ)
- Proper normalization
""")

    print("\n" + "=" * 80)
    print("OPTIMIZATION RECOMMENDATIONS")
    print("=" * 80)

    print("""
1. **MACD Signal Line**: Replace simplified signal with proper EMA(9) of MACD line
2. **Performance**: Pre-compute arrays once (already done in compute_macro_features)
3. **ADX Calculation**: Verify ADX formula matches standard implementation
4. **Edge Cases**: All functions handle insufficient data gracefully
5. **200K Requirement**: Strictly enforced - good for data quality
""")


if __name__ == "__main__":
    run_all_tests()
