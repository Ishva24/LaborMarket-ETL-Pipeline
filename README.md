# LaborMarket ETL Pipeline

A Python data engineering project for ingesting, validating, enriching, transforming, and analyzing labor-market job posting data.

## Overview

This pipeline simulates labor-market job ingestion, validates raw CSV quality, loads records into PostgreSQL, extracts skills from job descriptions, transforms warehouse tables with dbt, and supports dashboard analysis.

## Features

- Prefect-based ELT orchestration
- Mock job posting ingestion for repeatable local runs
- Raw CSV validation with Great Expectations
- JSON data quality reports under `data/quality/`
- PostgreSQL raw landing tables
- NLP/regex skill extraction from job descriptions
- dbt staging and mart models
- Tableau dashboard workbook
- Docker Compose support for local PostgreSQL

## Project Structure

```text
.
├── db/                         # Database initialization scripts
├── dbt_project/                # dbt project, models, and profiles
├── src/                        # Python pipeline modules
│   ├── extract.py              # Mock extraction
│   ├── validation.py           # Raw file validation and quality reports
│   ├── load_raw.py             # PostgreSQL raw loader
│   ├── parser.py               # Skill extraction
│   └── dashboard.py            # Dashboard helpers
├── main.py                     # Prefect flow entry point
├── docker-compose.yml          # Local database services
├── Dockerfile                  # Container build file
├── requirements.txt            # Python dependencies
└── labor_market_etl_pipeline.md
```

## Setup

Create and activate a virtual environment:

```bash
python -m venv .venv
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start PostgreSQL:

```bash
docker compose up -d
```

Run the pipeline:

```bash
python main.py
```

## Validation

Raw files are validated before loading. The validation step checks required columns, critical nulls, duplicate job IDs, work type values, currency values, and posted date quality.

Each validation run writes a JSON report to:

```text
data/quality/
```

You can syntax-check the validation module with:

```bash
python -m py_compile src/validation.py
```

## dbt

The dbt project lives in `dbt_project/`.

Run models:

```bash
dbt run --project-dir dbt_project --profiles-dir dbt_project
```

Run tests:

```bash
dbt test --project-dir dbt_project --profiles-dir dbt_project
```

## Notes

Generated files such as virtual environments, Python caches, dbt targets, logs, and raw data outputs are intentionally ignored by Git.
