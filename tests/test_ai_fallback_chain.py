"""AI fallback chain tests."""

from __future__ import annotations

from typing import Any, Dict, List

import api.server as server_module
import signal_monitor.ai_signal_analysis as ai_module


class _FakeResponse:
    def __init__(self, status_code: int, text: str = "", body: Dict[str, Any] | None = None) -> None:
        self.status_code = status_code
        self.text = text
        self._body = body or {}

    def json(self) -> Dict[str, Any]:
        return self._body


def test_build_ai_provider_chain_keeps_priority_and_skips_invalid_items() -> None:
    config = {
        "api_key": "primary-key",
        "api_url": "https://primary.example/v1",
        "model": "primary-model",
        "fallbacks": [
            {"api_key": "fallback-1-key", "api_url": "https://fallback-1.example/v1", "model": "fallback-1"},
            {"api_key": "missing-model", "api_url": "https://invalid.example/v1"},
            "invalid-item",
            {
                "api_key": "fallback-2-key",
                "api_url": "https://fallback-2.example/v1",
                "model": "fallback-2",
                "api_protocol": "responses",
            },
        ],
    }

    providers = ai_module._build_ai_provider_chain(config)

    assert [item["api_url"] for item in providers] == [
        "https://primary.example/v1",
        "https://fallback-1.example/v1",
        "https://fallback-2.example/v1",
    ]
    assert providers[0]["api_protocol"] == "auto"
    assert providers[2]["api_protocol"] == "responses"


def test_call_ai_api_fallbacks_from_primary_to_next_provider(monkeypatch) -> None:
    monkeypatch.setenv("NOFX_AI_API_RETRY", "0")
    monkeypatch.setenv("NOFX_AI_TRUST_ENV", "0")
    monkeypatch.setattr(ai_module, "_get_ai_proxies", lambda: None)
    monkeypatch.setattr(ai_module, "_is_gemini_provider", lambda _provider: False)
    monkeypatch.setattr(ai_module, "resolve_protocol_and_url", lambda api_url, _api_protocol: ("compatible", api_url))
    monkeypatch.setattr(ai_module, "should_force_responses_stream", lambda _url, _protocol: False)
    monkeypatch.setattr(ai_module, "build_payload", lambda *args, **kwargs: {"ok": True})
    monkeypatch.setattr(ai_module, "parse_compatible_content", lambda data: data.get("content"))
    monkeypatch.setattr(ai_module, "_strip_thoughts", lambda text: text)

    call_urls: List[str] = []
    responses = iter(
        [
            _FakeResponse(500, "primary failed"),
            _FakeResponse(200, body={"content": "fallback success"}),
        ]
    )

    class _FakeSession:
        trust_env = False

        def post(self, url, **kwargs):  # type: ignore[no-untyped-def]
            call_urls.append(url)
            return next(responses)

    monkeypatch.setattr(ai_module.requests, "Session", _FakeSession)

    config = {
        "api_key": "k1",
        "api_url": "https://primary.example/v1",
        "model": "m1",
        "fallbacks": [
            {"api_key": "k2", "api_url": "https://fallback.example/v1", "model": "m2"},
        ],
    }
    result = ai_module._call_ai_api("test prompt", config)

    assert result == "fallback success"
    assert call_urls == [
        "https://primary.example/v1",
        "https://fallback.example/v1",
    ]


def test_call_ai_api_returns_none_when_all_providers_fail(monkeypatch) -> None:
    monkeypatch.setenv("NOFX_AI_API_RETRY", "0")
    monkeypatch.setattr(ai_module, "_get_ai_proxies", lambda: None)
    monkeypatch.setattr(ai_module, "_is_gemini_provider", lambda _provider: False)
    monkeypatch.setattr(ai_module, "resolve_protocol_and_url", lambda api_url, _api_protocol: ("compatible", api_url))
    monkeypatch.setattr(ai_module, "should_force_responses_stream", lambda _url, _protocol: False)
    monkeypatch.setattr(ai_module, "build_payload", lambda *args, **kwargs: {"ok": True})

    call_urls: List[str] = []
    responses = iter(
        [
            _FakeResponse(500, "primary failed"),
            _FakeResponse(503, "fallback failed"),
        ]
    )

    class _FakeSession:
        trust_env = False

        def post(self, url, **kwargs):  # type: ignore[no-untyped-def]
            call_urls.append(url)
            return next(responses)

    monkeypatch.setattr(ai_module.requests, "Session", _FakeSession)

    config = {
        "api_key": "k1",
        "api_url": "https://primary.example/v1",
        "model": "m1",
        "fallbacks": [
            {"api_key": "k2", "api_url": "https://fallback.example/v1", "model": "m2"},
        ],
    }

    assert ai_module._call_ai_api("test prompt", config) is None
    assert call_urls == [
        "https://primary.example/v1",
        "https://fallback.example/v1",
    ]


def test_api_server_fallback_reports_provider_index(monkeypatch) -> None:
    calls: List[str] = []

    def _fake_call(api_url: str, api_key: str, model: str, api_protocol=None) -> Dict[str, Any]:
        calls.append(api_url)
        if api_url == "https://primary.example/v1":
            return {"success": False, "message": "primary failed"}
        return {"success": True}

    monkeypatch.setattr(server_module, "_call_ai_test", _fake_call)

    config = {
        "api_url": "https://primary.example/v1",
        "api_key": "k1",
        "model": "m1",
        "fallbacks": [
            {"api_url": "https://fallback.example/v1", "api_key": "k2", "model": "m2"},
        ],
    }
    result = server_module._call_ai_test_with_fallbacks(config)

    assert result["success"] is True
    assert result["provider_index"] == 2
    assert calls == [
        "https://primary.example/v1",
        "https://fallback.example/v1",
    ]
