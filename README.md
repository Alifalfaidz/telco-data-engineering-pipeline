# Telco Data Engineering Pipeline

<<<<<<< HEAD
A small, end-to-end Data Engineering project built with Python and SQLite.

I made this project as part of my Week 4 Data Engineering practice. The idea was to work through a common problem in a telecom company: customer, transaction, billing, and app-usage data often come from different systems, but they need to be brought together before anyone can use them for reporting or machine learning.

Here, I use **synthetic data** to build that flow locally—from generating CSV files to preparing customer features that could later be used for churn prediction.

## How it works

![End-to-end pipeline](docs/end_to_end_flow.png)

The pipeline follows a few main steps:

1. **Generate sample data** for customers, prepaid transactions, postpaid billing, and app usage.
2. **Ingest the CSV files** into a raw layer in SQLite.
3. **Check data quality**, including duplicates, invalid values, and inconsistent records. Invalid records are logged separately instead of silently entering the reporting tables.
4. **Build a Data Warehouse** using dimension and fact tables.
5. **Prepare customer features**, such as recent usage, top-up activity, and payment behavior.
6. **Record each pipeline run**, along with data-quality results and alerts.

The warehouse design is shown here:

![Data Warehouse model](docs/dwh_model.png)

## Tools used

- **Python 3.10+** for data generation, ingestion, and transformation
- **SQLite and SQL** for the raw layer, Data Warehouse, and reporting queries
- **Python `unittest`** for automated tests

Everything runs locally using Python's standard library, so no extra packages are required.

## Running the project

Open a terminal in the repository folder and run:

```bash
python3 run_pipeline.py generate --run-date 2026-10-24
python3 run_pipeline.py run --run-date 2026-10-24
python3 -m unittest discover -s tests -v
```

The commands generate the sample CSV files, run the pipeline, and execute the tests. If your computer uses `python` instead of `python3`, use that command instead.

After running the pipeline, the main outputs are:

- `outputs/telco_dwh.sqlite` — the local Data Warehouse
- `outputs/customer_features.csv` — customer-level features prepared for future ML work
- `outputs/run_report.json` — pipeline results, data-quality checks, and alerts

There are also example outputs in [`outputs/sample/`](outputs/sample/), so you can explore the results without running the project first.

## Results from my local run

I tested the pipeline using **240 synthetic customers** and the fixed date `2026-10-24`.

| What I checked | Result |
|---|---:|
| Input records processed | 12,138 |
| Unique records stored in the raw layer | 12,136 |
| Invalid records quarantined | 4 |
| Customer records in the warehouse | 240 |
| Prepaid transaction records | 1,105 |
| Postpaid billing records | 84 |
| Daily app-usage records | 9,116 |
| Customer feature rows | 240 |
| Automated tests passed | 6/6 |

I also ran the pipeline twice with the same input. On the second run, `inserted_raw` was **0**, and the warehouse row counts stayed the same. This was my way of checking **idempotency**: processing the same input again should not create duplicate records.

The run did produce a warning for four invalid usage records. That was expected—the sample dataset includes deliberately invalid examples to test the quality checks. The pipeline continued processing the valid records.

## Project files

```text
telco-data-engineering-pipeline/
├── data/synthetic/        # Generated CSV inputs
├── docs/                  # Architecture, data dictionary, and runbook
├── outputs/sample/        # Example pipeline outputs
├── sql/                   # Warehouse schema and sample queries
├── telco_pipeline/        # Data generator and pipeline logic
├── tests/                 # Automated tests
├── run_pipeline.py        # Main command-line entry point
├── requirements.txt
└── README.md
```

For more details, see the [data dictionary](docs/data_dictionary.md), [sample SQL queries](sql/sample_queries.sql), and [runbook](docs/runbook.md).

## What this project does not cover (yet)

This is a **local learning project**, not a production Telco system. All records are synthetic. The 15-minute ingestion windows are simulated within a Python run, not streamed from a live service. There is no cloud deployment, scheduler, or message broker.

The output is **AI-ready feature data**, not an AI model. I haven't trained a churn classifier in this repository, and the data doesn't include verified churn labels. That would be a separate step, along with time-based evaluation and model monitoring.

If I extend this project, my next focus would be incremental processing, automated scheduling, and a more realistic deployment setup.
=======
Hi! This is a Data Engineering project I worked on as part of my Week 4 mini project. I wanted to understand how data from different telecom services can be collected, processed, stored, and prepared for an AI model.

In this project, I use dummy data from customer information, prepaid transactions, postpaid billing, and digital app usage. The data goes through a Python pipeline before being stored in a SQLite database. I also added data quality checks, monitoring, customer feature preparation, and a simple Logistic Regression model to demonstrate churn classification.

All data in this project is dummy data created for learning and demonstration purposes. It does not contain actual Telkomsel customer data.

## Project Architecture

![End-to-end pipeline](docs/end_to_end_flow.png)

The general flow is:

**Data Sources → Ingestion → Data Quality Checks → Data Warehouse → Feature Engineering → Churn Model**

The pipeline reads CSV files, checks the data, stores records in SQLite, and prepares customer features. These features are then used by a separate Python module to demonstrate how a churn classification model can be trained and evaluated.

The project runs locally on my computer. The 15-minute ingestion windows are simulated during a single run, so this is not a live streaming system or a production telecom pipeline.

## Tools Used

- **Python** — for data processing and pipeline execution
- **SQLite and SQL** — for storing and querying data
- **scikit-learn** — for the Logistic Regression model
- **NumPy** — for numerical calculations
- **unittest** — for testing the pipeline and model

## How to Run the Project

### 1. Create a virtual environment

