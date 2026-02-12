# Market Analytics Brief

## 1) Data Quality & Schema
- Rows before: 35
- Rows after: 35
- Issues: []

## 2) North Star Metrics
- revenue: 372920.0
- net_profit: 164930.0
- ltv_cac_ratio: 4.4988
- retention_d30_mean: 0.3018

## 3) Forecast Validation
- Baseline RMSE/MAPE: 985.7586 / 6.0062%
- Seasonal baseline RMSE/MAPE: 1790.7149 / 11.6694%
- Linear RMSE/MAPE: 97.5421 / 0.5756%
- Windows: 1
- Explainability is predictive (not causal).

## 4) Risks & Assumptions
- Forecast assumes stable channel mix and no structural break.
- Attribution window fixed at 30 days in current run.
- Potential survivor bias if churned users are under-recorded.
- Competitor pricing sampled daily; intraday moves are not modeled.

## 5) Data Gaps / Backfill Needed
- User-level event table for true cohort retention by signup date.
- Multi-touch attribution log with impression/click timestamps.
- Discount and promotion flags for causal pricing effect separation.
