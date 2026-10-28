-- Example BI queries over the synthetic local Star Schema.
-- Explicitly keep prepaid top-up and postpaid billing separate;
-- their raw amounts are not identical to recognized company revenue.

-- 1) Successful prepaid top-ups by date
SELECT d.full_date, COUNT(*) AS topup_count, SUM(f.amount_idr) AS total_topup_idr
FROM fact_prepaid f
JOIN dim_date d ON d.date_key = f.date_key
WHERE f.status = 'SUCCESS'
GROUP BY d.full_date ORDER BY d.full_date;

-- 2) Postpaid billing and payments by billing month
SELECT f.billing_month, COUNT(*) AS invoice_count,
       SUM(f.amount_due_idr) AS billed_idr,
       SUM(f.paid_amount_idr) AS paid_idr
FROM fact_postpaid f
GROUP BY f.billing_month ORDER BY f.billing_month;

-- 3) Digital-app usage by category and region in the selected month
SELECT substr(d.full_date,1,7) AS month, c.region, a.app_category,
       ROUND(SUM(f.mb_used),2) AS usage_mb,
       SUM(f.sessions) AS sessions
FROM fact_usage_daily f
JOIN dim_customer c ON c.customer_key=f.customer_key
JOIN dim_date d ON d.date_key=f.date_key
JOIN dim_app a ON a.app_key=f.app_key
GROUP BY substr(d.full_date,1,7), c.region, a.app_category
ORDER BY month,c.region,a.app_category;
