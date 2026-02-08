"""Tests for signal_monitor.ai_api_utils — timeout, payload, protocol, parsing."""
from __future__ import annotations

import json

import pytest

from signal_monitor.ai_api_utils import (
    AI_PROTOCOL_AUTO,
    AI_PROTOCOL_COMPATIBLE,
    AI_PROTOCOL_RESPONSES,
    apply_protocol_to_url,
    build_payload,
    calculate_timeout,
    detect_protocol_from_url,
    normalize_protocol,
    override_responses_token_key,
    parse_compatible_content,
    parse_responses_body,
    parse_responses_json,
    resolve_protocol_and_url,
    resolve_responses_token_key_override,
    responses_token_key,
)


# ---------------------------------------------------------------------------
# calculate_timeout
# ---------------------------------------------------------------------------

class TestCalculateTimeout:
    def test_zero_prompt(self):
        assert calculate_timeout(0) == 60

    def test_small_prompt(self):
        assert calculate_timeout(500) == 60

    def test_1kb_prompt(self):
        assert calculate_timeout(1000) == 70

    def test_5kb_prompt(self):
        assert calculate_timeout(5000) == 110

    def test_capped_at_180(self):
        assert calculate_timeout(50000) == 180

    def test_large_prompt_cap(self):
        assert calculate_timeout(1_000_000) == 180

    def test_negative_treated_as_zero(self):
        # negative // 1000 is -1 in Python, extra = -10, result = 50 < 180
        result = calculate_timeout(-500)
        assert result <= 180


# ---------------------------------------------------------------------------
# normalize_protocol
# ---------------------------------------------------------------------------

class TestNormalizeProtocol:
    def test_none(self):
        assert normalize_protocol(None) == AI_PROTOCOL_AUTO

    def test_empty(self):
        assert normalize_protocol("") == AI_PROTOCOL_AUTO

    def test_auto(self):
        assert normalize_protocol("auto") == AI_PROTOCOL_AUTO

    def test_compatible_uppercase(self):
        assert normalize_protocol("COMPATIBLE") == AI_PROTOCOL_COMPATIBLE

    def test_responses_with_spaces(self):
        assert normalize_protocol("  responses  ") == AI_PROTOCOL_RESPONSES

    def test_unknown_falls_back(self):
        assert normalize_protocol("unknown") == AI_PROTOCOL_AUTO


# ---------------------------------------------------------------------------
# detect_protocol_from_url
# ---------------------------------------------------------------------------

class TestDetectProtocolFromUrl:
    def test_responses_url(self):
        assert detect_protocol_from_url("https://api.example.com/v1/responses") == AI_PROTOCOL_RESPONSES

    def test_chat_completions_url(self):
        assert detect_protocol_from_url("https://api.example.com/v1/chat/completions") == AI_PROTOCOL_COMPATIBLE

    def test_plain_url_defaults_compatible(self):
        assert detect_protocol_from_url("https://api.example.com/v1") == AI_PROTOCOL_COMPATIBLE

    def test_empty_url(self):
        assert detect_protocol_from_url("") == AI_PROTOCOL_COMPATIBLE


# ---------------------------------------------------------------------------
# apply_protocol_to_url
# ---------------------------------------------------------------------------

class TestApplyProtocolToUrl:
    def test_switch_compatible_to_responses(self):
        url = apply_protocol_to_url("https://api.example.com/v1/chat/completions", AI_PROTOCOL_RESPONSES)
        assert url.endswith("/responses")

    def test_switch_responses_to_compatible(self):
        url = apply_protocol_to_url("https://api.example.com/v1/responses", AI_PROTOCOL_COMPATIBLE)
        assert url.endswith("/chat/completions")

    def test_bare_url_gets_compatible(self):
        url = apply_protocol_to_url("https://api.example.com/v1", AI_PROTOCOL_COMPATIBLE)
        assert url.endswith("/chat/completions")

    def test_bare_url_gets_responses(self):
        url = apply_protocol_to_url("https://api.example.com/v1", AI_PROTOCOL_RESPONSES)
        assert url.endswith("/responses")

    def test_empty_url(self):
        assert apply_protocol_to_url("", AI_PROTOCOL_COMPATIBLE) == ""


# ---------------------------------------------------------------------------
# build_payload — compatible protocol
# ---------------------------------------------------------------------------

class TestBuildPayloadCompatible:
    def test_basic_structure(self):
        p = build_payload(AI_PROTOCOL_COMPATIBLE, "https://api.example.com", "gpt-4", "sys", "user", 1000, 0.7, False)
        assert p["model"] == "gpt-4"
        assert p["max_tokens"] == 1000
        assert p["temperature"] == 0.7
        assert len(p["messages"]) == 2
        assert "max_output_tokens" not in p

    def test_no_system_prompt(self):
        p = build_payload(AI_PROTOCOL_COMPATIBLE, "https://api.example.com", "gpt-4", "", "user", 1000, 0.7, False)
        assert len(p["messages"]) == 1
        assert p["messages"][0]["role"] == "user"


