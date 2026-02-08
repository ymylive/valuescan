#!/usr/bin/env python3
"""
OHLCV data cleaning helpers (inspired by Freqtrade).
"""

import re
from typing import Optional

import numpy as np
import pandas as pd

from logger import logger


def _timeframe_to_pandas_freq(timeframe: str) -> Optional[str]:
    match = re.match(r"^(\\d+)([mhdwM])$", timeframe.strip())
    if not match:
        return None
    value = int(match.group(1))
    unit = match.group(2)
    if unit == "m":
        return f"{value}T"
    if unit == "h":
        return f"{value}H"
    if unit == "d":
        return f"{value}D"
    if unit == "w":
        return f"{value}W"
    if unit == "M":
        return f"{value}M"
    return None


def clean_ohlcv_dataframe(
    df: pd.DataFrame,
    timeframe: str,
    symbol: str,
    *,
    fill_missing: bool = True,
    drop_incomplete: bool = True,
) -> pd.DataFrame:
    if df is None or df.empty:
        return df

    work = df.copy()
    work["timestamp"] = pd.to_datetime(work["timestamp"], errors="coerce", utc=True)
    work = work.dropna(subset=["timestamp"])

    for col in ("open", "high", "low", "close", "volume"):
        work[col] = pd.to_numeric(work[col], errors="coerce")

    work = work.replace([np.inf, -np.inf], np.nan).dropna(
        subset=["open", "high", "low", "close", "volume"]
    )

    valid = (
        (work["volume"] >= 0)
        & (work["open"] > 0)
        & (work["high"] > 0)
        & (work["low"] > 0)
        & (work["close"] > 0)
        & (work["high"] >= work[["open", "close", "low"]].max(axis=1))
        & (work["low"] <= work[["open", "close", "high"]].min(axis=1))
    )
    work = work.loc[valid]

    if work.empty:
        return work

    work = work.sort_values("timestamp")
    work = work.groupby("timestamp", as_index=False).agg(
        {
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
        }
    )

    if drop_incomplete and len(work) > 1:
        work = work.iloc[:-1].copy()

    if fill_missing:
        freq = _timeframe_to_pandas_freq(timeframe)
        if freq:
            work = _fill_missing(work, freq, symbol, timeframe)

    return work


def _fill_missing(
    df: pd.DataFrame, freq: str, symbol: str, timeframe: str
) -> pd.DataFrame:
    ohlcv_dict = {
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }
    resampled = df.resample(freq, on="timestamp").agg(ohlcv_dict)
    resampled["close"] = resampled["close"].ffill()
    resampled = resampled.dropna(subset=["close"])
    resampled["open"] = resampled["open"].fillna(resampled["close"])
    resampled["high"] = resampled["high"].fillna(resampled["close"])
    resampled["low"] = resampled["low"].fillna(resampled["close"])
    resampled["volume"] = resampled["volume"].fillna(0)
    resampled = resampled.reset_index()

    missing = len(resampled) - len(df)
    if missing > 0:
        pct_missing = missing / len(df) if len(df) > 0 else 0.0
        msg = (
            f"Missing OHLCV filled for {symbol} {timeframe}: "
            f"before={len(df)} after={len(resampled)} pct={pct_missing:.2%}"
        )
        if pct_missing > 0.01:
            logger.info(msg)
        else:
            logger.debug(msg)

    return resampled
