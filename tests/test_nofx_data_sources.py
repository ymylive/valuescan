import pytest

from signal_monitor.nofx_data_sources import (
    fetch_nofx_competition,
    fetch_nofx_public_strategies,
    fetch_nofx_top_traders,
)


def _skip_if_unavailable(payload, label):
    if payload is None:
        pytest.skip(f"NOFX {label} unavailable")
    if not isinstance(payload, dict):
        pytest.skip(f"NOFX {label} returned non-dict payload")


def test_nofx_competition_shape():
    data = fetch_nofx_competition(limit=1)
    _skip_if_unavailable(data, "competition")
    assert "traders" in data


def test_nofx_top_traders_shape():
    data = fetch_nofx_top_traders(limit=1)
    _skip_if_unavailable(data, "top traders")
    assert "traders" in data


def test_nofx_public_strategies_shape():
    data = fetch_nofx_public_strategies(limit=1)
    _skip_if_unavailable(data, "public strategies")
    assert "strategies" in data
