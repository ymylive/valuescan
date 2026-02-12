# Anomaly Detection v2 - Technical Documentation

## Overview

Anomaly Detection v2 implements mathematically rigorous statistical methods to detect market anomalies in crypto and metals markets. It replaces the previous standard deviation-based approach with robust statistical techniques that are less sensitive to outliers.

## Key Improvements

### 1. Robust Z-Score (MAD-based)

**Previous approach**: Standard deviation-based z-score
- Sensitive to outliers
- Can be skewed by extreme values
- Less reliable in volatile markets

**New approach**: Median Absolute Deviation (MAD)
- Robust to outliers
- More stable in volatile conditions
- Better statistical properties

**Formula**:
```
z = (value - median) / (1.4826 * MAD)
where MAD = median(|data - median(data)|)
```

The constant 1.4826 normalizes MAD to match standard deviation for normal distributions.

### 2. ATR Normalization

Range anomalies are normalized by Average True Range (ATR) to account for varying volatility levels:

```
range_anomaly = (high - low) / ATR(14)
```

This makes the detection adaptive to current market volatility.

### 3. Composite Scoring

Multiple z-scores are combined into a single composite score:

```
score = sqrt(z_return² + z_range² + z_volume²)
```

This provides a holistic view of anomaly strength across multiple dimensions.

## Anomaly Types

### PUMP
- **Trigger**: z_return > 3.5 AND z_volume > threshold
- **Direction**: bullish
- **Interpretation**: Strong upward price movement with volume confirmation
- **Volume threshold**: 3.5 for BTC/ETH, 5.0 for altcoins

### DUMP
- **Trigger**: z_return < -3.5 AND z_volume > threshold
- **Direction**: bearish
- **Interpretation**: Sharp downward price movement with volume confirmation
- **Volume threshold**: 3.5 for BTC/ETH, 5.0 for altcoins

### VOLUME_SPIKE
- **Trigger**: z_volume > 5.0 AND |price_change| < 2%
- **Direction**: neutral
- **Interpretation**: Significant volume increase without major price movement
- **Use case**: Potential accumulation/distribution, pre-breakout signal

### VOLATILITY_EXPANSION
- **Trigger**: z_range > 2.5
- **Direction**: bullish/bearish (based on price direction)
- **Interpretation**: Range expansion indicating increased volatility
- **Use case**: Trend acceleration, breakout confirmation

### REVERSAL
- **Trigger**: |z_return| > 2.0 AND z_volume > 2.5
- **Direction**: bullish/bearish (based on reversal direction)
- **Interpretation**: Potential trend reversal with volume support
- **Use case**: Counter-trend opportunities, exhaustion signals

## Timeframe Support

**Supported**: 15m, 1h only

**Rationale**:
- 15m: Captures intraday anomalies, suitable for active trading
- 1h: Balances noise reduction with responsiveness
- Shorter timeframes (5m): Too noisy, high false positive rate
- Longer timeframes (4h, 1d): Anomalies already visible in price action

## Data Requirements

### Input Schema
```python
{
  "asset": "BTC|ETH|XAU|XAG",
  "timeframes": {
    "15m": [200 klines],  # Required
    "1h": [200 klines]    # Required
  }
}
```

Each kline must contain:
- `time`: Unix timestamp
- `open`: Opening price
- `high`: Highest price
- `low`: Lowest price
- `close`: Closing price
- `volume`: Trading volume

### Output Schema
```python
{
  "timeframe": "15m|1h",
  "anomaly_type": "PUMP|DUMP|VOLUME_SPIKE|VOLATILITY_EXPANSION|REVERSAL",
  "direction": "bullish|bearish|neutral",
  "score": float,
  "triggers": {
    "z_return": float,
    "z_range": float,
    "z_volume": float,
    "threshold_hit": bool
  },
  "brief": str
}
```

## Algorithm Parameters

### Rolling Windows
- **Median calculation**: 200 periods
- **MAD calculation**: 200 periods
- **ATR calculation**: 14 periods

### Thresholds
- **PUMP/DUMP z_return**: ±3.5
- **Volume (major coins)**: 3.5
- **Volume (altcoins)**: 5.0
- **Volume spike**: 5.0
- **Range expansion**: 2.5
- **Reversal return**: ±2.0
- **Reversal volume**: 2.5
- **Price change threshold**: 2%

### Confirmation
- Requires 2+ consecutive periods with similar signals
- Reduces false positives from single-period noise
- Can be disabled for high-urgency scenarios

