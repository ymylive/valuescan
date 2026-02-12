"""Deterministic tests for signal tracker core flow."""

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from signal_monitor.signal_tracker import SignalTracker


def test_confluence_detected_at_window_boundary():
    tracker = SignalTracker(window_seconds=120)
    base_ts = 1_700_000_000_000

    assert tracker.add_signal("BTC", "alpha", 100.0, "alpha-1", base_ts) is False
    assert tracker.add_signal("BTC", "fomo", 101.0, "fomo-1", base_ts + 120_000) is True


def test_confluence_respects_cooldown_then_retriggers_after_expiry():
    tracker = SignalTracker(window_seconds=120)
    base_ts = 1_700_000_000_000

    assert tracker.add_signal("ETH", "alpha", 2000.0, "alpha-1", base_ts) is False
    assert tracker.add_signal("ETH", "fomo", 2001.0, "fomo-1", base_ts + 1_000) is True

    assert tracker.add_signal("ETH", "alpha", 2002.0, "alpha-2", base_ts + 2_000) is False

    cooldown_expired_ts = base_ts + tracker.confluence_cooldown * 1000 + 10_000
    assert tracker.add_signal("ETH", "alpha", 2003.0, "alpha-3", cooldown_expired_ts) is False
    assert tracker.add_signal("ETH", "fomo", 2004.0, "fomo-2", cooldown_expired_ts + 1_000) is True


def test_cleanup_removes_expired_signals_for_symbol():
    tracker = SignalTracker(window_seconds=10)
    base_ts = 1_800_000_000_000

    assert tracker.add_signal("SOL", "alpha", 150.0, "alpha-1", base_ts) is False
    assert tracker.add_signal("SOL", "fomo", 151.0, "fomo-1", base_ts + 1_000) is True

    assert tracker.add_signal("SOL", "alpha", 152.0, "alpha-2", base_ts + 11_001) is False

    assert len(tracker.signals["SOL"]["alpha"]) == 1
    assert len(tracker.signals["SOL"]["fomo"]) == 0
    assert tracker.signals["SOL"]["alpha"][0]["message_id"] == "alpha-2"
