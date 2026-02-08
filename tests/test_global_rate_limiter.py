"""Tests for signal_monitor.global_rate_limiter — token bucket, multi-source, thread safety."""
from __future__ import annotations

import threading
import time

import pytest

from signal_monitor.global_rate_limiter import GlobalRateLimiter, get_global_limiter


# ---------------------------------------------------------------------------
# Token bucket basics
# ---------------------------------------------------------------------------

class TestTokenBucketBasics:
    def test_acquire_succeeds_within_limit(self):
        limiter = GlobalRateLimiter()
        assert limiter.acquire("binance") is True

    def test_acquire_unknown_source_allowed(self):
        limiter = GlobalRateLimiter()
        assert limiter.acquire("unknown_source_xyz") is True

    def test_exhaust_tokens_then_reject(self):
        limiter = GlobalRateLimiter()
        limiter.add_source("test_src", limit=3, window=60)
        assert limiter.acquire("test_src") is True
        assert limiter.acquire("test_src") is True
        assert limiter.acquire("test_src") is True
        assert limiter.acquire("test_src") is False

    def test_multi_token_acquire(self):
        limiter = GlobalRateLimiter()
        limiter.add_source("test_src", limit=5, window=60)
        assert limiter.acquire("test_src", tokens=3) is True
        assert limiter.acquire("test_src", tokens=3) is False
        assert limiter.acquire("test_src", tokens=2) is True


# ---------------------------------------------------------------------------
# Token refill
# ---------------------------------------------------------------------------

class TestTokenRefill:
    def test_tokens_refill_over_time(self):
        limiter = GlobalRateLimiter()
        limiter.add_source("refill_test", limit=10, window=1)
        # Exhaust all tokens
        for _ in range(10):
            limiter.acquire("refill_test")
        assert limiter.acquire("refill_test") is False
        # Wait for refill (window=1s, so 1s should fully refill)
        time.sleep(1.1)
        assert limiter.acquire("refill_test") is True


# ---------------------------------------------------------------------------
# Multi-source isolation
# ---------------------------------------------------------------------------

class TestMultiSourceIsolation:
    def test_sources_independent(self):
        limiter = GlobalRateLimiter()
        limiter.add_source("src_a", limit=2, window=60)
        limiter.add_source("src_b", limit=2, window=60)
        # Exhaust src_a
        limiter.acquire("src_a")
        limiter.acquire("src_a")
        assert limiter.acquire("src_a") is False
        # src_b should still work
        assert limiter.acquire("src_b") is True

    def test_case_insensitive(self):
        limiter = GlobalRateLimiter()
        limiter.add_source("MySource", limit=2, window=60)
        assert limiter.acquire("MYSOURCE") is True
        assert limiter.acquire("mysource") is True
        assert limiter.acquire("MySource") is False


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

class TestStatistics:
    def test_stats_track_success_and_reject(self):
        limiter = GlobalRateLimiter()
        limiter.add_source("stats_src", limit=1, window=60)
        limiter.acquire("stats_src")  # success
        limiter.acquire("stats_src")  # rejected
        stats = limiter.get_stats("stats_src")
        assert stats["stats"]["successful_requests"] == 1
        assert stats["stats"]["rejected_requests"] == 1
        assert stats["stats"]["total_requests"] == 2

    def test_get_all_stats(self):
        limiter = GlobalRateLimiter()
        limiter.acquire("binance")
        stats = limiter.get_stats()
        assert "stats" in stats
        assert "limiters" in stats

    def test_reset_stats(self):
        limiter = GlobalRateLimiter()
        limiter.acquire("binance")
        limiter.reset_stats()
        stats = limiter.get_stats("binance")
        assert stats["stats"] == {}


# ---------------------------------------------------------------------------
# add_source
# ---------------------------------------------------------------------------

class TestAddSource:
    def test_add_new_source(self):
        limiter = GlobalRateLimiter()
        limiter.add_source("custom_api", limit=50, window=30)
        stats = limiter.get_stats("custom_api")
        assert stats["limiter"]["limit"] == 50
        assert stats["limiter"]["window"] == 30

    def test_override_existing_source(self):
        limiter = GlobalRateLimiter()
        limiter.add_source("binance", limit=5, window=10)
        stats = limiter.get_stats("binance")
        assert stats["limiter"]["limit"] == 5


# ---------------------------------------------------------------------------
# wait_and_acquire
# ---------------------------------------------------------------------------

class TestWaitAndAcquire:
    def test_immediate_acquire(self):
        limiter = GlobalRateLimiter()
        assert limiter.wait_and_acquire("binance", timeout=1.0) is True

    def test_timeout_raises(self):
        limiter = GlobalRateLimiter()
        limiter.add_source("tiny", limit=1, window=60)
        limiter.acquire("tiny")  # exhaust
        with pytest.raises(TimeoutError):
            limiter.wait_and_acquire("tiny", timeout=0.5)


# ---------------------------------------------------------------------------
# Thread safety
# ---------------------------------------------------------------------------

class TestThreadSafety:
    def test_concurrent_acquire(self):
        limiter = GlobalRateLimiter()
        limiter.add_source("concurrent", limit=100, window=60)
        results = []

        def worker():
            for _ in range(10):
                results.append(limiter.acquire("concurrent"))

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        success_count = sum(1 for r in results if r)
        fail_count = sum(1 for r in results if not r)
        assert success_count == 100
        assert fail_count == 0


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

class TestSingleton:
    def test_get_global_limiter_returns_same_instance(self):
        a = get_global_limiter()
        b = get_global_limiter()
        assert a is b
