from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np
import pandas as pd


def prevent_leakage(df: pd.DataFrame, date_col: str = "date") -> pd.DataFrame:
    ordered = df.sort_values(date_col).copy()
    ordered = ordered[ordered[date_col].notna()]
    return ordered.reset_index(drop=True)


def build_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str], str]:
    data = df.copy()
    data = data.sort_values("date")

    data["gross_profit"] = data["revenue"] - data["cogs"]
    data["net_profit"] = data["gross_profit"] - data["operating_cost"]
    data["conv_signup"] = np.where(data["visitors"] > 0, data["signups"] / data["visitors"], 0.0)
    data["conv_paid"] = np.where(data["activated"] > 0, data["paid_customers"] / data["activated"], 0.0)
    data["lag_revenue_1"] = data["revenue"].shift(1)
    data["lag_revenue_7"] = data["revenue"].shift(7)
    data["dow"] = data["date"].dt.dayofweek
    data["price_gap_vs_competitor"] = data["price"] - data["competitor_price"]

    data = data.dropna(subset=["lag_revenue_1", "lag_revenue_7"]).reset_index(drop=True)

    feature_cols = [
        "marketing_spend",
        "new_customers",
        "active_customers",
        "price",
        "competitor_price",
        "price_gap_vs_competitor",
        "conv_signup",
        "conv_paid",
        "lag_revenue_1",
        "lag_revenue_7",
        "dow",
    ]
    target_col = "revenue"
    return data, feature_cols, target_col


def split_train_test_by_time(df: pd.DataFrame, test_size: int) -> Tuple[pd.DataFrame, pd.DataFrame]:
    if test_size <= 0 or test_size >= len(df):
        raise ValueError("test_size must be between 1 and len(df)-1")
    return df.iloc[:-test_size].copy(), df.iloc[-test_size:].copy()


def apply_seed(seed: int) -> None:
    np.random.seed(seed)
