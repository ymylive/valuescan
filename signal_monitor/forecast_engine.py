from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from signal_monitor.btc_forecast import build_symbol_forecast
from signal_monitor.market_data_sources import get_coingecko_id
from signal_monitor.stock_forecast import build_stock_forecast


FUTURES_ALIASES = {
    "GOLD": "GC=F",
    "XAUUSD": "GC=F",
    "GC": "GC=F",
    "SILVER": "SI=F",
    "XAGUSD": "SI=F",
    "SI": "SI=F",
    "WTI": "CL=F",
    "CRUDE": "CL=F",
    "BRENT": "BZ=F",
}


def _normalize_symbol(symbol: str) -> str:
    return (symbol or "").strip().upper()


def _resolve_symbol(symbol: str) -> Tuple[str, str]:
    raw = _normalize_symbol(symbol)
    if not raw:
        return "", "unknown"
    if raw in FUTURES_ALIASES:
        return FUTURES_ALIASES[raw], "futures"
    if raw.endswith("=F"):
        return raw, "futures"
    base = raw.replace("$", "").replace("USDT", "").replace("USD", "").strip()
    if get_coingecko_id(base):
        return base, "crypto"
    return raw, "stock"


def build_market_forecast(symbol: str, use_llm: Optional[bool] = None) -> Optional[Dict[str, Any]]:
    resolved, asset_class = _resolve_symbol(symbol)
    if not resolved:
        return None
    if asset_class == "crypto":
        data = build_symbol_forecast(resolved, use_llm=use_llm)
    else:
        data = build_stock_forecast(resolved, asset_class=asset_class, use_llm=use_llm)
    if not isinstance(data, dict):
        return None
    data.setdefault("asset_class", asset_class)
    data["input_symbol"] = _normalize_symbol(symbol)
    data["resolved_symbol"] = resolved
    return data
