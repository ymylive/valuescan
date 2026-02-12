from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd


@dataclass
class BaselineModel:
    last_value: float = 0.0

    def fit(self, y: pd.Series) -> "BaselineModel":
        self.last_value = float(y.iloc[-1])
        return self

    def predict(self, steps: int) -> np.ndarray:
        return np.full(steps, self.last_value, dtype=float)


@dataclass
class LinearRegressionModel:
    coefficients: np.ndarray | None = None
    intercept: float = 0.0
    feature_names: List[str] | None = None

    def fit(self, x: pd.DataFrame, y: pd.Series) -> "LinearRegressionModel":
        self.feature_names = list(x.columns)
        x_mat = x.to_numpy(dtype=float)
        y_vec = y.to_numpy(dtype=float)
        coef, *_ = np.linalg.lstsq(x_mat, y_vec, rcond=None)
        self.coefficients = coef
        self.intercept = 0.0
        return self

    def predict(self, x: pd.DataFrame) -> np.ndarray:
        if self.coefficients is None:
            raise RuntimeError("Model not fitted")
        return x.to_numpy(dtype=float) @ self.coefficients + self.intercept

    def explain(self) -> Dict[str, Any]:
        if self.coefficients is None or not self.feature_names:
            return {"coefficients": []}
        pairs = []
        for name, value in zip(self.feature_names, self.coefficients):
            pairs.append({"feature": name, "coefficient": round(float(value), 6)})
        pairs.sort(key=lambda x: abs(x["coefficient"]), reverse=True)
        return {"coefficients": pairs}


def _block_bootstrap_paths(
    residuals: np.ndarray,
    horizon: int,
    n_bootstrap: int,
    block_size: int,
    rng: np.random.Generator,
) -> np.ndarray:
    if residuals.size == 0:
        return np.zeros((n_bootstrap, horizon), dtype=float)
    block = max(1, min(block_size, residuals.size))
    starts = np.arange(0, max(1, residuals.size - block + 1))
    out = np.zeros((n_bootstrap, horizon), dtype=float)
    for i in range(n_bootstrap):
        pos = 0
        while pos < horizon:
            start = int(rng.choice(starts))
            chunk = residuals[start : start + block]
            take = min(len(chunk), horizon - pos)
            out[i, pos : pos + take] = chunk[:take]
            pos += take
    return out


def forecast_with_intervals(
    model: LinearRegressionModel,
    history: pd.DataFrame,
    feature_cols: List[str],
    horizon: int,
    seed: int,
    n_bootstrap: int = 200,
    residuals: np.ndarray | None = None,
    block_size: int = 5,
) -> Tuple[List[float], List[float], List[float]]:
    if history.empty:
        raise ValueError("insufficient history after feature engineering")
    rng = np.random.default_rng(seed)
    x_last = history[feature_cols].iloc[-1].copy()
    preds: List[float] = []
    paths = np.zeros((n_bootstrap, horizon), dtype=float)

    if residuals is None:
        hist_pred = model.predict(history[feature_cols])
        residuals = history["revenue"].to_numpy(dtype=float) - hist_pred
    residual_arr = np.asarray(residuals, dtype=float)
    noise_paths = _block_bootstrap_paths(residual_arr, horizon, n_bootstrap, block_size, rng)

    for step in range(horizon):
        x_now = pd.DataFrame([x_last])
        pred = float(model.predict(x_now)[0])
        preds.append(pred)
        paths[:, step] = pred + noise_paths[:, step]

        x_last["lag_revenue_7"] = x_last.get("lag_revenue_1", pred)
        x_last["lag_revenue_1"] = pred

    lo = np.percentile(paths, 10, axis=0).round(2).tolist()
    hi = np.percentile(paths, 90, axis=0).round(2).tolist()
    return [round(v, 2) for v in preds], lo, hi
