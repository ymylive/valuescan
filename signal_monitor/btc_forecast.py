from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

try:
    from signal_monitor.logger import logger
except Exception:
    try:
        from logger import logger
    except Exception:
        logger = None

try:
    from signal_monitor.chart_pro_v10 import get_klines
except Exception:
    from chart_pro_v10 import get_klines  # type: ignore[import-not-found]

try:
    from signal_monitor.ai_api_utils import (
        AI_PROTOCOL_RESPONSES,
        build_payload,
        override_responses_token_key,
        parse_compatible_content,
        parse_responses_body,
        resolve_protocol_and_url,
        resolve_responses_token_key_override,
        should_force_responses_stream,
    )
except Exception:
    from ai_api_utils import (  # type: ignore[import-not-found]
        AI_PROTOCOL_RESPONSES,
        build_payload,
        override_responses_token_key,
        parse_compatible_content,
        parse_responses_body,
        resolve_protocol_and_url,
        resolve_responses_token_key_override,
        should_force_responses_stream,
    )

from signal_monitor.anomaly_detector.features.technical_indicators import (
    compute_technical_snapshot,
    score_technical_indicators,
)
from signal_monitor.ccxt_data import fetch_ccxt_orderbook, fetch_ccxt_snapshot
from signal_monitor.fundamentals_sources import fetch_fundamentals_snapshot
from signal_monitor.market_data_sources import (
    CRYPTO_SOURCE_WEIGHTS,
    fetch_binance_futures_snapshot,
    fetch_market_snapshot_with_sources,
    fetch_news,
    fetch_trending,
)
from signal_monitor.forecast_advice import build_investment_advice

BASE_DIR = Path(__file__).resolve().parent
AI_FORECAST_ENABLED = os.getenv("NOFX_AI_FORECAST_ENABLED", "0").strip().lower() in ("1", "true", "yes", "on")
AI_FORECAST_API_KEY = os.getenv("NOFX_AI_FORECAST_API_KEY", "").strip() or os.getenv("AI_SUMMARY_API_KEY", "").strip()
AI_FORECAST_API_URL = os.getenv("NOFX_AI_FORECAST_API_URL", "").strip() or os.getenv("AI_SUMMARY_API_URL", "").strip()
AI_FORECAST_API_PROTOCOL = os.getenv("NOFX_AI_FORECAST_API_PROTOCOL", os.getenv("AI_SUMMARY_API_PROTOCOL", "auto")).strip()
AI_FORECAST_MODEL = os.getenv("NOFX_AI_FORECAST_MODEL", "").strip() or os.getenv("AI_SUMMARY_MODEL", "").strip()


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def _calc_depth(side: List[List[float]], depth: int = 10) -> float:
    total = 0.0
    for price, amount in side[:depth]:
        try:
            total += float(price) * float(amount)
        except Exception:
            continue
    return total


def _calc_orderbook_imbalance(orderbook: Optional[Dict[str, Any]], depth: int = 10) -> Optional[Dict[str, Any]]:
    if not isinstance(orderbook, dict):
        return None
    bids = orderbook.get("bids") or []
    asks = orderbook.get("asks") or []
    if not bids or not asks:
        return None
    bid_depth = _calc_depth(bids, depth=depth)
    ask_depth = _calc_depth(asks, depth=depth)
    if bid_depth <= 0 or ask_depth <= 0:
        return None
    ratio = bid_depth / ask_depth
    return {
        "bid_depth": bid_depth,
        "ask_depth": ask_depth,
        "ratio": ratio,
    }


def _score_direction(score: float, threshold: float = 0.2) -> str:
    if score > threshold:
        return "bullish"
    if score < -threshold:
        return "bearish"
    return "sideways"


