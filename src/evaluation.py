from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd

from src.models import BaselineModel, LinearRegressionModel


def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    denom = np.where(np.abs(y_true) < 1e-8, np.nan, np.abs(y_true))
    return float(np.nanmean(np.abs((y_true - y_pred) / denom)) * 100)


def rolling_backtest(
    df: pd.DataFrame,
    feature_cols: List[str],
    target_col: str,
    min_train_size: int = 30,
    test_window: int = 7,
    seasonal_period: int = 7,
    embargo: int = 1,
) -> Dict[str, Any]:
    baseline_scores: List[Dict[str, float]] = []
    seasonal_scores: List[Dict[str, float]] = []
    linear_scores: List[Dict[str, float]] = []

    for end in range(min_train_size, len(df) - test_window - embargo + 1, test_window):
        train = df.iloc[:end]
        test_start = end + embargo
        test = df.iloc[test_start : test_start + test_window]
        if len(test) == 0:
            continue

        y_train = train[target_col]
        y_test = test[target_col].to_numpy(dtype=float)

        baseline = BaselineModel().fit(y_train)
        pred_base = baseline.predict(len(test))

        if len(y_train) >= seasonal_period:
            season = y_train.iloc[-seasonal_period:].to_numpy(dtype=float)
            repeats = int(np.ceil(len(test) / seasonal_period))
            pred_seasonal = np.tile(season, repeats)[: len(test)]
        else:
            pred_seasonal = pred_base

        linear = LinearRegressionModel().fit(train[feature_cols], y_train)
        pred_linear = linear.predict(test[feature_cols])

        baseline_scores.append({"rmse": rmse(y_test, pred_base), "mape": mape(y_test, pred_base)})
        seasonal_scores.append({"rmse": rmse(y_test, pred_seasonal), "mape": mape(y_test, pred_seasonal)})
        linear_scores.append({"rmse": rmse(y_test, pred_linear), "mape": mape(y_test, pred_linear)})

    def _avg(items: List[Dict[str, float]], key: str) -> float:
        return round(float(np.mean([x[key] for x in items])) if items else 0.0, 4)

    return {
        "baseline": {
            "rmse": _avg(baseline_scores, "rmse"),
            "mape": _avg(baseline_scores, "mape"),
        },
        "seasonal_baseline": {
            "rmse": _avg(seasonal_scores, "rmse"),
            "mape": _avg(seasonal_scores, "mape"),
        },
        "linear_regression": {
            "rmse": _avg(linear_scores, "rmse"),
            "mape": _avg(linear_scores, "mape"),
        },
        "windows": len(baseline_scores),
    }