From the project folder, run:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install the required package

```bash
python -m pip install -r requirements.txt
```

### 3. Generate the dummy data

```bash
python run_pipeline.py generate --run-date 2026-10-24
```

This command creates the CSV files used as input for the pipeline.

### 4. Run the data pipeline

```bash
python run_pipeline.py run --run-date 2026-10-24
```

This runs the ingestion, data quality checks, data warehouse loading, feature preparation, and pipeline reporting.

Some of the outputs are:

- `outputs/telco_dwh.sqlite`
- `outputs/customer_features.csv`
- `outputs/run_report.json`

### 5. Run the churn model

```bash
python -m telco_pipeline.churn_model
```

This trains a Logistic Regression model using the customer features and dummy churn labels created for the demonstration.

The model generates:

- `outputs/churn_predictions.csv`
- `outputs/model_metrics.json`

### 6. Run the tests

```bash
python -m unittest discover -s tests -v
```

The project currently has seven automated tests: six for the data pipeline and one for the churn model.

## Data Pipeline Results

These are the results from my local run using the generated dummy data.

| Measurement | Result |
|---|---:|
| Total CSV input rows | 12,138 |
| Unique raw records | 12,136 |
| Invalid records found | 4 |
| Customer dimension rows | 240 |
| Prepaid transaction rows | 1,105 |
| Postpaid billing rows | 84 |
| Daily app usage fact rows | 9,116 |
| Customer feature rows | 240 |
| Numeric customer features | 14 |
| Foreign key check | PASS |
| Data quality alerts | 1 warning |
| Simulated data freshness lag | 5 minutes |

The four invalid records were identified during data quality checks and quarantined. The pipeline still completed successfully because the invalid records were handled separately.

The reported pipeline success rate was 100% for the observed successful run. This only describes the local test run, not the reliability of a production system.

### Checking Duplicate Records

One thing I wanted to check was whether running the same pipeline twice would insert duplicate records.

To test this, I ran the pipeline again with the same input data:

```bash
python run_pipeline.py run --run-date 2026-10-24
```

On the second run, `inserted_raw` became `0`, and the raw and fact-table row counts stayed the same. This shows that the pipeline can handle repeated runs with the same input without inserting the same raw records again.

## Churn Model

I also added a simple Logistic Regression model in `telco_pipeline/churn_model.py`.

The model uses 14 customer features, including usage patterns, inactivity, customer tenure, prepaid top-up behavior, and postpaid payment information.

Since the project does not have actual customer churn outcomes, I created dummy churn labels using a predefined risk-scoring rule. The model then learns to classify these labels using a 75:25 training and testing split.

One of my local runs produced these results:

| Evaluation Metric | Result |
|---|---:|
| Accuracy | 96.67% |
| Precision | 90.00% |
| Recall | 100.00% |
| F1-score | 94.74% |
| ROC-AUC | 1.00 |

The confusion matrix from that run was:

| | Predicted Non-Churn | Predicted Churn |
|---|---:|---:|
| Actual Non-Churn | 40 | 2 |
| Actual Churn | 0 | 18 |

These results show that the model can learn the dummy labels used in this demonstration. However, they do not prove that the model can predict real customer churn accurately, because the labels are generated from a rule based on the same features used by the model.

The current dataset also contains only one customer snapshot, so the model has not been evaluated using a time-based train/test split or actual churn outcomes.

## Project Structure

```text
.
├── run_pipeline.py
├── requirements.txt
├── README.md
├── telco_pipeline/
│   ├── __init__.py
│   ├── generator.py
│   ├── pipeline.py
│   └── churn_model.py
├── sql/
│   ├── schema.sql
│   └── sample_queries.sql
├── data/
│   └── synthetic/
├── outputs/
│   └── sample/
├── docs/
│   ├── end_to_end_flow.png
│   ├── dwh_model.png
│   ├── data_dictionary.md
│   └── runbook.md
└── tests/
    ├── test_pipeline.py
    └── test_churn_model.py
```

## Data Quality and Monitoring

I included several basic checks to make the pipeline easier to maintain and troubleshoot:

- **Duplicate handling:** repeated source records are not inserted again.
- **Data validation:** the pipeline checks identifiers, numeric values, timestamps, invoice consistency, and foreign key relationships.
- **Invalid records:** records that fail validation are recorded with their issue types.
- **Pipeline monitoring:** execution results and alerts are stored in SQLite and reported through JSON.
- **Repeated runs:** the pipeline can be run again with the same input data without duplicating raw records.

There are still limitations. The usage aggregation is rebuilt from raw history on each run, which is acceptable for this small demonstration but would be inefficient for a much larger production dataset.

A real implementation would also need scheduled execution, incremental processing, access controls, privacy safeguards, and a proper alerting system.

## What I Learned

Working on this project helped me understand that Data Engineering involves more than just moving data from one place to another.

The data needs to be checked, stored in a consistent structure, and prepared so that other teams can use it. I also learned how data quality issues, duplicate records, and pipeline monitoring can affect the reliability of the overall system.

Adding the churn model helped me understand how the features prepared by a data pipeline can be passed to a machine learning workflow. However, building a useful model also requires reliable labels and proper evaluation, not just running a training algorithm.

## Project Limitations

This project is a local demonstration built with dummy data. It is not connected to actual telecom systems and is not intended for real customer decisions, customer outreach, or financial reporting.

The churn model is an educational example using dummy labels, not a validated model for real-world customer churn prediction.

For more details, see the [data dictionary](docs/data_dictionary.md) and [incident runbook](docs/runbook.md).
>>>>>>> a61e596 (Add churn model demo and update README)
