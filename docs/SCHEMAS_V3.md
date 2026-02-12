# ValuScan QuantRefactorV3 - Data Schemas

## Overview
This document defines all data contracts for the ValuScan v3 refactoring.

---

## Input Schemas

### Multi-Timeframe Klines Input
```python
{
  "asset": "BTC|ETH|XAU|XAG",
  "timeframes": {
    "15m": [  # Exactly 200 klines required
      {"time": int, "open": float, "high": float, "low": float, "close": float, "volume": float},
      ...
    ],
    "1h": [200 klines],
    "4h": [200 klines],
    "1d": [200 klines]
  }
}
```

**Validation Rules:**
- Each timeframe MUST have exactly 200 klines
- Missing timeframes or < 200 klines should raise validation error
- Klines must be sorted by time (oldest first)

---

## Anomaly Detection Output (v2)

### Anomaly Signal Schema
```python
{
  "timeframe": "15m|1h",  # Only 15m and 1h supported
  "anomaly_type": "PUMP|DUMP|VOLUME_SPIKE|VOLATILITY_EXPANSION|REVERSAL",
  "direction": "bullish|bearish|neutral",
  "score": float,  # Composite anomaly score
  "triggers": {
    "z_return": float,  # MAD-based z-score for returns
    "z_range": float,   # ATR-normalized range z-score
    "z_volume": float,  # MAD-based volume z-score
    "threshold_hit": bool
  },
  "brief": str  # Short explanation of the anomaly
}
```

**Anomaly Type Definitions:**
- **PUMP**: z_return > 3.5, z_volume > 3.5, direction = bullish
- **DUMP**: z_return < -3.5, z_volume > 3.5, direction = bearish
- **VOLUME_SPIKE**: z_volume > 5.0, price change < 2%
- **VOLATILITY_EXPANSION**: z_range > 2.5
- **REVERSAL**: Price reversal + volume confirmation

---

## Fundamentals Data

### News Raw Data
```python
{
  "news_raw_latest_50": [
    {
      "time": str,  # ISO 8601 format
      "title": str,
      "content": str,
      "tags": [str],
      "importance": "high|medium|low",
      "source": "jin10"
    },
    ...  # Up to 50 items
  ]
}
```

### News Summary
```python
{
  "news_summary": {
    "top_narratives": [
      {
        "title": str,
        "detail": str
      }
    ],  # Top 5 narratives
    "top_catalysts": [
      {
        "event": str,
        "impact_assets": [str],  # e.g., ["BTC", "ETH"]
        "impact_direction": "bullish|bearish|neutral",
        "detail": str
      }
    ],  # Top 5 catalysts
    "risk_appetite": {
      "state": "risk_on|risk_off|neutral",
      "detail": str
    }
  }
}
```

### Economic Events
```python
{
  "econ_events": [
    {
      "name": str,
      "country": str,
      "importance": "high|medium|low",
      "time": str,  # ISO 8601 format
      "previous": float,
      "forecast": float,
      "actual": float,
      "description": str
    }
  ]
}
```

### Economic Summary
```python
{
  "econ_summary": {
    "key_events": [
      {
        "event": str,
        "impact": str,
        "crypto_relevance": str,
        "metals_relevance": str
      }
    ],
    "macro_outlook": {
      "inflation": str,
      "growth": str,
      "policy": str
    }
  }
}
```

---

## Macro Features

### Multi-Timeframe Features
```python
{
  "asset": str,
  "timeframes": {
    "15m": {
      "trend": {
        "ema_7_slope": float,
        "ema_21_slope": float,
        "ema_50_slope": float,
        "ema_200_slope": float,
        "adx": float
      },
      "momentum": {
        "rsi": float,
        "macd_histogram": float,
        "rate_of_change": float
      },
      "volatility": {
        "atr": float,
        "bb_width": float,
        "realized_vol": float
      },
      "structure": {
        "higher_highs": bool,
        "higher_lows": bool,
        "retracement_depth": float,
        "breakout_detected": bool
      },
      "volume": {
        "volume_ma_ratio": float,
        "obv_trend": str  # "up|down|neutral"
      }
    },
    "1h": {...},
    "4h": {...},
    "1d": {...}
  }
}
```

### Support/Resistance Levels
```python
{
  "support": [float, float, ...],  # Sorted ascending
  "resistance": [float, float, ...]  # Sorted ascending
}
```

---

## AI Output Schema

### AI Brief (Dual-Track)
```python
{
  "asset": str,
  "time_focus": ["15m", "1h", "4h", "1d"],
  "key_levels": {
    "support": [float],
    "resistance": [float]
  },
  "market_state": {
    "regime": "trend|range|transition",
    "drivers": [str]  # Key factors driving current state
  },
  "futures_plan": {
    "bias": "long|short|neutral",
    "long_zone": [float, float],  # [low, high]
    "short_zone": [float, float],
    "invalid_level": float,  # Stop loss / invalidation level
    "take_profit": [float, float, float],  # [tp1, tp2, tp3]
    "risk_control": str
  },
  "spot_plan": {
    "bias": "buy_dip|breakout_follow|wait",
    "buy_zone": [float, float],
    "sell_zone": [float, float],
    "take_profit": [float, float],  # [tp1, tp2]
    "risk_control": str
  },
  "one_sentence_summary": str,
  "disclaimer": "仅供参考，不构成投资建议"
}
```

**CRITICAL: Forbidden Fields**
The following fields MUST NOT appear anywhere in AI outputs:
- `confidence`
- `confident`
- `probability`
- `置信`
- `信心`
- `胜率`

Any AI output containing these fields should be rejected by schema validation.

---

## API Endpoints

### Control API
- `POST /api/control/scheduler/start`
- `POST /api/control/scheduler/stop`
- `POST /api/control/trigger/anomaly`
- `POST /api/control/trigger/macro`
- `POST /api/control/trigger/ai_brief`
- `POST /api/control/trigger/news`
- `POST /api/control/trigger/econ`

### Config API
- `GET /api/config`
- `PUT /api/config`
- `GET /api/config/history`

### Logs API
- `GET /api/logs?level=info&module=anomaly&since=2026-02-10T00:00:00&limit=100`
- `GET /api/logs/stream`

### Health API
```python
{
  "version": "3.0.0",
  "uptime_seconds": int,
  "tasks": {
    "anomaly_detection": {
      "status": "running|idle|error",
      "last_run": str,  # ISO 8601
      "next_run": str
    },
    "macro_analysis": {...},
    "ai_brief": {...},
    "news_fetch": {...},
    "econ_fetch": {...}
  },
  "queue_backlog": int
}
```

### Fundamentals API
- `GET /api/fundamentals/news/latest?limit=50`
- `GET /api/fundamentals/econ/upcoming`
- `GET /api/fundamentals/econ/history`

---

## Version Control

**Schema Version**: `3.0.0`

All data structures should include a `schema_version` field for future compatibility:
```python
{
  "schema_version": "3.0.0",
  ...
}
```
