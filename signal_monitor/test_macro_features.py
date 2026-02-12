"""
Integration tests for macro_features.py and level_detector.py
"""

import pytest
from macro_features import compute_macro_features, validate_klines_input
from level_detector import detect_levels


def generate_test_klines(count: int = 200, base_price: float = 50000.0) -> list:
    """Generate synthetic kline data for testing"""
    import random
    klines = []
    price = base_price

    for i in range(count):
        change = random.uniform(-0.02, 0.02)
        price = price * (1 + change)

        high = price * (1 + abs(random.uniform(0, 0.01)))
        low = price * (1 - abs(random.uniform(0, 0.01)))
        volume = random.uniform(1000, 5000)

        klines.append({
            "time": 1700000000 + i * 900,
            "open": price,
            "high": high,
            "low": low,
            "close": price,
            "volume": volume
        })

    return klines


def test_validate_klines_input():
    """Test input validation"""
    # Valid input
    valid_data = {
        "asset": "BTC",
        "timeframes": {
            "15m": generate_test_klines(200),
            "1h": generate_test_klines(200),
            "4h": generate_test_klines(200),
            "1d": generate_test_klines(200)
        }
    }
    validate_klines_input(valid_data)  # Should not raise

    # Missing asset
    with pytest.raises(ValueError, match="Missing 'asset'"):
        validate_klines_input({"timeframes": {}})

    # Missing timeframe
    with pytest.raises(ValueError, match="Missing timeframe: 1h"):
        validate_klines_input({
            "asset": "BTC",
            "timeframes": {
                "15m": generate_test_klines(200),
                "4h": generate_test_klines(200),
                "1d": generate_test_klines(200)
            }
        })

    # Wrong kline count
    with pytest.raises(ValueError, match="must have exactly 200 klines"):
        validate_klines_input({
            "asset": "BTC",
            "timeframes": {
                "15m": generate_test_klines(150),
                "1h": generate_test_klines(200),
                "4h": generate_test_klines(200),
                "1d": generate_test_klines(200)
            }
        })


def test_compute_macro_features():
    """Test macro feature extraction"""
    data = {
        "asset": "BTC",
        "timeframes": {
            "15m": generate_test_klines(200, 50000),
            "1h": generate_test_klines(200, 50000),
            "4h": generate_test_klines(200, 50000),
            "1d": generate_test_klines(200, 50000)
        }
    }

    result = compute_macro_features(data)

    # Check structure
    assert result["asset"] == "BTC"
    assert "timeframes" in result

    for tf in ["15m", "1h", "4h", "1d"]:
        assert tf in result["timeframes"]
        features = result["timeframes"][tf]

        # Check trend features
        assert "trend" in features
        assert "ema_7_slope" in features["trend"]
        assert "ema_21_slope" in features["trend"]
        assert "ema_50_slope" in features["trend"]
        assert "ema_200_slope" in features["trend"]
        assert "adx" in features["trend"]

        # Check momentum features
        assert "momentum" in features
        assert "rsi" in features["momentum"]
        assert 0 <= features["momentum"]["rsi"] <= 100
        assert "macd_histogram" in features["momentum"]
        assert "rate_of_change" in features["momentum"]

        # Check volatility features
        assert "volatility" in features
        assert "atr" in features["volatility"]
        assert features["volatility"]["atr"] >= 0
        assert "bb_width" in features["volatility"]
        assert "realized_vol" in features["volatility"]

        # Check structure features
        assert "structure" in features
        assert "higher_highs" in features["structure"]
        assert "higher_lows" in features["structure"]
        assert "retracement_depth" in features["structure"]
        assert "breakout_detected" in features["structure"]

        # Check volume features
        assert "volume" in features
        assert "volume_ma_ratio" in features["volume"]
        assert "obv_trend" in features["volume"]
        assert features["volume"]["obv_trend"] in ["up", "down", "neutral"]


def test_detect_levels():
    """Test level detection"""
    data = {
        "asset": "BTC",
        "timeframes": {
            "15m": generate_test_klines(200, 50000),
            "1h": generate_test_klines(200, 50000),
            "4h": generate_test_klines(200, 50000),
            "1d": generate_test_klines(200, 50000)
        }
    }

    result = detect_levels(data)

    # Check structure
    assert "support" in result
    assert "resistance" in result
    assert isinstance(result["support"], list)
    assert isinstance(result["resistance"], list)

    # Check that levels are sorted
    assert result["support"] == sorted(result["support"], reverse=True)
    assert result["resistance"] == sorted(result["resistance"])

    # Check max 5 levels per side
    assert len(result["support"]) <= 5
    assert len(result["resistance"]) <= 5

    # Check that support < current price < resistance
    current_price = data["timeframes"]["15m"][-1]["close"]
    for s in result["support"]:
        assert s < current_price
    for r in result["resistance"]:
        assert r > current_price


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