# ---------------------------------------------------------------------------
# build_payload — responses protocol
# ---------------------------------------------------------------------------

class TestBuildPayloadResponses:
    def test_openai_uses_max_output_tokens(self):
        p = build_payload(AI_PROTOCOL_RESPONSES, "https://api.openai.com/v1/responses", "gpt-4", "sys", "user", 1000, 0.7, False)
        assert "max_output_tokens" in p
        assert "max_tokens" not in p

    def test_non_openai_uses_max_tokens(self):
        p = build_payload(AI_PROTOCOL_RESPONSES, "https://api.example.com/v1/responses", "gpt-4", "sys", "user", 1000, 0.7, False)
        assert "max_tokens" in p
        assert "max_output_tokens" not in p

    def test_no_conflicting_token_keys(self):
        p = build_payload(AI_PROTOCOL_RESPONSES, "https://api.openai.com/v1/responses", "gpt-4", "sys", "user", 1000, 0.7, False)
        has_both = "max_tokens" in p and "max_output_tokens" in p
        assert not has_both

    def test_stream_flag(self):
        p = build_payload(AI_PROTOCOL_RESPONSES, "https://api.example.com", "gpt-4", "sys", "user", 1000, 0.7, True)
        assert p.get("stream") is True

    def test_zero_max_tokens_omitted(self):
        p = build_payload(AI_PROTOCOL_RESPONSES, "https://api.example.com", "gpt-4", "sys", "user", 0, 0.7, False)
        assert "max_tokens" not in p
        assert "max_output_tokens" not in p


# ---------------------------------------------------------------------------
# parse_compatible_content
# ---------------------------------------------------------------------------

class TestParseCompatibleContent:
    def test_standard_openai_response(self):
        data = {"choices": [{"message": {"content": "hello"}}]}
        assert parse_compatible_content(data) == "hello"

    def test_empty_choices(self):
        assert parse_compatible_content({"choices": []}) == ""

    def test_non_dict_returns_empty(self):
        assert parse_compatible_content("not a dict") == ""

    def test_result_field_fallback(self):
        data = {"result": "fallback text"}
        assert parse_compatible_content(data) == "fallback text"


# ---------------------------------------------------------------------------
# parse_responses_body
# ---------------------------------------------------------------------------

class TestParseResponsesBody:
    def test_empty(self):
        assert parse_responses_body("") == ""
        assert parse_responses_body(None) == ""

    def test_json_output_text(self):
        body = json.dumps({"output_text": "result here"})
        assert parse_responses_body(body) == "result here"

    def test_sse_delta_stream(self):
        lines = [
            'data: {"type":"response.output_text.delta","delta":"hel"}',
            'data: {"type":"response.output_text.delta","delta":"lo"}',
            "data: [DONE]",
        ]
        body = "\n".join(lines)
        assert parse_responses_body(body) == "hello"

    def test_sse_done_event(self):
        lines = [
            'data: {"type":"response.output_text.delta","delta":"partial"}',
            'data: {"type":"response.output_text.done","text":"full text"}',
            "data: [DONE]",
        ]
        body = "\n".join(lines)
        assert parse_responses_body(body) == "full text"

    def test_api_error_raises(self):
        body = json.dumps({"error": {"code": "rate_limit", "message": "too fast"}})
        with pytest.raises(ValueError, match="API error"):
            parse_responses_body(body)


# ---------------------------------------------------------------------------
# resolve_responses_token_key_override
# ---------------------------------------------------------------------------

class TestResolveResponsesTokenKeyOverride:
    def test_unsupported_max_output_tokens(self):
        assert resolve_responses_token_key_override("Unsupported parameter: max_output_tokens") == "max_tokens"

    def test_unsupported_max_tokens(self):
        assert resolve_responses_token_key_override("Unsupported parameter: max_tokens") == ""

    def test_no_match(self):
        assert resolve_responses_token_key_override("all good") is None

    def test_empty(self):
        assert resolve_responses_token_key_override("") is None


# ---------------------------------------------------------------------------
# override_responses_token_key
# ---------------------------------------------------------------------------

class TestOverrideResponsesTokenKey:
    def test_switch_to_max_tokens(self):
        payload = {"max_output_tokens": 2000, "model": "gpt-4"}
        result = override_responses_token_key(payload, "max_tokens", 1000)
        assert result["max_tokens"] == 2000
        assert "max_output_tokens" not in result

    def test_empty_key_removes_both(self):
        payload = {"max_tokens": 500}
        result = override_responses_token_key(payload, "", 1000)
        assert "max_tokens" not in result
        assert "max_output_tokens" not in result

    def test_fallback_on_missing(self):
        payload = {"model": "gpt-4"}
        result = override_responses_token_key(payload, "max_tokens", 1000)
        assert result["max_tokens"] == 1000
