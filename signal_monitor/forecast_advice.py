from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional


_RISK_ORDER = ["low", "medium", "high"]


def _clamp_risk(level: str) -> str:
    if level not in _RISK_ORDER:
        return "high"
    return level


def _shift_risk(level: str, delta: int) -> str:
    base = _RISK_ORDER.index(_clamp_risk(level))
    idx = min(max(base + delta, 0), len(_RISK_ORDER) - 1)
    return _RISK_ORDER[idx]


def _summarize_factors(factors: List[Dict[str, Any]], max_items: int = 3) -> List[str]:
    notes: List[str] = []
    for factor in factors:
        if not isinstance(factor, dict):
            continue
        name = factor.get("name")
        factor_notes = factor.get("notes") if isinstance(factor.get("notes"), list) else []
        for note in factor_notes:
            if not note:
                continue
            if name:
                notes.append(f"{name}: {note}")
            else:
                notes.append(str(note))
        if len(notes) >= max_items:
            break
    return notes[:max_items]


def build_investment_advice(
    direction: str,
    confidence: int,
    factors: List[Dict[str, Any]],
    ai_summary: Optional[str] = None,
    agreement: Optional[bool] = None,
    asset_class: str = "crypto",
    as_of: Optional[str] = None,
    horizon_hours: int = 24,
) -> Dict[str, Any]:
    direction = (direction or "sideways").lower()
    confidence = int(confidence or 0)
    agreement = agreement if agreement is not None else True

    base_risk = "high" if asset_class in ("crypto", "futures") else "medium"
    if confidence >= 70 and agreement:
        risk_level = _shift_risk(base_risk, -1)
    elif confidence < 40 or not agreement:
        risk_level = _shift_risk(base_risk, 1)
    else:
        risk_level = base_risk

    if not agreement or confidence < 40:
        action = "wait"
    elif direction == "bullish":
        action = "cautious_buy"
    elif direction == "bearish":
        action = "reduce_or_hedge"
    else:
        action = "wait"

    rationale = _summarize_factors(factors, max_items=3)
    if ai_summary:
        rationale.append(str(ai_summary))
    rationale = [item for item in rationale if item]

    timestamp = None
    if as_of:
        try:
            timestamp = datetime.fromisoformat(as_of.replace("Z", "+00:00"))
        except Exception:
            timestamp = None
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)
    effective_until = timestamp + timedelta(hours=horizon_hours)

    return {
        "action": action,
        "bias": direction,
        "confidence": confidence,
        "risk_level": risk_level,
        "time_horizon_hours": horizon_hours,
        "effective_from": timestamp.isoformat(),
        "effective_until": effective_until.isoformat(),
        "rationale": rationale,
        "disclaimer": "For informational purposes only. Not financial advice.",
    }
