from __future__ import annotations

from flask import request, jsonify

from . import forecast_bp
from signal_monitor.forecast_engine import build_market_forecast
from ..utils.logger import get_logger

logger = get_logger("mirofish.api.forecast")


@forecast_bp.route("/btc", methods=["GET"])
def btc_forecast():
    """BTC forecast powered by ValueScan data + MiroFish."""
    use_llm_raw = request.args.get("use_llm", "1").strip().lower()
    use_llm = use_llm_raw in ("1", "true", "yes", "on")
    data = build_market_forecast("BTC", use_llm=use_llm)
    return jsonify({"success": True, "data": data})


@forecast_bp.route("/symbol/<symbol>", methods=["GET"])
def symbol_forecast(symbol: str):
    """Symbol forecast powered by ValueScan data + MiroFish."""
    use_llm_raw = request.args.get("use_llm", "1").strip().lower()
    use_llm = use_llm_raw in ("1", "true", "yes", "on")
    data = build_market_forecast(symbol, use_llm=use_llm)
    return jsonify({"success": True, "data": data})
