from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..config import Config
from ..utils.llm_client import LLMClient
from ..utils.logger import get_logger
from .valuescan_client import fetch_valuescan_bundle

logger = get_logger("mirofish.btc_forecast")


def _build_llm_prompt(payload: Dict[str, Any]) -> List[Dict[str, str]]:
    compact = json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
    system = (
        "You are a crypto analyst. Use the input data to predict BTC trend for the next 24h. "
        "Return JSON only with keys: direction, confidence, summary, key_factors. "
        "direction must be one of bullish/bearish/sideways. confidence is 0-100."
    )
    user = f"Input data (JSON):\n{compact}"
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def _fallback_from_valuescan(valuescan_forecast: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    direction = "sideways"
    confidence = 0
    key_factors: List[str] = []
    summary = "Fallback forecast based on ValueScan data."

    if isinstance(valuescan_forecast, dict):
        direction = str(valuescan_forecast.get("direction") or direction)
        confidence = int(valuescan_forecast.get("confidence") or confidence)
        factors = valuescan_forecast.get("factors") if isinstance(valuescan_forecast.get("factors"), list) else []
        for factor in factors:
            if not isinstance(factor, dict):
                continue
            name = factor.get("name")
            notes = factor.get("notes")
            if name and isinstance(notes, list) and notes:
                key_factors.append(f"{name}: {', '.join(str(n) for n in notes if n)}")
        if valuescan_forecast.get("score") is not None:
            summary = f"ValueScan score {valuescan_forecast.get('score')}, direction {direction}."

    return {
        "direction": direction,
        "confidence": confidence,
        "summary": summary,
        "key_factors": key_factors,
        "source": "valuescan_fallback",
    }


def build_btc_forecast(symbol: str = "BTC", use_llm: bool = True) -> Dict[str, Any]:
    symbol = symbol.upper().replace("$", "").replace("USDT", "").strip() or "BTC"
    valuescan_bundle = fetch_valuescan_bundle(symbol)

    prediction: Optional[Dict[str, Any]] = None
    if use_llm and Config.LLM_API_KEY:
        try:
            llm = LLMClient()
            prediction = llm.chat_json(
                messages=_build_llm_prompt(valuescan_bundle),
                temperature=0.3,
                max_tokens=1200,
            )
            if isinstance(prediction, dict):
                prediction["source"] = "mirofish_llm"
        except Exception as exc:
            logger.warning("LLM forecast failed: %s", exc)

    if not isinstance(prediction, dict):
        prediction = _fallback_from_valuescan(valuescan_bundle.get("btc_forecast"))

    return {
        "symbol": symbol,
        "as_of": datetime.now(timezone.utc).isoformat(),
        "valuescan": valuescan_bundle,
        "prediction": prediction,
    }
