from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from signal_monitor.anomaly_detector.features.technical_indicators import (
    compute_technical_snapshot,
    score_technical_indicators,
)
from signal_monitor.fundamentals_sources import fetch_macro_snapshot
from signal_monitor.market_alert import fetch_vix
from signal_monitor.market_data_hub import (
    STOCK_SOURCE_WEIGHTS,
    fetch_stock_klines,
    fetch_stock_snapshot_sources,
)
from signal_monitor.forecast_advice import build_investment_advice

try:
    from signal_monitor.btc_forecast import (
        _build_ai_forecast,
        _build_consensus,
        _get_ai_forecast_config,
        _score_direction,
    )
except Exception:
    _build_ai_forecast = None
    _build_consensus = None
    _get_ai_forecast_config = None
    _score_direction = None


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def _score_technical(closes: List[float], highs: List[float], lows: List[float], volumes: List[float]) -> Dict[str, Any]:
    if not closes:
        return {"score": 0.0, "weight": 0.5, "direction": "sideways", "notes": ["missing klines"]}
    snapshot = compute_technical_snapshot(closes, highs, lows, volumes)
    current_price = closes[-1]
    raw_score, direction, triggers = score_technical_indicators(snapshot, current_price)
    score = 0.0
    if direction == "bullish":
        score = min(raw_score / 25.0, 1.0)
    elif direction == "bearish":
        score = -min(raw_score / 25.0, 1.0)
    return {
        "score": score,
        "weight": 0.5,
        "direction": direction,
        "notes": triggers[:6],
        "snapshot": vars(snapshot),
    }


def _score_momentum(price_change_24h: Optional[float], price_change_1h: Optional[float]) -> Dict[str, Any]:
    score = 0.0
    notes: List[str] = []
    if price_change_24h is not None:
        if price_change_24h >= 1.0:
            score += 0.4
            notes.append(f"24h change +{price_change_24h:.2f}%")
        elif price_change_24h <= -1.0:
            score -= 0.4
            notes.append(f"24h change {price_change_24h:.2f}%")
    if price_change_1h is not None:
        if price_change_1h >= 0.3:
            score += 0.2
            notes.append(f"1h change +{price_change_1h:.2f}%")
        elif price_change_1h <= -0.3:
            score -= 0.2
            notes.append(f"1h change {price_change_1h:.2f}%")
    score = max(min(score, 1.0), -1.0)
    return {
        "score": score,
        "weight": 0.3,
        "direction": _score_direction(score, threshold=0.05) if _score_direction else "sideways",
        "notes": notes,
    }


def _score_macro_risk(vix_value: Optional[float]) -> Dict[str, Any]:
    if vix_value is None:
        return {"score": 0.0, "weight": 0.2, "direction": "sideways", "notes": ["missing vix"]}
    score = 0.0
    notes: List[str] = []
    if vix_value >= 30:
        score -= 0.5
        notes.append(f"vix elevated {vix_value:.2f}")
    elif vix_value <= 15:
        score += 0.3
        notes.append(f"vix calm {vix_value:.2f}")
    else:
        notes.append(f"vix {vix_value:.2f}")
    return {
        "score": score,
        "weight": 0.2,
        "direction": _score_direction(score, threshold=0.05) if _score_direction else "sideways",
        "notes": notes,
    }


def _extract_klines_metrics(df: Any) -> Tuple[List[float], List[float], List[float], List[float], Optional[float]]:
    if df is None or getattr(df, "empty", True):
        return [], [], [], [], None
    closes = df["close"].tolist()
    highs = df["high"].tolist()
    lows = df["low"].tolist()
    volumes = df["volume"].tolist()
    price_change_1h = None
    if len(closes) >= 2 and closes[-2] != 0:
        price_change_1h = (closes[-1] - closes[-2]) / closes[-2] * 100.0
    return closes, highs, lows, volumes, price_change_1h


def build_stock_forecast(
    symbol: str,
    asset_class: str = "stock",
    use_llm: Optional[bool] = None,
) -> Optional[Dict[str, Any]]:
    symbol = symbol.upper().strip()
    if not symbol:
        return None

    snapshot, snapshot_sources = fetch_stock_snapshot_sources(symbol)
    snapshot = snapshot or {}
    snapshot_sources = snapshot_sources or []
    macro_snapshot = fetch_macro_snapshot() or {}
    vix_value = fetch_vix()

    df = fetch_stock_klines(symbol)
    closes, highs, lows, volumes, price_change_1h = _extract_klines_metrics(df)

    technical = _score_technical(closes, highs, lows, volumes)
    momentum = _score_momentum(_safe_float(snapshot.get("price_change_percent")), price_change_1h)
    macro = _score_macro_risk(_safe_float(vix_value))

    factors = [
        {"name": "technical", **technical},
        {"name": "momentum", **momentum},
        {"name": "macro", **macro},
    ]

    weighted_sum = 0.0
    weight_total = 0.0
    for factor in factors:
        weight = float(factor.get("weight", 0) or 0)
        score = float(factor.get("score", 0) or 0)
        weighted_sum += score * weight
        weight_total += weight

    score = weighted_sum / weight_total if weight_total > 0 else 0.0
    direction = _score_direction(score) if _score_direction else "sideways"
    confidence = int(min(abs(score) * 100, 100))

    config = _get_ai_forecast_config() if _get_ai_forecast_config else None
    if use_llm is None and config:
        use_llm = bool(config.get("enabled"))
    ai_forecast = None
    if use_llm and _build_ai_forecast and config and config.get("enabled"):
        ai_forecast = _build_ai_forecast(
            symbol,
            asset_class,
            score,
            direction,
            confidence,
            factors,
            snapshot,
            {"macro": macro_snapshot},
            {},
            None,
            price_change_1h,
            [],
            [],
            snapshot_sources,
            {"stock": STOCK_SOURCE_WEIGHTS, "futures": STOCK_SOURCE_WEIGHTS},
            config,
        )

    consensus = None
    if ai_forecast and _build_consensus:
        consensus = _build_consensus(direction, confidence, ai_forecast)
    as_of = datetime.now(timezone.utc).isoformat()
    advice = build_investment_advice(
        consensus.get("direction") if consensus else direction,
        consensus.get("confidence") if consensus else confidence,
        factors,
        ai_summary=ai_forecast.get("summary") if ai_forecast else None,
        agreement=consensus.get("agreement") if consensus else None,
        asset_class=asset_class,
        as_of=as_of,
        horizon_hours=24,
    )

    return {
        "symbol": symbol,
        "asset_class": asset_class,
        "as_of": as_of,
        "horizon_hours": 24,
        "direction": direction,
        "confidence": confidence,
        "score": round(score, 4),
        "factors": factors,
        "ai_forecast": ai_forecast,
        "consensus": consensus,
        "advice": advice,
        "data": {
            "market_snapshot": snapshot,
            "market_sources": snapshot_sources,
            "macro_snapshot": macro_snapshot,
            "price_change_1h": price_change_1h,
        },
    }
