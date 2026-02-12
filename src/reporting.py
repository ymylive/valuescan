from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


def build_results_summary(
    north_star_metrics: Dict[str, Any],
    funnel_breakdown: List[Dict[str, Any]],
    ltv_cac_table: List[Dict[str, Any]],
    forecast_values: List[float],
    forecast_lo: List[float],
    forecast_hi: List[float],
    key_drivers: List[Dict[str, Any]],
    risks_assumptions: List[str],
    recommended_levers: List[Dict[str, Any]],
) -> Dict[str, Any]:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "north_star_metrics": north_star_metrics,
        "funnel_breakdown": funnel_breakdown,
        "ltv_cac_table": ltv_cac_table,
        "forecast": {
            "horizon_days": len(forecast_values),
            "point_forecast": forecast_values,
            "p10": forecast_lo,
            "p90": forecast_hi,
        },
        "key_drivers": key_drivers,
        "risks_assumptions": risks_assumptions,
        "recommended_levers": recommended_levers,
    }


def write_json(payload: Dict[str, Any], path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=True, indent=2)


def write_markdown_report(
    path: str | Path,
    summary: Dict[str, Any],
    validation_report: Dict[str, Any],
    eval_report: Dict[str, Any],
    data_limitations: List[str],
) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Market Analytics Brief",
        "",
        "## 1) Data Quality & Schema",
        f"- Rows before: {validation_report.get('row_count_before', 0)}",
        f"- Rows after: {validation_report.get('row_count_after', 0)}",
        f"- Issues: {validation_report.get('issues', [])}",
        "",
        "## 2) North Star Metrics",
    ]
    for k, v in summary["north_star_metrics"].items():
        lines.append(f"- {k}: {v}")

    lines += [
        "",
        "## 3) Forecast Validation",
        f"- Baseline RMSE/MAPE: {eval_report['baseline']['rmse']} / {eval_report['baseline']['mape']}%",
        f"- Seasonal baseline RMSE/MAPE: {eval_report['seasonal_baseline']['rmse']} / {eval_report['seasonal_baseline']['mape']}%",
        f"- Linear RMSE/MAPE: {eval_report['linear_regression']['rmse']} / {eval_report['linear_regression']['mape']}%",
        f"- Windows: {eval_report['windows']}",
        "- Explainability is predictive (not causal).",
        "",
        "## 4) Risks & Assumptions",
    ]
    for x in summary["risks_assumptions"]:
        lines.append(f"- {x}")

    lines += ["", "## 5) Data Gaps / Backfill Needed"]
    for item in data_limitations:
        lines.append(f"- {item}")

    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
