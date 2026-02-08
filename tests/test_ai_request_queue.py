"""Tests for signal_monitor.ai_request_queue — rate limiting, backoff, empty response."""
from __future__ import annotations

import threading
import time
from unittest.mock import patch

import pytest

from signal_monitor.ai_request_queue import (
    _calculate_backoff,
    _is_429_error,
    call_ai_with_queue,
)


# ---------------------------------------------------------------------------
# _calculate_backoff
# ---------------------------------------------------------------------------

class TestCalculateBackoff:
    def test_attempt_1(self):
        assert _calculate_backoff(1) == 2.0

    def test_attempt_2(self):
        assert _calculate_backoff(2) == 4.0

    def test_attempt_5(self):
        assert _calculate_backoff(5) == 32.0

    def test_capped_at_300(self):
        assert _calculate_backoff(10) == 300.0
        assert _calculate_backoff(20) == 300.0

    def test_attempt_0(self):
        assert _calculate_backoff(0) == 1.0


# ---------------------------------------------------------------------------
# _is_429_error
# ---------------------------------------------------------------------------

class TestIs429Error:
    def test_status_code_429(self):
        assert _is_429_error(Exception("HTTP 429 error"))

    def test_too_many_requests(self):
        assert _is_429_error(Exception("Too Many Requests"))

    def test_capacity(self):
        assert _is_429_error(Exception("no capacity available"))

    def test_normal_error(self):
        assert not _is_429_error(Exception("connection timeout"))

    def test_empty_message(self):
        assert not _is_429_error(Exception(""))


# ---------------------------------------------------------------------------
# call_ai_with_queue — success path
# ---------------------------------------------------------------------------

class TestCallAiWithQueueSuccess:
    def test_returns_result(self):
        result = call_ai_with_queue(lambda: "hello", attempts=1, retry_delay=0)
        assert result == "hello"

    def test_returns_dict(self):
        payload = {"key": "value"}
        result = call_ai_with_queue(lambda: payload, attempts=1, retry_delay=0)
        assert result == payload


# ---------------------------------------------------------------------------
# call_ai_with_queue — empty response handling
# ---------------------------------------------------------------------------

class TestCallAiWithQueueEmptyResponse:
    def test_empty_string_returns_none(self):
        result = call_ai_with_queue(lambda: "", attempts=1, retry_delay=0)
        assert result is None

    def test_none_returns_none(self):
        result = call_ai_with_queue(lambda: None, attempts=1, retry_delay=0)
        assert result is None

    def test_empty_does_not_raise(self):
        # Should NOT raise even with raise_on_error=True, because empty is not an error
        result = call_ai_with_queue(lambda: "", attempts=1, retry_delay=0, raise_on_error=True)
        assert result is None


# ---------------------------------------------------------------------------
# call_ai_with_queue — error handling
# ---------------------------------------------------------------------------

class TestCallAiWithQueueErrors:
    def test_error_returns_none_by_default(self):
        result = call_ai_with_queue(
            lambda: (_ for _ in ()).throw(RuntimeError("fail")),
            attempts=1,
            retry_delay=0,
        )
        assert result is None

    def test_error_raises_when_requested(self):
        with pytest.raises(RuntimeError, match="fail"):
            call_ai_with_queue(
                lambda: (_ for _ in ()).throw(RuntimeError("fail")),
                attempts=1,
                retry_delay=0,
                raise_on_error=True,
            )

    def test_retries_on_failure(self):
        counter = {"n": 0}

        def flaky():
            counter["n"] += 1
            if counter["n"] < 3:
                raise RuntimeError("transient")
            return "ok"

        result = call_ai_with_queue(flaky, attempts=3, retry_delay=0.01)
        assert result == "ok"
        assert counter["n"] == 3
