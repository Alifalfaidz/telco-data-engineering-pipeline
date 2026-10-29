# Telco Data Engineering Pipeline

This is a Data Engineering project I built as part of my Week 4 practice. The project focuses on how customer, prepaid transaction, postpaid billing, and app usage data can be processed and combined into one database.

I also added a simple churn prediction demo using Logistic Regression to explore how the processed customer data can be used for machine learning.

All data used in this project is dummy data created for learning and testing purposes. It does not represent real Telkomsel customer data or production infrastructure.

## Project Overview

The main goal of this project is to build a data pipeline from the source files to a dataset that can be used for analysis and a simple churn model.

The pipeline covers several steps:

1. Generate dummy data for customers, prepaid transactions, postpaid billing, and app usage.
2. Read CSV files and load the records into a raw data layer in SQLite.
3. Check data quality, including duplicate records, invalid values, and inconsistent data.
4. Organize the cleaned data into dimension and fact tables.
5. Prepare customer features for further analysis.
6. Train and evaluate a simple Logistic Regression model using dummy churn labels.
7. Save pipeline reports, model metrics, and customer predictions.

## Architecture

![End-to-end pipeline](docs/end_to_end_flow.png)

The pipeline starts with CSV files, processes the data, and stores the results in a local SQLite database. Customer features are then prepared for the churn prediction demo.

The architecture diagram represents the overall workflow. Some components, such as scheduled jobs and live streaming, are not implemented in this project.

## Tech Stack

- **Python** for data generation, ingestion, processing, and model training.
- **SQLite and SQL** for data storage and warehouse tables.
- **Pandas, NumPy, and scikit-learn** for the machine learning demo and its dependencies.
- **Python unittest** for automated testing.
- **CSV and JSON** for input files, predictions, metrics, and pipeline reports.

## Project Structure

```text
telco-data-engineering-pipeline/
├── data/
│   └── synthetic/
├── docs/
│   ├── end_to_end_flow.png
│   ├── dwh_model.png
│   ├── data_dictionary.md
│   └── runbook.md
├── outputs/
│   ├── sample/
│   ├── customer_features.csv
│   ├── churn_predictions.csv
│   ├── model_metrics.json
│   ├── run_report.json
│   └── telco_dwh.sqlite
├── sql/
│   ├── schema.sql
│   └── sample_queries.sql
├── telco_pipeline/
│   ├── __init__.py
│   ├── generator.py
│   ├── pipeline.py
│   └── churn_model.py
├── tests/
│   ├── test_pipeline.py
│   └── test_churn_model.py
├── requirements.txt
├── run_pipeline.py
└── README.md
```

## How to Run the Project

Make sure Python is installed. The following commands can be run from the repository folder.

### 1. Set up the environment

Create a virtual environment and activate it:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the required package:

```bash
python -m pip install -r requirements.txt
```

### 2. Generate dummy data

```bash
python run_pipeline.py generate --run-date 2026-10-24
```

This command generates the input CSV files using a fixed seed so the example data can be reproduced.

### 3. Run the data pipeline

```bash
python run_pipeline.py run --run-date 2026-10-24
```

The pipeline processes the input data and generates the SQLite database, customer features, and monitoring report.

### 4. Run the churn model

```bash
python -m telco_pipeline.churn_model
```

The model reads the prepared customer data, trains a Logistic Regression classifier, and saves the prediction results and evaluation metrics.

### 5. Run the automated tests

```bash
python -m unittest discover -s tests -v
```

The tests cover the data pipeline, data quality checks, repeated ingestion, late-arriving usage records, and model outputs.

## Data Pipeline Results

During my local testing, the pipeline processed 12,138 input records from the dummy CSV files.

| Measurement | Result |
|---|---:|
| Input records processed | 12,138 |
| Unique records stored in the raw layer | 12,136 |
| Invalid records identified | 4 |
| Customer dimension records | 240 |
| Prepaid transaction records | 1,105 |
| Postpaid billing records | 84 |
| Daily app usage records | 9,116 |
| Customer feature rows | 240 |
| Foreign key checks | PASS |

The two duplicate records were ignored, while four invalid records were identified and recorded for data-quality handling. The pipeline continued processing valid records.

The pipeline also supports repeated runs with the same input without inserting duplicate raw records.

## Churn Model Results

I added a Logistic Regression model to demonstrate how customer features can be used for a classification task.

The model was tested using 240 dummy customer records, divided into 180 training records and 60 testing records.

| Metric | Result |
|---|---:|
| Accuracy | 96.67% |
| Precision | 90.00% |
| Recall | 100.00% |
| F1-score | 94.74% |
| ROC-AUC | 1.00 |

**Important note:** The churn labels used in this demo are generated from a predefined risk score. They are not actual customer churn outcomes. Therefore, these metrics show how the model performs against the generated labels, not how accurately it would predict churn in a real telecom environment.

The results should not be used to make decisions about real customers.

## Monitoring and Data Quality

The project includes several checks to make the pipeline easier to inspect:

- Duplicate records are handled during ingestion.
- Invalid source records are recorded for further review.
- Foreign key relationships are checked.
- Pipeline execution status and data-quality results are saved in monitoring reports.
- Model evaluation metrics and predictions are saved as output files.

The project also includes a runbook and sample SQL queries for further inspection.

## Project Limitations

This project is a local learning project, not a production telecom system.

- All customer and transaction records are dummy data.
- The 15-minute ingestion windows are simulated within a Python run.
- There is no live streaming service, message broker, cloud deployment, or job scheduler.
- The churn labels are generated for demonstration rather than collected from observed customer outcomes.
- The model has not been validated on real customer data or through temporal evaluation.

A future improvement would be to use approved historical data, define churn labels based on actual business outcomes, improve the feature engineering process, and evaluate the model on a separate time period.

## Conclusion

Through this project, I practiced building a data pipeline from CSV ingestion and data-quality checks to a SQLite Data Warehouse and customer feature preparation.

I also explored how the prepared data could be used in a simple churn classification model. This project helped me understand the relationship between Data Engineering and machine learning, especially the importance of data quality before the data is used for modeling.

For more details, see the architecture diagrams, [data dictionary](docs/data_dictionary.md), [sample SQL queries](sql/sample_queries.sql), and [runbook](docs/runbook.md).
