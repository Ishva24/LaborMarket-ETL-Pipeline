import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import great_expectations as gx
import pandas as pd

REQUIRED_COLS = [
    "job_id",
    "title",
    "company_name",
    "city",
    "country",
    "job_description",
    "work_type",
]
CRITICAL_NOT_NULL_COLS = ["job_id", "title"]
EXPECTED_WORK_TYPES = ["Remote", "Hybrid", "Onsite"]
EXPECTED_CURRENCIES = ["USD", "GBP", "EUR", "INR", "CAD"]
NULL_WARNING_THRESHOLD = 0.25
STALE_POSTING_DAYS = 120


def validate_raw_files(file_path: str) -> bool:
    """Validate raw ingested CSV files and persist a data quality report."""
    print(f"Validating file structure for: {file_path}")

    raw_df = pd.read_csv(file_path)
    quality_report = build_quality_report(raw_df, file_path)
    report_path = write_quality_report(quality_report, file_path)

    if quality_report["failures"]:
        for failure in quality_report["failures"]:
            print(f"Validation failure: {failure}")
        print(f"Data quality report written to {report_path}")
        return False

    run_great_expectations_checks(raw_df)

    for warning in quality_report["warnings"]:
        print(f"Warning: {warning}")

    print(f"Data quality report written to {report_path}")
    print("Great Expectations verification completed successfully.")
    return True


def build_quality_report(raw_df: pd.DataFrame, file_path: str) -> dict[str, Any]:
    """Build a compact report describing raw feed quality gates."""
    missing_columns = [col for col in REQUIRED_COLS if col not in raw_df.columns]
    failures: list[str] = []
    warnings: list[str] = []

    if missing_columns:
        failures.append(f"missing required columns: {', '.join(missing_columns)}")

    null_rates = {
        col: round(float(raw_df[col].isna().mean()), 4)
        for col in raw_df.columns
    }

    for col in CRITICAL_NOT_NULL_COLS:
        if col in raw_df.columns and raw_df[col].isna().any():
            failures.append(f"'{col}' contains null values")

    for col, rate in null_rates.items():
        if rate >= NULL_WARNING_THRESHOLD:
            warnings.append(f"'{col}' is {rate:.0%} null")

    duplicate_job_ids = 0
    if "job_id" in raw_df.columns:
        duplicate_job_ids = int(raw_df["job_id"].duplicated().sum())
        if duplicate_job_ids:
            failures.append(f"job_id contains {duplicate_job_ids} duplicate value(s)")

    invalid_work_types: list[str] = []
    if "work_type" in raw_df.columns:
        invalid_work_types = sorted(
            raw_df.loc[~raw_df["work_type"].isin(EXPECTED_WORK_TYPES), "work_type"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )
        if invalid_work_types:
            failures.append(
                "work_type has invalid value(s): " + ", ".join(invalid_work_types)
            )

    invalid_currencies: list[str] = []
    if "currency" in raw_df.columns:
        invalid_currencies = sorted(
            raw_df.loc[~raw_df["currency"].isin(EXPECTED_CURRENCIES), "currency"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )
        if invalid_currencies:
            warnings.append(
                "currency has non-standard value(s): " + ", ".join(invalid_currencies)
            )

    date_quality = analyze_posted_dates(raw_df)
    if date_quality["invalid_count"]:
        warnings.append(f"posted_date has {date_quality['invalid_count']} invalid value(s)")
    if date_quality["future_count"]:
        warnings.append(f"posted_date has {date_quality['future_count']} future-dated record(s)")
    if date_quality["stale_count"]:
        warnings.append(
            f"posted_date has {date_quality['stale_count']} record(s) older than {STALE_POSTING_DAYS} days"
        )

    return {
        "file_path": file_path,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "row_count": int(len(raw_df)),
        "column_count": int(len(raw_df.columns)),
        "required_columns": REQUIRED_COLS,
        "missing_columns": missing_columns,
        "duplicate_job_ids": duplicate_job_ids,
        "null_rates": null_rates,
        "invalid_work_types": invalid_work_types,
        "invalid_currencies": invalid_currencies,
        "posted_date_quality": date_quality,
        "warnings": warnings,
        "failures": failures,
        "passed": not failures,
    }


def analyze_posted_dates(raw_df: pd.DataFrame) -> dict[str, Any]:
    if "posted_date" not in raw_df.columns:
        return {
            "checked": False,
            "invalid_count": 0,
            "future_count": 0,
            "stale_count": 0,
            "oldest_posted_date": None,
            "newest_posted_date": None,
        }

    parsed_dates = pd.to_datetime(raw_df["posted_date"], errors="coerce", utc=True)
    now = pd.Timestamp.now(tz="UTC")
    stale_cutoff = now - pd.Timedelta(days=STALE_POSTING_DAYS)
    valid_dates = parsed_dates.dropna()

    return {
        "checked": True,
        "invalid_count": int(parsed_dates.isna().sum()),
        "future_count": int((valid_dates > now).sum()),
        "stale_count": int((valid_dates < stale_cutoff).sum()),
        "oldest_posted_date": valid_dates.min().isoformat() if not valid_dates.empty else None,
        "newest_posted_date": valid_dates.max().isoformat() if not valid_dates.empty else None,
    }


def write_quality_report(report: dict[str, Any], file_path: str) -> str:
    report_dir = Path("data/quality")
    report_dir.mkdir(parents=True, exist_ok=True)
    source_name = Path(file_path).stem
    report_path = report_dir / f"{source_name}_quality.json"

    with report_path.open("w", encoding="utf-8") as report_file:
        json.dump(report, report_file, indent=2)
        report_file.write("\n")

    return os.fspath(report_path)


def run_great_expectations_checks(raw_df: pd.DataFrame) -> None:
    """Run column-level Great Expectations checks after structural gates pass."""
    context = gx.get_context()
    data_source = context.data_sources.add_pandas(name="csv_data_source")
    data_asset = data_source.add_dataframe_asset(name="csv_data_asset")
    batch_definition = data_asset.add_batch_definition_whole_dataframe(name="csv_batch_definition")

    validator = context.get_validator(
        batch_request=batch_definition.build_batch_request(batch_parameters={"dataframe": raw_df}),
        create_expectation_suite_with_name="csv_expectation_suite",
    )

    for col in REQUIRED_COLS:
        validator.expect_column_to_exist(col)

    for col in CRITICAL_NOT_NULL_COLS:
        validator.expect_column_values_to_not_be_null(col)

    if "work_type" in raw_df.columns:
        validator.expect_column_values_to_be_in_set("work_type", EXPECTED_WORK_TYPES)

    if "currency" in raw_df.columns:
        validator.expect_column_values_to_be_in_set("currency", EXPECTED_CURRENCIES)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        validate_raw_files(sys.argv[1])
    else:
        print("Please provide a file path to validate.")
