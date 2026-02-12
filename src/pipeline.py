from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, List

try:
    from src.cleaning import apply_seed, build_features, prevent_leakage
    from src.evaluation import rolling_backtest
    from src.ingestion import load_config, load_dataset, validate_and_standardize
    from src.metrics import (
        cohort_retention,
        compute_kpis,
        funnel_breakdown,
        ltv_cac_table,
        pricing_elasticity,
        scenario_sensitivity,
    )
    from src.models import LinearRegressionModel, forecast_with_intervals
    from src.reporting import build_results_summary, write_json, write_markdown_report
except ModuleNotFoundError:
    from cleaning import apply_seed, build_features, prevent_leakage
    from evaluation import rolling_backtest
    from ingestion import load_config, load_dataset, validate_and_standardize
    from metrics import (
        cohort_retention,
        compute_kpis,
        funnel_breakdown,
        ltv_cac_table,
        pricing_elasticity,
        scenario_sensitivity,
    )
    from models import LinearRegressionModel, forecast_with_intervals
    from reporting import build_results_summary, write_json, write_markdown_report


def _recommended_levers(kpis: Dict[str, Any], funnel: List[Dict[str, Any]], elasticity: Dict[str, Any]) -> List[Dict[str, Any]]:
    levers: List[Dict[str, Any]] = []
    if kpis.get("ltv_cac_ratio") is not None and kpis["ltv_cac_ratio"] < 3:
        levers.append(
            {
                "lever": "reduce_cac",
                "reason": "ltv_cac_ratio below 3",
                "quant_basis": {"ltv_cac_ratio": kpis["ltv_cac_ratio"]},
            }
        )

    if funnel:
        worst = sorted(funnel, key=lambda x: min(x["rates"].values()))[0]
        levers.append(
            {
                "lever": "improve_funnel_stage",
                "reason": f"bottleneck at {worst['bottleneck']} in group {worst['group']}",
                "quant_basis": worst["rates"],
            }
        )

    if elasticity.get("status") == "ok" and elasticity.get("elasticity", 0) < -1.0:
        levers.append(
            {
                "lever": "optimize_pricing",
                "reason": "demand appears elastic",
                "quant_basis": elasticity,
            }
        )

    return levers


def run_pipeline(input_path: str, config_path: str, output_dir: str) -> Dict[str, Any]:
    cfg = load_config(config_path)
    seed = int(cfg.get("runtime", {}).get("random_seed", 42))
    apply_seed(seed)

    raw = load_dataset(input_path)
    standardized, validation_report = validate_and_standardize(raw, cfg)
    clean = prevent_leakage(standardized)
    features_df, feature_cols, target_col = build_features(clean)
    if features_df.empty:
        raise ValueError("insufficient rows after feature engineering; provide more history")

    min_train_size = int(cfg.get("modeling", {}).get("min_train_size", 30))
    test_window = int(cfg.get("modeling", {}).get("test_window", 7))
    embargo = int(cfg.get("modeling", {}).get("embargo", 1))
    min_required_rows = min_train_size + test_window + embargo
    if len(features_df) < min_required_rows:
        raise ValueError(
            f"insufficient rows for backtest: need >= {min_required_rows}, got {len(features_df)}"
        )

    eval_report = rolling_backtest(
        features_df,
        feature_cols=feature_cols,
        target_col=target_col,
        min_train_size=min_train_size,
        test_window=test_window,
        seasonal_period=int(cfg.get("modeling", {}).get("seasonal_period", 7)),
        embargo=embargo,
    )

    model = LinearRegressionModel().fit(features_df[feature_cols], features_df[target_col])
    in_sample_pred = model.predict(features_df[feature_cols])
    residuals = features_df[target_col].to_numpy() - in_sample_pred
    horizon = int(cfg.get("modeling", {}).get("forecast_horizon", 14))
    forecast_values, forecast_lo, forecast_hi = forecast_with_intervals(
        model,
        history=features_df,
        feature_cols=feature_cols,
        horizon=horizon,
        seed=seed,
        n_bootstrap=int(cfg.get("modeling", {}).get("n_bootstrap", 200)),
        residuals=residuals,
        block_size=int(cfg.get("modeling", {}).get("bootstrap_block_size", 5)),
    )

    kpis = compute_kpis(features_df)
    funnel = funnel_breakdown(features_df)
    retention = cohort_retention(features_df)
    unit_econ = ltv_cac_table(features_df)
    elasticity = pricing_elasticity(features_df)
    sensitivity = scenario_sensitivity(kpis, cfg.get("sensitivity", {}).get("deltas", {}))

    key_drivers = model.explain().get("coefficients", [])[:5]
    risks_assumptions = [
        "Forecast assumes stable channel mix and no structural break.",
        "Attribution window fixed at 30 days in current run.",
        "Potential survivor bias if churned users are under-recorded.",
        "Competitor pricing sampled daily; intraday moves are not modeled.",
    ]
    recommended_levers = _recommended_levers(kpis, funnel, elasticity)

    north_star = {
        "revenue": kpis["revenue"],
        "net_profit": kpis["net_profit"],
        "ltv_cac_ratio": kpis["ltv_cac_ratio"],
        "retention_d30_mean": round(sum(x["d30"] for x in retention) / max(len(retention), 1), 4),
    }

    summary = build_results_summary(
        north_star_metrics=north_star,
        funnel_breakdown=funnel,
        ltv_cac_table=unit_econ,
        forecast_values=forecast_values,
        forecast_lo=forecast_lo,
        forecast_hi=forecast_hi,
        key_drivers=key_drivers,
        risks_assumptions=risks_assumptions,
        recommended_levers=recommended_levers,
    )
    summary["retention"] = retention
    summary["pricing_elasticity"] = elasticity
    summary["sensitivity"] = sensitivity

    backfill_list = [
        "User-level event table for true cohort retention by signup date.",
        "Multi-touch attribution log with impression/click timestamps.",
        "Discount and promotion flags for causal pricing effect separation.",
    ]

    out_dir = Path(output_dir)
    write_json(summary, out_dir / "results_summary.json")
    write_markdown_report(
        out_dir / "report.md",
        summary=summary,
        validation_report=validation_report,
        eval_report=eval_report,
        data_limitations=backfill_list,
    )

    write_json(
        {
            "validation": validation_report,
            "evaluation": eval_report,
            "config": cfg,
        },
        out_dir / "run_metadata.json",
    )
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run enterprise market analytics pipeline")
    parser.add_argument("--input", required=True, help="Input dataset path (csv/parquet)")
    parser.add_argument("--config", default="config/market_analysis_config.yaml", help="Config YAML path")
    parser.add_argument("--output", default="data/market_analysis_output", help="Output directory")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_pipeline(args.input, args.config, args.output)