## Usage Examples

### Basic Detection
```python
from signal_monitor.anomaly_detector.detector_v2 import AnomalyDetectorV2

detector = AnomalyDetectorV2("BTC")
signal = detector.detect(klines_200, "15m")

if signal:
    print(f"Anomaly detected: {signal.anomaly_type}")
    print(f"Direction: {signal.direction}")
    print(f"Score: {signal.score:.2f}")
    print(f"Brief: {signal.brief}")
```

### Multi-Timeframe Detection
```python
from signal_monitor.anomaly_detector.detector_v2 import detect_anomalies_multi_timeframe

timeframes_data = {
    "15m": klines_15m,  # 200 klines
    "1h": klines_1h     # 200 klines
}

signals = detect_anomalies_multi_timeframe("BTC", timeframes_data)

for signal in signals:
    print(f"[{signal.timeframe}] {signal.anomaly_type}: {signal.brief}")
```

## Statistical Properties

### MAD vs Standard Deviation

| Property | Standard Deviation | MAD |
|----------|-------------------|-----|
| Outlier sensitivity | High | Low |
| Breakdown point | 0% | 50% |
| Efficiency (normal dist) | 100% | 37% |
| Robustness | Poor | Excellent |

**Breakdown point**: Proportion of outliers that can be tolerated before the statistic becomes unreliable.

### Z-Score Interpretation

| Z-Score | Probability (Normal) | Interpretation |
|---------|---------------------|----------------|
| ±1.96 | 5% | Significant |
| ±2.58 | 1% | Highly significant |
| ±3.29 | 0.1% | Very highly significant |
| ±3.5 | 0.05% | Extreme anomaly |

## Performance Considerations

### Computational Complexity
- **Per detection**: O(n) where n = 200 klines
- **Median calculation**: O(n log n)
- **MAD calculation**: O(n log n)
- **ATR calculation**: O(n)

### Memory Usage
- **Per detector instance**: ~10 KB
- **Per detection call**: ~50 KB (temporary arrays)

### Optimization Tips
1. Reuse detector instances across multiple detections
2. Pre-sort klines by time to avoid validation overhead
3. Use numpy arrays directly if possible
4. Cache ATR calculations for repeated use

## Testing

### Unit Tests
Location: `E:\project\valuescan\signal_monitor\anomaly_detector\tests\test_detector_v2.py`

Run tests:
```bash
pytest E:\project\valuescan\signal_monitor\anomaly_detector\tests\test_detector_v2.py -v
```

### Test Coverage
- Robust z-score calculation
- ATR calculation
- Composite scoring
- Anomaly classification (all types)
- Multi-timeframe detection
- Schema validation
- Edge cases (zero MAD, constant data, extreme values)

## Integration

### With Existing System
The v2 detector is designed to coexist with the existing detector during migration:

```python
# Old detector (to be deprecated)
from signal_monitor.anomaly_detector.detector import SignalDetector

# New detector (v2)
from signal_monitor.anomaly_detector.detector_v2 import AnomalyDetectorV2
```

### Migration Path
1. Deploy v2 detector alongside existing detector
2. Run both detectors in parallel, compare outputs
3. Gradually increase v2 weight in composite signals
4. Deprecate old detector after validation period

## Limitations

1. **Requires 200 klines**: Cannot detect anomalies with less data
2. **Confirmation delay**: 2-period confirmation adds latency
3. **Not suitable for**: Ultra-high-frequency trading (< 5m timeframes)
4. **Asset-specific tuning**: Thresholds optimized for crypto/metals, may need adjustment for other assets

## Future Enhancements

1. **Adaptive thresholds**: Adjust thresholds based on market regime
2. **Multi-asset correlation**: Detect anomalies across correlated assets
3. **Machine learning**: Use ML to optimize threshold selection
4. **Real-time streaming**: Support incremental updates without full recalculation

## References

1. Rousseeuw, P. J., & Croux, C. (1993). "Alternatives to the Median Absolute Deviation". Journal of the American Statistical Association.
2. Wilder, J. W. (1978). "New Concepts in Technical Trading Systems". Trend Research.
3. Tukey, J. W. (1977). "Exploratory Data Analysis". Addison-Wesley.

## Version History

- **v2.0.0** (2026-02-10): Initial release with MAD-based robust detection
- **v1.0.0** (legacy): Standard deviation-based detection (deprecated)