def _score_technical(closes: List[float], highs: List[float], lows: List[float], volumes: List[float]) -> Dict[str, Any]:
    if not closes:
        return {"score": 0.0, "weight": 0.0, "direction": "sideways", "notes": ["missing klines"]}
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
        "weight": 0.35,
        "direction": direction,
        "notes": triggers[:6],
        "snapshot": vars(snapshot),
    }


def _score_momentum(price_change_24h: Optional[float], price_change_1h: Optional[float]) -> Dict[str, Any]:
    score = 0.0
    notes: List[str] = []
    if price_change_24h is not None:
        if price_change_24h >= 2.0:
            score += 0.4
            notes.append(f"24h change +{price_change_24h:.2f}%")
        elif price_change_24h <= -2.0:
            score -= 0.4
            notes.append(f"24h change {price_change_24h:.2f}%")
    if price_change_1h is not None:
        if price_change_1h >= 0.5:
            score += 0.2
            notes.append(f"1h change +{price_change_1h:.2f}%")
        elif price_change_1h <= -0.5:
            score -= 0.2
            notes.append(f"1h change {price_change_1h:.2f}%")
    if score > 1:
        score = 1.0
    if score < -1:
        score = -1.0
    return {
        "score": score,
        "weight": 0.15,
        "direction": _score_direction(score, threshold=0.05),
        "notes": notes,
    }


