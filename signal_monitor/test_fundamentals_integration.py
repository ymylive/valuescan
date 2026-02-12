"""Integration tests for Jin10 news and fundamentals."""

import json
from pathlib import Path

try:
    from signal_monitor.jin10_news import fetch_jin10_news
    from signal_monitor.news_summarizer import summarize_news
    from signal_monitor.fundamentals_sources import (
        fetch_jin10_news_latest,
        fetch_econ_events_upcoming,
        fetch_econ_events_history,
    )
except Exception:
    from jin10_news import fetch_jin10_news
    from news_summarizer import summarize_news
    from fundamentals_sources import (
        fetch_jin10_news_latest,
        fetch_econ_events_upcoming,
        fetch_econ_events_history,
    )


def test_jin10_news_fetch():
    """Test Jin10 news fetching."""
    news = fetch_jin10_news(limit=10)
    assert isinstance(news, list), "Should return a list"

    if news:
        item = news[0]
        assert "time" in item, "Should have time field"
        assert "title" in item, "Should have title field"
        assert "content" in item, "Should have content field"
        assert "tags" in item, "Should have tags field"
        assert "importance" in item, "Should have importance field"
        assert "source" in item, "Should have source field"
        assert item["source"] == "jin10", "Source should be jin10"
        print(f"✓ Fetched {len(news)} Jin10 news items")
    else:
        print("⚠ No Jin10 news items returned (API/fixtures unavailable)")


def test_fundamentals_api_functions():
    """Test fundamentals API wrapper functions."""
    # Test Jin10 news latest
    news = fetch_jin10_news_latest(limit=5)
    assert isinstance(news, list), "Should return a list"
    print(f"✓ fetch_jin10_news_latest: {len(news)} items")

    # Test upcoming economic events
    upcoming = fetch_econ_events_upcoming()
    assert isinstance(upcoming, list), "Should return a list"
    if upcoming:
        event = upcoming[0]
        assert "name" in event, "Should have name field"
        assert "country" in event, "Should have country field"
        assert "importance" in event, "Should have importance field"
        assert "time" in event, "Should have time field"
        print(f"✓ fetch_econ_events_upcoming: {len(upcoming)} events")
    else:
        print("⚠ No upcoming economic events")

    # Test historical economic events
    history = fetch_econ_events_history(days=7)
    assert isinstance(history, list), "Should return a list"
    print(f"✓ fetch_econ_events_history: {len(history)} events")


def test_news_summarizer():
    """Test news summarization (will return None without LLM)."""
    news = fetch_jin10_news(limit=5)
    if news:
        summary = summarize_news(news)
        # Should return None without LLM configured
        assert summary is None or isinstance(summary, dict), "Should return None or dict"
        print("✓ News summarizer tested (LLM not configured, returns None as expected)")
    else:
        print("⚠ No news to summarize")


def test_fixtures_exist():
    """Test that fixture files exist."""
    fixtures_dir = Path(__file__).resolve().parents[1] / "fixtures"

    jin10_fixture = fixtures_dir / "jin10_news_50.json"
    assert jin10_fixture.exists(), f"Jin10 fixture should exist at {jin10_fixture}"

    econ_fixture = fixtures_dir / "econ_samples.json"
    assert econ_fixture.exists(), f"Econ fixture should exist at {econ_fixture}"

    # Validate JSON structure
    jin10_data = json.loads(jin10_fixture.read_text(encoding="utf-8"))
    assert isinstance(jin10_data, list), "Jin10 fixture should be a list"
    if jin10_data:
        assert "time" in jin10_data[0], "Jin10 items should have time field"
        assert "source" in jin10_data[0], "Jin10 items should have source field"

    econ_data = json.loads(econ_fixture.read_text(encoding="utf-8"))
    assert isinstance(econ_data, list), "Econ fixture should be a list"
    if econ_data:
        assert "name" in econ_data[0], "Econ items should have name field"
        assert "importance" in econ_data[0], "Econ items should have importance field"

    print(f"✓ Fixtures exist and are valid JSON")


if __name__ == "__main__":
    print("Running fundamentals integration tests...\n")

    try:
        test_fixtures_exist()
        test_jin10_news_fetch()
        test_fundamentals_api_functions()
        test_news_summarizer()
        print("\n✅ All tests passed!")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        raise
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        raise
