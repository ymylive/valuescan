from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd


def compute_kpis(df: pd.DataFrame) -> Dict[str, float]:
    total_revenue = float(df["revenue"].sum())
    total_gmv = float(df["gmv"].sum())
    gross_profit = float((df["revenue"] - df["cogs"]).sum())
    net_profit = float((df["revenue"] - df["cogs"] - df["operating_cost"]).sum())
    total_new_customers = float(df["new_customers"].sum())
    total_spend = float(df["marketing_spend"].sum())
    cac = total_spend / total_new_customers if total_new_customers > 0 else float("nan")

    avg_revenue_per_customer = total_revenue / max(total_new_customers, 1.0)
    gross_margin = gross_profit / max(total_revenue, 1.0)
    mean_retention_d30 = float((df["retained_d30"] / df["new_customers"].replace(0, np.nan)).fillna(0).mean())
    monthly_churn = max(1.0 - mean_retention_d30, 0.05)
    expected_life_months = 1.0 / monthly_churn
    ltv = avg_revenue_per_customer * gross_margin * expected_life_months

    return {
        "revenue": round(total_revenue, 2),
        "gmv": round(total_gmv, 2),
        "gross_profit": round(gross_profit, 2),
        "net_profit": round(net_profit, 2),
        "cac": round(cac, 4) if np.isfinite(cac) else None,
        "ltv": round(float(ltv), 4),
        "ltv_cac_ratio": round(float(ltv / cac), 4) if np.isfinite(cac) and cac > 0 else None,
    }


def funnel_breakdown(df: pd.DataFrame, group_col: str = "channel") -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    grouped = df.groupby(group_col, dropna=False)
    for key, part in grouped:
        visitors = float(part["visitors"].sum())
        signups = float(part["signups"].sum())
        activated = float(part["activated"].sum())
        paid = float(part["paid_customers"].sum())
        s1 = signups / visitors if visitors > 0 else 0.0
        s2 = activated / signups if signups > 0 else 0.0
        s3 = paid / activated if activated > 0 else 0.0
        stages = {
            "visitor_to_signup": s1,
            "signup_to_activated": s2,
            "activated_to_paid": s3,
        }
        bottleneck = min(stages, key=stages.get)
        out.append(
            {
                "group": str(key),
                "visitors": int(visitors),
                "signups": int(signups),
                "activated": int(activated),
                "paid_customers": int(paid),
                "rates": {k: round(v, 4) for k, v in stages.items()},
                "bottleneck": bottleneck,
            }
        )
    return out


def cohort_retention(df: pd.DataFrame, group_col: str = "channel") -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    grouped = df.groupby(group_col, dropna=False)
    for key, part in grouped:
        new_customers = part["new_customers"].replace(0, np.nan)
        d1 = float((part["retained_d1"] / new_customers).fillna(0).mean())
        d7 = float((part["retained_d7"] / new_customers).fillna(0).mean())
        d30 = float((part["retained_d30"] / new_customers).fillna(0).mean())
        out.append({"group": str(key), "d1": round(d1, 4), "d7": round(d7, 4), "d30": round(d30, 4)})
    return out


def ltv_cac_table(df: pd.DataFrame) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    grouped = df.groupby(["channel", "segment"], dropna=False)
    for (channel, segment), part in grouped:
        kpis = compute_kpis(part)
        out.append(
            {
                "channel": str(channel),
                "segment": str(segment),
                "ltv": kpis["ltv"],
                "cac": kpis["cac"],
                "ltv_cac_ratio": kpis["ltv_cac_ratio"],
            }
        )
    return out


def pricing_elasticity(df: pd.DataFrame) -> Dict[str, float]:
    clean = df[(df["price"] > 0) & (df["units_sold"] > 0)].copy()
    if len(clean) < 3:
        return {"elasticity": 0.0, "status": "insufficient_data"}
    x = np.log(clean["price"].to_numpy())
    y = np.log(clean["units_sold"].to_numpy())
    slope = float(np.polyfit(x, y, 1)[0])
    return {"elasticity": round(slope, 4), "status": "ok"}


def scenario_sensitivity(base_kpis: Dict[str, float], deltas: Dict[str, float]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    revenue = float(base_kpis.get("revenue", 0) or 0)
    net_profit = float(base_kpis.get("net_profit", 0) or 0)
    for name, delta in deltas.items():
        rows.append(
            {
                "parameter": name,
                "delta": delta,
                "revenue_impact": round(revenue * delta, 2),
                "net_profit_impact": round(net_profit * delta, 2),
            }
        )
    return rows
