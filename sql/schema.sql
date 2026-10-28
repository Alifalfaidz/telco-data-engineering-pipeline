PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS raw_events (
 source TEXT NOT NULL, record_key TEXT NOT NULL, payload_json TEXT NOT NULL,
 source_file TEXT NOT NULL, loaded_at TEXT NOT NULL,
 PRIMARY KEY (source,record_key)
);
CREATE TABLE IF NOT EXISTS dim_customer (
 customer_key INTEGER PRIMARY KEY AUTOINCREMENT,
 customer_id TEXT UNIQUE NOT NULL, plan_type TEXT NOT NULL,
 region TEXT NOT NULL, join_date TEXT NOT NULL, segment TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS dim_date (
 date_key INTEGER PRIMARY KEY, full_date TEXT UNIQUE NOT NULL,
 year INTEGER NOT NULL, month INTEGER NOT NULL, day INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS dim_app (
 app_key INTEGER PRIMARY KEY AUTOINCREMENT,
 app_category TEXT UNIQUE NOT NULL
);
CREATE TABLE IF NOT EXISTS fact_prepaid (
 transaction_id TEXT PRIMARY KEY,
 customer_key INTEGER NOT NULL REFERENCES dim_customer(customer_key),
 date_key INTEGER NOT NULL REFERENCES dim_date(date_key),
 amount_idr INTEGER NOT NULL CHECK(amount_idr >= 0),
 status TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS fact_postpaid (
 invoice_id TEXT PRIMARY KEY,
 customer_key INTEGER NOT NULL REFERENCES dim_customer(customer_key),
 date_key INTEGER NOT NULL REFERENCES dim_date(date_key),
 billing_month TEXT NOT NULL, due_date TEXT NOT NULL,
 amount_due_idr INTEGER NOT NULL CHECK(amount_due_idr >= 0),
 paid_amount_idr INTEGER NOT NULL CHECK(paid_amount_idr >= 0),
 paid_date TEXT
);
CREATE TABLE IF NOT EXISTS fact_usage_daily (
 customer_key INTEGER NOT NULL REFERENCES dim_customer(customer_key),
 date_key INTEGER NOT NULL REFERENCES dim_date(date_key),
 app_key INTEGER NOT NULL REFERENCES dim_app(app_key),
 mb_used REAL NOT NULL CHECK(mb_used >= 0), sessions INTEGER NOT NULL CHECK(sessions >= 0),
 event_count INTEGER NOT NULL,
 PRIMARY KEY (customer_key,date_key,app_key)
);
CREATE TABLE IF NOT EXISTS data_quality_issues (
 source TEXT NOT NULL, record_key TEXT NOT NULL,
 issue_type TEXT NOT NULL, issue_detail TEXT NOT NULL,
 first_seen_at TEXT NOT NULL,
 PRIMARY KEY (source,record_key,issue_type)
);
CREATE TABLE IF NOT EXISTS pipeline_runs (
 run_id TEXT PRIMARY KEY, run_date TEXT NOT NULL,
 started_at TEXT NOT NULL, finished_at TEXT NOT NULL,
 status TEXT NOT NULL, duration_ms INTEGER NOT NULL,
 input_rows INTEGER NOT NULL, inserted_raw INTEGER NOT NULL,
 duplicate_raw INTEGER NOT NULL, invalid_rows INTEGER NOT NULL,
 output_usage_rows INTEGER NOT NULL,
 error_message TEXT
);
CREATE TABLE IF NOT EXISTS alerts (
 alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
 run_id TEXT NOT NULL, level TEXT NOT NULL,
 code TEXT NOT NULL, message TEXT NOT NULL,
 UNIQUE (run_id,code)
);
CREATE INDEX IF NOT EXISTS idx_usage_date ON fact_usage_daily(date_key);
CREATE INDEX IF NOT EXISTS idx_usage_customer ON fact_usage_daily(customer_key);
CREATE INDEX IF NOT EXISTS idx_prepaid_date ON fact_prepaid(date_key);
CREATE INDEX IF NOT EXISTS idx_postpaid_date ON fact_postpaid(date_key);
