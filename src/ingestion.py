from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd
import yaml


@dataclass(frozen=True)
class FieldSpec:
    name: str
    dtype: str
    required: bool
    unit: str
    missing: str


def load_config(config_path: str | Path) -> Dict[str, Any]:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_dataset(path: str | Path) -> pd.DataFrame:
    p = Path(path)
    if p.suffix.lower() == ".csv":
        return pd.read_csv(p)
    if p.suffix.lower() in {".parquet", ".pq"}:
        return pd.read_parquet(p)
    raise ValueError(f"Unsupported input format: {p.suffix}")


def _build_specs(config: Dict[str, Any]) -> List[FieldSpec]:
    fields = config.get("schema", {}).get("fields", [])
    specs: List[FieldSpec] = []
    for item in fields:
        specs.append(
            FieldSpec(
                name=item["name"],
                dtype=item.get("type", "str"),
                required=bool(item.get("required", False)),
                unit=item.get("unit", ""),
                missing=item.get("missing", "allow"),
            )
        )
    return specs


def _validate_dtype(series: pd.Series, expected: str) -> bool:
    if expected in {"float", "int"}:
        return pd.api.types.is_numeric_dtype(series)
    if expected == "date":
        dtype = series.dtype
        return isinstance(dtype, pd.DatetimeTZDtype) or pd.api.types.is_datetime64_any_dtype(series)
    if expected == "str":
        sample = series.dropna()
        if sample.empty:
            return True
        return bool(sample.map(lambda x: isinstance(x, str)).all())
    return True


def _apply_missing_strategy(df: pd.DataFrame, spec: FieldSpec) -> pd.DataFrame:
    if spec.name not in df.columns:
        return df
    if spec.missing == "zero" and spec.dtype in {"float", "int"}:
        df[spec.name] = df[spec.name].fillna(0)
    elif spec.missing == "drop":
        df = df[df[spec.name].notna()]
    return df


def validate_and_standardize(df: pd.DataFrame, config: Dict[str, Any]) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    specs = _build_specs(config)
    metadata = config.get("schema", {})
    report: Dict[str, Any] = {
        "row_count_before": int(len(df)),
        "issues": [],
        "applied": [],
    }

    for spec in specs:
        if spec.required and spec.name not in df.columns:
            raise ValueError(f"Missing required field: {spec.name}")

    for spec in specs:
        if spec.name not in df.columns:
            continue
        if spec.dtype == "date":
            df[spec.name] = pd.to_datetime(df[spec.name], utc=True, errors="coerce")
        elif spec.dtype == "float":
            df[spec.name] = pd.to_numeric(df[spec.name], errors="coerce")
        elif spec.dtype == "int":
            df[spec.name] = pd.to_numeric(df[spec.name], errors="coerce")

        if not _validate_dtype(df[spec.name], spec.dtype):
            report["issues"].append(f"dtype mismatch on {spec.name}: expected {spec.dtype}")
        df = _apply_missing_strategy(df, spec)
        report["applied"].append({"field": spec.name, "missing": spec.missing, "unit": spec.unit})

    # Consistency checks: currency, timezone, grain, primary key
    expected_currency = metadata.get("currency", "USD")
    expected_timezone = metadata.get("timezone", "UTC")
    grain = metadata.get("grain", "day")
    primary_key = metadata.get("primary_key", [])

    if "currency" in df.columns:
        bad_currency = df[df["currency"] != expected_currency]
        if not bad_currency.empty:
            report["issues"].append("currency mismatch rows found")

    if "date" in df.columns and str(df["date"].dtype).find("datetime") == -1:
        report["issues"].append("date is not datetime after normalization")
    if "date" in df.columns and isinstance(df["date"].dtype, pd.DatetimeTZDtype):
        tz_name = str(df["date"].dt.tz)
        if expected_timezone.upper() == "UTC" and tz_name.upper() != "UTC":
            report["issues"].append(f"timezone mismatch: expected UTC got {tz_name}")
    if "date" in df.columns:
        future_rows = int((df["date"] > pd.Timestamp.utcnow()).sum())
        if future_rows > 0:
            report["issues"].append(f"future-dated rows found: {future_rows}")

    # Semantic range checks to catch impossible values.
    for name in ["visitors", "signups", "activated", "paid_customers", "new_customers", "retained_d1", "retained_d7", "retained_d30"]:
        if name in df.columns and (df[name] < 0).any():
            report["issues"].append(f"negative values in {name}")

    if "price" in df.columns and (df["price"] <= 0).any():
        report["issues"].append("non-positive price found")

    if "retained_d1" in df.columns and "new_customers" in df.columns:
        bad = int((df["retained_d1"] > df["new_customers"]).sum())
        if bad > 0:
            report["issues"].append(f"retained_d1 exceeds new_customers rows: {bad}")
    if "retained_d7" in df.columns and "new_customers" in df.columns:
        bad = int((df["retained_d7"] > df["new_customers"]).sum())
        if bad > 0:
            report["issues"].append(f"retained_d7 exceeds new_customers rows: {bad}")
    if "retained_d30" in df.columns and "new_customers" in df.columns:
        bad = int((df["retained_d30"] > df["new_customers"]).sum())
        if bad > 0:
            report["issues"].append(f"retained_d30 exceeds new_customers rows: {bad}")

    if primary_key:
        duplicated = df.duplicated(primary_key).sum()
        if duplicated > 0:
            report["issues"].append(f"duplicate primary keys: {duplicated}")

    report["metadata"] = {
        "currency": expected_currency,
        "timezone": expected_timezone,
        "grain": grain,
        "primary_key": primary_key,
    }
    report["row_count_after"] = int(len(df))
    return df.reset_index(drop=True), report
