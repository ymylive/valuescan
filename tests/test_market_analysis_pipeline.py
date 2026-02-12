from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.cleaning import build_features, prevent_leakage
from src.ingestion import load_config, load_dataset, validate_and_standardize
from src.metrics import compute_kpis
from src.models import LinearRegressionModel, forecast_with_intervals
from src.pipeline import run_pipeline


ROOT = Path(__file__).resolve().parents[1]
CFG_PATH = ROOT / "config" / "market_analysis_config.yaml"
DATA_PATH = ROOT / "fixtures" / "enterprise_market_sample.csv"


def _load_prepared() -> pd.DataFrame:
    cfg = load_config(CFG_PATH)
    raw = load_dataset(DATA_PATH)
    validated, _ = validate_and_standardize(raw, cfg)
    return prevent_leakage(validated)


def test_schema_validation_required_field() -> None:
    cfg = load_config(CFG_PATH)
    raw = load_dataset(DATA_PATH)
    broken = raw.drop(columns=["revenue"])

    with pytest.raises(ValueError) as exc:
        validate_and_standardize(broken, cfg)
    assert "revenue" in str(exc.value)


def test_metrics_kpi_sanity() -> None:
    df = _load_prepared()
    kpis = compute_kpis(df)
    assert kpis["revenue"] > 0
    assert kpis["gross_profit"] < kpis["revenue"]
    assert kpis["ltv"] > 0
    assert kpis["cac"] is None or kpis["cac"] > 0


def test_model_forecast_shape_and_interval_order() -> None:
    df = _load_prepared()
    features_df, feature_cols, target_col = build_features(df)
    model = LinearRegressionModel().fit(features_df[feature_cols], features_df[target_col])

    point, lo, hi = forecast_with_intervals(
        model,
        history=features_df,
        feature_cols=feature_cols,
        horizon=7,
        seed=42,
        n_bootstrap=120,
    )
    assert len(point) == 7
    assert len(lo) == 7
    assert len(hi) == 7
    assert all(l <= p <= h for l, p, h in zip(lo, point, hi))


def test_pipeline_rejects_insufficient_rows(tmp_path: Path) -> None:
    tiny = pd.read_csv(DATA_PATH).head(10)
    tiny_path = tmp_path / "tiny.csv"
    tiny.to_csv(tiny_path, index=False)

    with pytest.raises(ValueError) as exc:
        run_pipeline(str(tiny_path), str(CFG_PATH), str(tmp_path / "out"))
    assert "insufficient rows" in str(exc.value)
