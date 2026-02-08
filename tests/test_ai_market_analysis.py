"""Tests for signal_monitor.ai_market_analysis — parse, validate, analysis cache."""
from __future__ import annotations

import json
import time as _time_mod

import pytest

from signal_monitor.ai_market_analysis import (
    _analysis_cache,
    _ANALYSIS_CACHE_MAX,
    parse_ai_analysis,
    validate_and_clean_analysis,
)


# ---------------------------------------------------------------------------
# parse_ai_analysis
# ---------------------------------------------------------------------------

class TestParseAiAnalysis:
    def test_valid_json(self):
        raw = json.dumps({"trend": {"direction": "bullish"}})
        result = parse_ai_analysis(raw)
        assert result is not None
        assert result["trend"]["direction"] == "bullish"

    def test_json_with_markdown_fence(self):
        raw = '```json\n{"trend": {"direction": "bearish"}}\n```'
        result = parse_ai_analysis(raw)
        assert result is not None
        assert result["trend"]["direction"] == "bearish"

    def test_json_with_leading_text(self):
        raw = 'Here is the analysis:\n{"summary": "test"}'
        result = parse_ai_analysis(raw)
        assert result is not None
        assert result["summary"] == "test"

    def test_empty_returns_none(self):
        assert parse_ai_analysis("") is None
        assert parse_ai_analysis(None) is None

    def test_invalid_json_returns_none(self):
        assert parse_ai_analysis("not json at all") is None

    def test_list_json_returns_none(self):
        # Only dicts are accepted
        assert parse_ai_analysis("[1, 2, 3]") is None


# ---------------------------------------------------------------------------
# validate_and_clean_analysis
# ---------------------------------------------------------------------------

class TestValidateAndCleanAnalysis:
    def test_supports_below_price_kept(self):
        analysis = {
            "key_levels": {
                "supports": [
                    {"price": 90, "strength": 80, "reason": "test"},
                    {"price": 110, "strength": 50, "reason": "above price"},
                ],
                "resistances": [],
            }
        }
        result = validate_and_clean_analysis(analysis, current_price=100.0)
        assert len(result["key_levels"]["supports"]) == 1
        assert result["key_levels"]["supports"][0]["price"] == 90

    def test_resistances_above_price_kept(self):
        analysis = {
            "key_levels": {
                "supports": [],
                "resistances": [
                    {"price": 110, "strength": 70, "reason": "above"},
                    {"price": 80, "strength": 60, "reason": "below price"},
                ],
            }
        }
        result = validate_and_clean_analysis(analysis, current_price=100.0)
        assert len(result["key_levels"]["resistances"]) == 1
        assert result["key_levels"]["resistances"][0]["price"] == 110

    def test_max_5_levels(self):
        supports = [{"price": float(i), "strength": 50, "reason": "s"} for i in range(10)]
        analysis = {"key_levels": {"supports": supports, "resistances": []}}
        result = validate_and_clean_analysis(analysis, current_price=100.0)
        assert len(result["key_levels"]["supports"]) <= 5

    def test_missing_trend_gets_default(self):
        result = validate_and_clean_analysis({}, current_price=100.0)
        assert result["trend"]["direction"] == "sideways"
        assert result["trend"]["strength"] == 50

    def test_missing_sentiment_gets_default(self):
        result = validate_and_clean_analysis({}, current_price=100.0)
        assert result["sentiment"]["score"] == 0

    def test_missing_summary_gets_default(self):
        result = validate_and_clean_analysis({}, current_price=100.0)
        assert isinstance(result["summary"], str)
        assert len(result["summary"]) > 0

    def test_existing_fields_preserved(self):
        analysis = {
            "trend": {"direction": "bullish", "strength": 80, "description": "Strong"},
            "sentiment": {"score": 50, "description": "Positive"},
            "summary": "Custom summary",
        }
        result = validate_and_clean_analysis(analysis, current_price=100.0)
        assert result["trend"]["direction"] == "bullish"
        assert result["sentiment"]["score"] == 50
        assert result["summary"] == "Custom summary"

    def test_non_dict_support_items_filtered(self):
        analysis = {
            "key_levels": {
                "supports": [50, "invalid", {"price": 90, "strength": 70, "reason": "ok"}],
                "resistances": [],
            }
        }
        result = validate_and_clean_analysis(analysis, current_price=100.0)
        assert len(result["key_levels"]["supports"]) == 1


# ---------------------------------------------------------------------------
# Analysis cache behavior
# ---------------------------------------------------------------------------

class TestAnalysisCache:
    def setup_method(self):
        _analysis_cache.clear()

    def test_cache_stores_and_retrieves(self):
        _analysis_cache["BTC"] = (_time_mod.monotonic(), {"summary": "cached"})
        ts, result = _analysis_cache["BTC"]
        assert result["summary"] == "cached"

    def test_cache_eviction_on_max(self):
        # Fill cache beyond max
        now = _time_mod.monotonic()
        for i in range(_ANALYSIS_CACHE_MAX + 5):
            _analysis_cache[f"SYM{i}"] = (now + i, {"i": i})
        # Simulate eviction logic (same as in get_ai_market_analysis)
        while len(_analysis_cache) > _ANALYSIS_CACHE_MAX:
            oldest_key = min(_analysis_cache, key=lambda k: _analysis_cache[k][0])
            del _analysis_cache[oldest_key]
        assert len(_analysis_cache) == _ANALYSIS_CACHE_MAX

    def test_cache_max_is_200(self):
        assert _ANALYSIS_CACHE_MAX == 200

    def teardown_method(self):
        _analysis_cache.clear()
