import csv
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from telco_pipeline.generator import generate_data
from telco_pipeline.pipeline import run_pipeline


class TelcoPipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.base=Path(self.temp.name)
        self.inputs=self.base/'data'
        generate_data(self.inputs,run_date='2026-10-24',seed=42,customers=40)
        self.db=self.base/'output'/'warehouse.sqlite'
        self.output=self.base/'output'

    def tearDown(self):self.temp.cleanup()

    def test_end_to_end_and_quality_quarantine(self):
        result=run_pipeline(self.inputs,self.db,self.output)
        self.assertEqual(result['status'],'SUCCESS')
        self.assertEqual(result['data_warehouse']['dim_customer'],40)
        self.assertEqual(result['data_quality']['invalid_distinct_raw_records'],4)
        self.assertEqual(result['features']['rows'],40)
        self.assertEqual(result['data_quality']['foreign_key_check'],'PASS')
        self.assertGreater(result['ingestion']['simulated_microbatch_windows_and_batch_jobs'],3)
        self.assertTrue((self.output/'customer_features.csv').exists())

    def test_idempotency_and_repeatability(self):
        first=run_pipeline(self.inputs,self.db,self.output)
        second=run_pipeline(self.inputs,self.db,self.output)
        self.assertEqual(first['data_warehouse'],second['data_warehouse'])
        self.assertEqual(first['raw_unique_rows'],second['raw_unique_rows'])
        self.assertEqual(first['business_indicators'],second['business_indicators'])
        self.assertEqual(second['ingestion']['inserted_raw'],0)
        self.assertEqual(second['pipeline_success_rate_pct'],100.0)

    def test_features_have_cutoff_and_no_labels(self):
        run_pipeline(self.inputs,self.db,self.output)
        with (self.output/'customer_features.csv').open(newline='') as fp:
            rows=list(csv.DictReader(fp))
        self.assertTrue(all(x['as_of_date']=='2026-10-24' for x in rows))
        self.assertNotIn('churn_label',rows[0])
        self.assertTrue(all(int(x['tenure_days']) >=0 for x in rows))
        self.assertTrue(all(int(x['topup_applicable'])+int(x['bill_applicable'])==1 for x in rows))
        self.assertTrue(all(int(x['bill_outstanding_idr']) >=0 for x in rows))

    def test_late_arriving_event_updates_correct_daily_fact(self):
        first=run_pipeline(self.inputs,self.db,self.output)
        before=first['business_indicators']['total_usage_mb']
        usage_file=self.inputs/'app_usage.csv'
        with usage_file.open('a',newline='',encoding='utf-8') as fp:
            writer=csv.writer(fp)
            # Event arrives only in second replay; event-time belongs to an earlier day.
            writer.writerow(['U_LATE_TEST','SYN00001','2026-10-20T10:15:00','123.0','2','VIDEO'])
        second=run_pipeline(self.inputs,self.db,self.output)
        self.assertAlmostEqual(second['business_indicators']['total_usage_mb'],before+123.0,places=2)
        self.assertEqual(second['ingestion']['inserted_raw'],1)

    def test_failure_is_recorded(self):
        (self.inputs/'customers.csv').unlink()
        with self.assertRaises(RuntimeError):
            run_pipeline(self.inputs,self.db,self.output)
        con=sqlite3.connect(self.db)
        try:
            self.assertEqual(con.execute('SELECT status FROM pipeline_runs').fetchone()[0],'FAILED')
            self.assertEqual(con.execute('SELECT code FROM alerts').fetchone()[0],'PIPELINE_FAILURE')
        finally: con.close()

    def test_generator_is_deterministic(self):
        other=self.base/'other'
        generate_data(other,run_date='2026-10-24',seed=42,customers=40)
        for file in ('customers.csv','prepaid_transactions.csv','postpaid_billing.csv','app_usage.csv'):
            self.assertEqual((self.inputs/file).read_bytes(),(other/file).read_bytes())


if __name__=='__main__':unittest.main()
