
import csv
import tempfile
import unittest
from pathlib import Path

from telco_pipeline.churn_model import FEATURE_COLUMNS, run_model


class ChurnModelTests(unittest.TestCase):
    def test_model_training_and_outputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            features_path = root / "customer_features.csv"
            output_dir = root / "outputs"

            # Data simulasi khusus untuk menguji alur training.
            rows = []
            for i in range(80):
                row = {
                    "as_of_date": "2026-10-24",
                    "customer_id": f"SYN{i + 1:05d}",
                    "is_postpaid": i % 2,
                    "tenure_days": 30 + i * 10,
                    "usage_mb_7d": 500 + (i % 20) * 150,
                    "usage_mb_previous_7d": 1000 + (i % 15) * 200,
                    "usage_trend_pct": -90 + (i * 17) % 150,
                    "has_previous_usage": 0 if i % 9 == 0 else 1,
                    "sessions_7d": i % 50,
                    "days_since_last_usage": (i * 7) % 31,
                    "topup_amount_30d": 10000 + i * 10000,
                    "topup_count_30d": i % 12,
                    "topup_applicable": 1,
                    "bill_paid_ratio": (i % 11) / 10,
                    "bill_outstanding_idr": (i * 17000) % 600000,
                    "bill_applicable": i % 2,
                }
                rows.append(row)

            with features_path.open(
                "w", newline="", encoding="utf-8"
            ) as file:
                writer = csv.DictWriter(
                    file,
                    fieldnames=[
                        "as_of_date",
                        "customer_id",
                        *FEATURE_COLUMNS,
                    ],
                )
                writer.writeheader()
                writer.writerows(rows)

            result = run_model(features_path, output_dir, seed=42)

            # Pastikan evaluasi dan kedua file output tersedia.
            self.assertEqual(result["dataset_rows"], 80)
            self.assertEqual(result["train_rows"], 60)
            self.assertEqual(result["test_rows"], 20)

            self.assertTrue(
                (output_dir / "churn_predictions.csv").exists()
            )
            self.assertTrue(
                (output_dir / "model_metrics.json").exists()
            )

            with (output_dir / "churn_predictions.csv").open(
                newline="", encoding="utf-8"
            ) as file:
                predictions = list(csv.DictReader(file))

            self.assertEqual(len(predictions), 80)
            self.assertIn(
                "churn_probability", predictions[0]
            )

            metrics = result["metrics"]
            for name in (
                "accuracy",
                "precision",
                "recall",
                "f1_score",
                "roc_auc",
            ):
                self.assertGreaterEqual(metrics[name], 0)
                self.assertLessEqual(metrics[name], 1)


if __name__ == "__main__":
    unittest.main()
