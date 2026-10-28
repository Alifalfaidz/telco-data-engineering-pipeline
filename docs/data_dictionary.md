# Data dictionary and grain

All identifiers are synthetic and contain no personal information.

| Layer | Table / file | Grain | Business meaning |
|---|---|---|---|
| Input | `customers.csv` | one customer | Synthetic identity, plan, region, join date, segment |
| Input | `prepaid_transactions.csv` | one top-up transaction | `amount_idr` and status; not automatically revenue |
| Input | `postpaid_billing.csv` | one invoice | Due/paid amounts and dates; not revenue recognition |
| Input | `app_usage.csv` | one application usage event | Data usage in MB, sessions, and category |
| Raw | `raw_events` | unique `(source, record_key)` | Original source payload in JSON text; replay-safe |
| DWH | `dim_customer` | one synthetic customer | Conformed ID and plan/region/segment; Type 1 in demo |
| DWH | `dim_date` | one calendar day | `YYYYMMDD` integer surrogate date key |
| DWH | `dim_app` | one app category | Category grouping |
| DWH | `fact_prepaid` | one top-up transaction | Transaction date, amount, status |
| DWH | `fact_postpaid` | one invoice | Bill month, amount due/paid, payment date |
| DWH | `fact_usage_daily` | one customer × day × app | `mb_used` / `sessions` / event count (daily sum) |
| Monitoring | `data_quality_issues` | unique source row × issue | Quarantined input reason |
| Monitoring | `pipeline_runs` | one invocation | Result, counts, duration, status |
| Monitoring | `alerts` | one alert / invocation | Quality, freshness, failure notices |
| Feature | `customer_features.csv` | one customer × as-of date | Model input without churn ground-truth labels |

**Important distinction:** target design mentions Slowly Changing Dimension Type 2 and selective partition upserts. The **implemented** SQLite customer dimension updates values in-place (Type 1), and usage aggregation recomputes from valid raw history. Those are deliberate prototype simplifications; do not claim SCD2 or production-scale incremental loading is implemented.

## Feature field definitions

| Field | Definition at cutoff date | Notes |
|---|---|---|
| `as_of_date` | Simulation observation date | Date of prediction, not a feature |
| `customer_id` | Synthetic stable ID | Join/troubleshooting key; exclude from ML features |
| `is_postpaid` | 1 if postpaid; otherwise 0 | Encoded plan |
| `tenure_days` | Days since join_date at cutoff | Must be >= 0 |
| `usage_mb_7d` | Usage MB in last 7 calendar days including cutoff | Only valid events |
| `usage_mb_previous_7d` | Usage MB in the preceding 7 days | Days -13 through -7 |
| `usage_trend_pct` | 100 × (last7 − previous7)/previous7 | Set 0 when denominator absent; use flag |
| `has_previous_usage` | 1 if previous7 > 0 | Missing denominator flag |
| `sessions_7d` | Session count over latest 7 days | App usage only |
| `days_since_last_usage` | Days since last valid usage event, max 30 if none in window | Only current 30-day usage available |
| `topup_amount_30d` | Sum completed prepaid top-ups over 30 days | Zero for postpaid + applicability flag |
| `topup_count_30d` | Count completed prepaid top-ups over 30 days | Zero for postpaid + applicability flag |
| `topup_applicable` | 1 for prepaid, otherwise 0 | Distinguishes not-applicable from zero |
| `bill_paid_ratio` | paid amount / billed amount in current billing month | Zero for prepaid + applicability flag |
| `bill_outstanding_idr` | bill due − bill paid in current billing month | Zero for prepaid + applicability flag |
| `bill_applicable` | 1 for postpaid, otherwise 0 | Distinguishes not-applicable from zero |

**Not yet implemented:** label creation, training/validation split, feature normalization, predictive model fitting, drift monitoring, real retention outcomes, SCD2 history, streaming transport, real production alert routing.
