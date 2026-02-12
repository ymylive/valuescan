# Macro Features & Level Detection

## Overview

This module provides multi-timeframe feature engineering and support/resistance level detection for ValuScan QuantRefactorV3.

## Components

### 1. `macro_features.py`

Extracts technical features from 200-kline datasets across 4 timeframes (15m, 1h, 4h, 1d).

**Input Requirements:**
- Exactly 200 klines per timeframe
- All 4 timeframes must be present: 15m, 1h, 4h, 1d
- Klines must include: time, open, high, low, close, volume

**Feature Categories:**

1. **Trend Features**
   - EMA slopes (7, 21, 50, 200 periods)
   - ADX (Average Directional Index)

2. **Momentum Features**
   - RSI (Relative Strength Index)
   - MACD histogram
   - Rate of change (20-period)

3. **Volatility Features**
   - ATR (Average True Range)
   - Bollinger Band width
   - Realized volatility (annualized)

4. **Structure Features**
   - Higher highs/lows detection
   - Retracement depth
   - Breakout detection

5. **Volume Features**
   - Volume MA ratio
   - OBV trend (up/down/neutral)

**Usage:**

```python
from macro_features import compute_macro_features

data = {
    "asset": "BTC",
    "timeframes": {
        "15m": [...],  # 200 klines
        "1h": [...],   # 200 klines
        "4h": [...],   # 200 klines
        "1d": [...]    # 200 klines
    }
}

features = compute_macro_features(data)
```

**Output Schema:**

```python
{
    "asset": "BTC",
    "timeframes": {
        "15m": {
            "trend": {...},
            "momentum": {...},
            "volatility": {...},
            "structure": {...},
            "volume": {...}
        },
        # ... same for 1h, 4h, 1d
    }
}
```

### 2. `level_detector.py`

Detects support and resistance levels using multi-timeframe swing point analysis.

**Algorithm:**

1. **Swing Point Detection**
   - Uses local extrema detection with configurable lookback window
   - Different orders for different timeframes (15m: 3, 1h: 5, 4h: 5, 1d: 7)

2. **Level Clustering**
   - Groups nearby levels within tolerance (0.5% * ATR)
   - Takes median of each cluster as representative level

3. **Multi-Timeframe Merge**
   - Weights levels by timeframe importance:
     - 1d: weight = 4
     - 4h: weight = 3
     - 1h: weight = 2
     - 15m: weight = 1
   - Removes duplicates within 0.5% of current price
   - Returns top 5 closest levels per side

**Usage:**

```python
from level_detector import detect_levels

data = {
    "asset": "BTC",
    "timeframes": {
        "15m": [...],  # 200 klines
        "1h": [...],
        "4h": [...],
        "1d": [...]
    }
}

levels = detect_levels(data)
```

**Output Schema:**

```python
{
    "support": [49800.0, 49500.0, 49200.0],      # Sorted descending
    "resistance": [50200.0, 50500.0, 50800.0]    # Sorted ascending
}
```

## Testing

Run integration tests:

```bash
cd E:\project\valuescan\signal_monitor
python -m pytest test_macro_features.py -v
```

**Test Coverage:**
- Input validation (200-kline requirement)
- Feature extraction for all timeframes
- Level detection and clustering
- Output schema compliance

## Dependencies

- `numpy`: Numerical computations
- `scipy`: Signal processing (local extrema detection)
- `pytest`: Testing framework

## Performance

- **Feature extraction**: ~50ms per asset (4 timeframes)
- **Level detection**: ~30ms per asset
- **Total**: ~80ms per asset for complete macro analysis

## Integration

This module is designed to integrate with:
- Anomaly detection pipeline (provides macro context)
- AI brief generation (provides key levels and market structure)
- Signal scheduler (runs on configurable intervals)

See `SCHEMAS_V3.md` for complete data contracts.
