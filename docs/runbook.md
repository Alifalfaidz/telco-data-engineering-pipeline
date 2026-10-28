# Operations runbook (local demonstration)

## Standard procedure

1. Run `python run_pipeline.py generate --run-date 2026-10-24` to prepare deterministic synthetic sources.
2. Run `python run_pipeline.py run --run-date 2026-10-24`.
3. Check `outputs/run_report.json`: `status`, source row counts, data quality, fact counts, warnings, and simulated freshness.
4. Inspect SQLite tables `pipeline_runs`, `data_quality_issues`, and `alerts` if needed.
5. Run `python -m unittest discover -s tests -v` before sharing or changing the implementation.

## Triage / incident handling

| Signal | Potential cause | Initial action |
|---|---|---|
| Pipeline FAILED | Missing CSV, invalid schema, runtime exception | Inspect terminal traceback and `pipeline_runs.error_message`; check input files and rerun after fix |
| Quarantined rows WARNING | Negative MB, unknown or empty customer ID, invalid date | Inspect `data_quality_issues`; validate source contract; do not remove validation to silence alert |
| Freshness WARNING | Last valid event older than 120 minutes relative to synthetic cutoff | Check whether the input CSV contains events for the expected simulated period; no claim of true source latency |
| Quality threshold CRITICAL | >1% invalid distinct raw records | Stop downstream use until source quality is reviewed; adjust threshold only with approval |
| Counts change on replay | New files or code altered, or duplicate handling defect | Recreate a clean demo DB; compare source checksums, constraints and test suite |

## Change and recovery discipline

- Make changes on a branch, test with a fresh temporary database, review SQL, and verify metric definitions.
- Do not overwrite a live database or delete unknown `*.sqlite` files to fix a demo.
- To recreate **only this generated local demo**, remove `outputs/telco_dwh.sqlite` and run once with the same synthetic source files. Historical run logs will restart.
- Record change description, expected result, rollback version, and monitoring follow-up.

## Limitations

Operational alerting is **written to local SQLite and JSON**, not sent to Slack/email/PagerDuty. The replay of 15-minute buckets is not a continuous consumer; the code runs once when invoked. For production, deploy a real scheduler/orchestrator, retries with backoff, incremental affected-partition recomputation, durable dead-letter storage, access control, encrypted sensitive data handling, and agreed SLAs.