def _score_orderbook(imbalance: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not imbalance:
        return {"score": 0.0, "weight": 0.1, "direction": "sideways", "notes": ["missing orderbook"]}
    ratio = imbalance.get("ratio")
    score = 0.0
    if isinstance(ratio, (int, float)):
        if ratio >= 1.1:
            score = 0.4
        elif ratio <= 0.9:
            score = -0.4
    notes = [f"depth ratio {ratio:.2f}"] if isinstance(ratio, (int, float)) else []
    return {
        "score": score,
        "weight": 0.1,
        "direction": _score_direction(score, threshold=0.05),
        "notes": notes,
    }


def _score_sentiment(fear_greed_value: Optional[float]) -> Dict[str, Any]:
    score = 0.0
    notes: List[str] = []
    if fear_greed_value is None:
        return {"score": 0.0, "weight": 0.1, "direction": "sideways", "notes": ["missing sentiment"]}
    if fear_greed_value <= 25:
        score = 0.4
        notes.append(f"fear/greed {fear_greed_value:.0f} (fear)")
    elif fear_greed_value >= 75:
        score = -0.4
        notes.append(f"fear/greed {fear_greed_value:.0f} (greed)")
    else:
        notes.append(f"fear/greed {fear_greed_value:.0f}")
    return {
        "score": score,
        "weight": 0.1,
        "direction": _score_direction(score, threshold=0.05),
        "notes": notes,
    }


def _score_derivatives(
    futures: Dict[str, Any],
    price_change_1h: Optional[float],
) -> Dict[str, Any]:
    score = 0.0
    notes: List[str] = []
    funding_rate = _safe_float(futures.get("funding_rate"))
    oi_change = _safe_float(futures.get("open_interest_change_1h_pct"))

    if funding_rate is not None:
        if funding_rate >= 0.0005:
            score -= 0.5
            notes.append(f"funding high {funding_rate * 100:.4f}%")
        elif funding_rate <= -0.0005:
            score += 0.5
            notes.append(f"funding low {funding_rate * 100:.4f}%")
        else:
            notes.append(f"funding {funding_rate * 100:.4f}%")

    if oi_change is not None and price_change_1h is not None:
        if oi_change >= 2.0 and price_change_1h >= 0.5:
            score += 0.4
            notes.append(f"oi up {oi_change:.2f}% with price up")
        elif oi_change >= 2.0 and price_change_1h <= -0.5:
            score -= 0.4
            notes.append(f"oi up {oi_change:.2f}% with price down")
        elif oi_change <= -2.0 and price_change_1h >= 0.5:
            score -= 0.3
            notes.append(f"oi down {oi_change:.2f}% with price up")
        elif oi_change <= -2.0 and price_change_1h <= -0.5:
            score += 0.3
            notes.append(f"oi down {oi_change:.2f}% with price down")

    liq = futures.get("liquidations_24h") if isinstance(futures.get("liquidations_24h"), dict) else {}
    buy_notional = _safe_float(liq.get("buy_notional"))
    sell_notional = _safe_float(liq.get("sell_notional"))
    if buy_notional is not None and sell_notional is not None:
        total = buy_notional + sell_notional
        if total > 0:
            buy_share = buy_notional / total
            sell_share = sell_notional / total
            if buy_share >= 0.6:
                score += 0.2
                notes.append("liq buy-dominant")
            elif sell_share >= 0.6:
                score -= 0.2
                notes.append("liq sell-dominant")

    if score > 1:
        score = 1.0
    if score < -1:
        score = -1.0
    return {
        "score": score,
        "weight": 0.2,
        "direction": _score_direction(score, threshold=0.05),
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


def _load_json_config(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _get_ai_forecast_config() -> Dict[str, Any]:
    defaults = {
        "enabled": AI_FORECAST_ENABLED,
        "api_key": AI_FORECAST_API_KEY,
        "api_url": AI_FORECAST_API_URL,
        "api_protocol": AI_FORECAST_API_PROTOCOL,
        "model": AI_FORECAST_MODEL,
    }
    fallback = _load_json_config(BASE_DIR / "ai_summary_config.json")
    file_config = _load_json_config(BASE_DIR / "ai_forecast_config.json")

    merged = dict(defaults)
    for key in ("api_key", "api_url", "api_protocol", "model"):
        if fallback.get(key):
            merged[key] = fallback.get(key)
    merged.update({k: v for k, v in file_config.items() if v is not None})
    return merged


def _normalize_direction(value: Any) -> str:
    if not value:
        return "sideways"
    val = str(value).strip().lower()
    if val in {"bullish", "up", "uptrend", "long", "buy"}:
        return "bullish"
    if val in {"bearish", "down", "downtrend", "short", "sell"}:
        return "bearish"
    return "sideways"


def _normalize_confidence(value: Any) -> int:
    try:
        conf = int(float(value))
    except Exception:
        conf = 0
    if conf < 0:
        return 0
    if conf > 100:
        return 100
    return conf


def _extract_key_factors(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item) for item in value if item]
    if isinstance(value, str):
        parts = [item.strip() for item in value.replace(";", ",").split(",")]
        return [item for item in parts if item]
    return []


def _build_llm_payload(
    symbol: str,
    asset_class: str,
    score: float,
    direction: str,
    confidence: int,
    factors: List[Dict[str, Any]],
    market: Dict[str, Any],
    fundamentals: Dict[str, Any],
    futures: Dict[str, Any],
    orderbook_imbalance: Optional[Dict[str, Any]],
    price_change_1h: Optional[float],
    news: List[Dict[str, Any]],
    trending: List[Dict[str, Any]],
    sources: Optional[List[Dict[str, Any]]] = None,
    source_weights: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    news_items = []
    for item in news[:8]:
        if not isinstance(item, dict):
            continue
        news_items.append({
            "title": item.get("title"),
            "source": item.get("source"),
            "url": item.get("url"),
            "published_at": item.get("published_at"),
        })

    trending_items = []
    for item in trending[:8]:
        if not isinstance(item, dict):
            continue
        trending_items.append({
            "symbol": item.get("symbol"),
            "name": item.get("name"),
            "market_cap_rank": item.get("market_cap_rank"),
        })

    market_view = {
        "price": market.get("price"),
        "price_change_percent": market.get("price_change_percent"),
        "high_24h": market.get("high_24h"),
        "low_24h": market.get("low_24h"),
        "volume_24h": market.get("volume_24h"),
        "market_cap": market.get("market_cap"),
    }

    fundamentals_view = {}
    if isinstance(fundamentals, dict):
        fundamentals_view = {
            "sentiment": fundamentals.get("sentiment"),
            "tokenomics": fundamentals.get("tokenomics"),
            "project": fundamentals.get("project"),
            "onchain": fundamentals.get("onchain"),
        }

    futures_view = {}
    if isinstance(futures, dict):
        futures_view = {
            "funding_rate": futures.get("funding_rate"),
            "open_interest": futures.get("open_interest"),
            "open_interest_change_1h_pct": futures.get("open_interest_change_1h_pct"),
            "long_short_ratio": futures.get("long_short_ratio"),
            "taker_flow_15m": futures.get("taker_flow_15m"),
            "liquidations_24h": futures.get("liquidations_24h"),
        }

    factor_view = []
    for factor in factors:
        if not isinstance(factor, dict):
            continue
        factor_view.append({
            "name": factor.get("name"),
            "score": factor.get("score"),
            "direction": factor.get("direction"),
            "notes": factor.get("notes"),
        })

    return {
        "symbol": symbol,
        "asset_class": asset_class,
        "horizon_hours": 24,
        "source_weights": source_weights or {},
        "sources": sources or [],
        "baseline": {
            "direction": direction,
            "confidence": confidence,
            "score": score,
            "factors": factor_view,
        },
        "market_snapshot": market_view,
        "fundamentals": fundamentals_view,
        "futures_snapshot": futures_view,
        "orderbook_imbalance": orderbook_imbalance,
        "price_change_1h": price_change_1h,
        "news": news_items,
        "trending": trending_items,
    }


def _build_llm_prompt(symbol: str, payload: Dict[str, Any]) -> Tuple[str, str]:
    compact = json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
    system_prompt = (
        f"You are a professional multi-asset analyst. Use the input data to predict {symbol} trend for the next 24h. "
        "Return JSON only with keys: direction, confidence, summary, key_factors. "
        "direction must be one of bullish/bearish/sideways. confidence is 0-100. "
        "Use source_weights to prioritize signals (higher weight = higher reliability). "
        "Summary must be concise, professional, and include: bias, recommended stance (buy/hold/reduce/hedge), key driver, key risk, and validity window (next 24h). "
        "If inputs are sparse or conflicting, clearly state low conviction. "
        "Do not add any extra keys or commentary."
    )
    user_prompt = f"Input data (JSON):\n{compact}"
    return system_prompt, user_prompt


def _call_ai_forecast(prompt: Tuple[str, str], config: Dict[str, Any]) -> Optional[str]:
    api_key = (config.get("api_key") or "").strip()
    api_url = (config.get("api_url") or "").strip()
    model = (config.get("model") or "").strip()
    if not api_key or not api_url or not model:
        return None

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    timeout_sec = int(os.getenv("NOFX_AI_API_TIMEOUT", "90") or 90)
    connect_timeout = float(os.getenv("NOFX_AI_CONNECT_TIMEOUT", "15") or 15)
    max_tokens = int(os.getenv("NOFX_AI_FORECAST_MAX_TOKENS", "1200") or 1200)

    protocol, resolved_url = resolve_protocol_and_url(api_url, config.get("api_protocol"))
    stream = should_force_responses_stream(resolved_url, protocol)
    payload = build_payload(
        protocol,
        resolved_url,
        model,
        prompt[0],
        prompt[1],
        max_tokens,
        0.3,
        stream,
    )

    try:
        session = requests.Session()
        session.trust_env = False
        if protocol == AI_PROTOCOL_RESPONSES:
            headers["Accept"] = "text/event-stream" if stream else "application/json"
        resp = session.post(resolved_url, headers=headers, json=payload, timeout=(connect_timeout, timeout_sec))
        if resp.status_code != 200:
            if protocol == AI_PROTOCOL_RESPONSES and resp.status_code == 400:
                override_key = resolve_responses_token_key_override(resp.text)
                if override_key is not None:
                    payload = override_responses_token_key(payload, override_key, max_tokens)
                    resp = session.post(
                        resolved_url,
                        headers=headers,
                        json=payload,
                        timeout=(connect_timeout, timeout_sec),
                    )
            if resp.status_code != 200:
                if logger:
                    logger.warning("AI forecast call failed: %s - %s", resp.status_code, resp.text[:200])
                return None

        if protocol == AI_PROTOCOL_RESPONSES:
            content = parse_responses_body(resp.text)
        else:
            content = parse_compatible_content(resp.json())
        return content.strip() if content else None
    except Exception as exc:
        if logger:
            logger.warning("AI forecast call error: %s", exc)
        return None


def _parse_ai_forecast(raw: str) -> Optional[Dict[str, Any]]:
    if not raw:
        return None
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        first_newline = cleaned.find("\n")
        if first_newline != -1:
            cleaned = cleaned[first_newline + 1 :]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
    elif "```" in cleaned:
        try:
            import re

            match = re.search(r"```(?:json)?\\s*(\\{.*?\\})\\s*```", cleaned, flags=re.S)
            if match:
                cleaned = match.group(1).strip()
        except Exception:
            pass

    try:
        data = json.loads(cleaned)
    except Exception:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                data = json.loads(cleaned[start : end + 1])
            except Exception:
                data = None
        else:
            data = None
    return data if isinstance(data, dict) else None


def _build_ai_forecast(
    symbol: str,
    asset_class: str,
    score: float,
    direction: str,
    confidence: int,
    factors: List[Dict[str, Any]],
    market: Dict[str, Any],
    fundamentals: Dict[str, Any],
    futures: Dict[str, Any],
    orderbook_imbalance: Optional[Dict[str, Any]],
    price_change_1h: Optional[float],
    news: List[Dict[str, Any]],
    trending: List[Dict[str, Any]],
    sources: Optional[List[Dict[str, Any]]],
    source_weights: Optional[Dict[str, Any]],
    config: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    payload = _build_llm_payload(
        symbol,
        asset_class,
        score,
        direction,
        confidence,
        factors,
        market,
        fundamentals,
        futures,
        orderbook_imbalance,
        price_change_1h,
        news,
        trending,
        sources=sources,
        source_weights=source_weights,
    )
    raw = _call_ai_forecast(_build_llm_prompt(symbol, payload), config)
    if not raw:
        return None
    parsed = _parse_ai_forecast(raw)
    if not isinstance(parsed, dict):
        return None
    return {
        "direction": _normalize_direction(parsed.get("direction")),
        "confidence": _normalize_confidence(parsed.get("confidence")),
        "summary": str(parsed.get("summary") or "").strip(),
        "key_factors": _extract_key_factors(parsed.get("key_factors")),
        "source": "valuescan_llm",
    }


def _build_consensus(
    rule_direction: str,
    rule_confidence: int,
    ai_forecast: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    if not ai_forecast:
        return None
    ai_direction = _normalize_direction(ai_forecast.get("direction"))
    ai_confidence = _normalize_confidence(ai_forecast.get("confidence"))
    agreement = ai_direction == rule_direction
    if agreement:
        confidence = min(100, int(max(rule_confidence, ai_confidence) + 0.2 * min(rule_confidence, ai_confidence)))
        direction = ai_direction
    else:
        confidence = int(min(rule_confidence, ai_confidence) * 0.7) if min(rule_confidence, ai_confidence) else max(
            rule_confidence, ai_confidence
        )
        direction = ai_direction if ai_confidence >= rule_confidence else rule_direction
    return {
        "direction": direction,
        "confidence": confidence,
        "agreement": agreement,
        "rule_direction": rule_direction,
        "ai_direction": ai_direction,
    }


def build_symbol_forecast(symbol: str, use_llm: Optional[bool] = None) -> Optional[Dict[str, Any]]:
    symbol = symbol.upper().replace("$", "").replace("USDT", "").strip()
    if not symbol:
        return None

    market, market_sources = fetch_market_snapshot_with_sources(symbol)
    market = market or {}
    market_sources = market_sources or []
    fundamentals = fetch_fundamentals_snapshot(symbol, include_macro=True) or {}
    futures = fetch_binance_futures_snapshot(symbol) or {}
    ccxt_snapshot = fetch_ccxt_snapshot(symbol) or {}
    orderbook = fetch_ccxt_orderbook(symbol, limit=20) or {}
    news = fetch_news(limit=12)
    trending = fetch_trending(limit=8)

    df = None
    try:
        df = get_klines(symbol, timeframe="1h", limit=200)
    except Exception as exc:
        if logger:
            logger.warning("btc forecast klines failed: %s", exc)

    closes, highs, lows, volumes, price_change_1h = _extract_klines_metrics(df)

    technical = _score_technical(closes, highs, lows, volumes)
    momentum = _score_momentum(_safe_float(market.get("price_change_percent")), price_change_1h)
    orderbook_imbalance = _calc_orderbook_imbalance(orderbook)
    orderbook_score = _score_orderbook(orderbook_imbalance)
    sentiment_value = None
    sentiment = fundamentals.get("sentiment") if isinstance(fundamentals.get("sentiment"), dict) else {}
    if isinstance(sentiment, dict):
        sentiment_value = _safe_float(sentiment.get("value"))
    sentiment_score = _score_sentiment(sentiment_value)
    derivatives_score = _score_derivatives(futures, price_change_1h)

    factors = [
        {"name": "technical", **technical},
        {"name": "momentum", **momentum},
        {"name": "orderbook", **orderbook_score},
        {"name": "sentiment", **sentiment_score},
        {"name": "derivatives", **derivatives_score},
    ]

    weighted_sum = 0.0
    weight_total = 0.0
    for factor in factors:
        weight = float(factor.get("weight", 0) or 0)
        score = float(factor.get("score", 0) or 0)
        weighted_sum += score * weight
        weight_total += weight

    score = weighted_sum / weight_total if weight_total > 0 else 0.0
    direction = _score_direction(score)
    confidence = int(min(abs(score) * 100, 100))

    config = _get_ai_forecast_config()
    if use_llm is None:
        use_llm = bool(config.get("enabled"))
    ai_forecast = None
    if use_llm:
        ai_forecast = _build_ai_forecast(
            symbol,
            "crypto",
            score,
            direction,
            confidence,
            factors,
            market,
            fundamentals,
            futures,
            orderbook_imbalance,
            price_change_1h,
            news,
            trending,
            market_sources,
            {"crypto": CRYPTO_SOURCE_WEIGHTS},
            config,
        )

    consensus = _build_consensus(direction, confidence, ai_forecast)
    as_of = datetime.now(timezone.utc).isoformat()
    advice = build_investment_advice(
        consensus.get("direction") if consensus else direction,
        consensus.get("confidence") if consensus else confidence,
        factors,
        ai_summary=ai_forecast.get("summary") if ai_forecast else None,
        agreement=consensus.get("agreement") if consensus else None,
        asset_class="crypto",
        as_of=as_of,
        horizon_hours=24,
    )

    return {
        "symbol": symbol,
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
            "market_snapshot": market,
            "market_sources": market_sources,
            "futures_snapshot": futures,
            "ccxt_snapshot": ccxt_snapshot,
            "orderbook": orderbook_imbalance,
            "fundamentals": fundamentals,
            "news": news,
            "trending": trending,
            "price_change_1h": price_change_1h,
        },
    }


def build_btc_forecast(symbol: str = "BTC", use_llm: Optional[bool] = None) -> Optional[Dict[str, Any]]:
    return build_symbol_forecast(symbol, use_llm=use_llm)
