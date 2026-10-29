from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


FEATURE_COLUMNS = [
    "is_postpaid",
    "tenure_days",
    "usage_mb_7d",
    "usage_mb_previous_7d",
    "usage_trend_pct",
    "has_previous_usage",
    "sessions_7d",
    "days_since_last_usage",
    "topup_amount_30d",
    "topup_count_30d",
    "topup_applicable",
    "bill_paid_ratio",
    "bill_outstanding_idr",
    "bill_applicable",
]


def load_features(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    if len(rows) < 20:
        raise ValueError("At least 20 customer rows are required.")

    for column in FEATURE_COLUMNS:
        if not rows or column not in rows[0]:
            raise ValueError(f"Missing required feature: {column}")

    return rows


def create_synthetic_labels(rows: list[dict]) -> np.ndarray:
    """Create proxy labels for a demonstration, not real churn ground truth."""
    risk_scores = []

    for row in rows:
        usage = float(row["usage_mb_7d"])
        trend = np.clip(float(row["usage_trend_pct"]), -100, 100) / 100
        inactive_days = np.clip(
            float(row["days_since_last_usage"]), 0, 30
        ) / 30
        previous_usage = float(row["has_previous_usage"])
        paid_ratio = np.clip(float(row["bill_paid_ratio"]), 0, 1)
        bill_applicable = float(row["bill_applicable"])
        outstanding = np.clip(
            float(row["bill_outstanding_idr"]) / 500000, 0, 1
        )

        risk = (
            0.25 * inactive_days
            + 0.25 * max(0, -trend)
            + 0.20 * (1 - np.clip(usage / 4000, 0, 1))
            + 0.15 * (1 - paid_ratio) * bill_applicable
            + 0.10 * outstanding
            + 0.05 * (1 - previous_usage)
        )
        risk_scores.append(risk)

    threshold = np.quantile(risk_scores, 0.70)
    labels = (np.asarray(risk_scores) >= threshold).astype(int)

    if len(np.unique(labels)) < 2:
        raise ValueError("Synthetic labels contain only one class.")

    return labels


def run_model(
    features_path: Path,
    output_dir: Path,
    seed: int = 42,
) -> dict:
    rows = load_features(features_path)

    # Customer IDs and dates are metadata, not model features.
    X = np.asarray(
        [
            [float(row[column]) for column in FEATURE_COLUMNS]
            for row in rows
        ],
        dtype=float,
    )
    y = create_synthetic_labels(rows)

    X_train, X_test, y_train, y_test, _, test_indices = train_test_split(
        X,
        y,
        np.arange(len(rows)),
        test_size=0.25,
        random_state=seed,
        stratify=y,
    )

    model = make_pipeline(
        StandardScaler(),
        LogisticRegression(
            max_iter=2000,
            class_weight="balanced",
            random_state=seed,
        ),
    )
    model.fit(X_train, y_train)

    test_predictions = model.predict(X_test)
    test_probabilities = model.predict_proba(X_test)[:, 1]

    tn, fp, fn, tp = confusion_matrix(
        y_test, test_predictions, labels=[0, 1]
    ).ravel()

    metrics = {
        "model": "Logistic Regression",
        "model_version": "synthetic-demo-0.1",
        "dataset_rows": len(rows),
        "train_rows": len(X_train),
        "test_rows": len(X_test),
        "synthetic_positive_labels": int(y.sum()),
        "label_definition": (
            "Synthetic proxy labels derived from a predefined risk score; "
            "not observed churn outcomes."
        ),
        "validation_method": (
            "Stratified random 75/25 split. This dataset contains one "
            "snapshot, so temporal validation is not possible."
        ),
        "metrics": {
            "accuracy": round(float(accuracy_score(y_test, test_predictions)), 4),
            "precision": round(
                float(precision_score(y_test, test_predictions, zero_division=0)), 4
            ),
            "recall": round(
                float(recall_score(y_test, test_predictions, zero_division=0)), 4
            ),
            "f1_score": round(
                float(f1_score(y_test, test_predictions, zero_division=0)), 4
            ),
            "roc_auc": round(float(roc_auc_score(y_test, test_probabilities)), 4),
        },
        "confusion_matrix": {
            "true_negative": int(tn),
            "false_positive": int(fp),
            "false_negative": int(fn),
            "true_positive": int(tp),
        },
        "warning": (
            "These metrics evaluate a synthetic rule, not real-world churn "
            "prediction performance."
        ),
    }

    output_dir.mkdir(parents=True, exist_ok=True)

    all_probabilities = model.predict_proba(X)[:, 1]
    all_predictions = model.predict(X)

    predictions_path = output_dir / "churn_predictions.csv"
    with predictions_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "as_of_date",
                "customer_id",
                "synthetic_churn_label",
                "predicted_churn",
                "churn_probability",
            ],
        )
        writer.writeheader()

        for i, row in enumerate(rows):
            writer.writerow({
                "as_of_date": row["as_of_date"],
                "customer_id": row["customer_id"],
                "synthetic_churn_label": int(y[i]),
                "predicted_churn": int(all_predictions[i]),
                "churn_probability": round(float(all_probabilities[i]), 4),
            })

    metrics_path = output_dir / "model_metrics.json"
    metrics_path.write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    return {
        **metrics,
        "predictions_file": str(predictions_path),
        "metrics_file": str(metrics_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train a synthetic churn-classification demo."
    )
    parser.add_argument(
        "--features", default="outputs/customer_features.csv"
    )
    parser.add_argument("--output-dir", default="outputs")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    result = run_model(
        Path(args.features),
        Path(args.output_dir),
        args.seed,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
