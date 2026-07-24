import os
import subprocess
from prefect import task, flow
from src.extract import fetch_api_data
from src.validation import validate_raw_files
from src.load_raw import bulk_insert_raw
from src.parser import run_nlp_enrichment

@task(retries=3, retry_delay_seconds=10)
def extract_jobs_task():
    print("Executing task: Extract job data")
    raw_file_path = fetch_api_data()
    return raw_file_path

@task
def validate_data_task(file_path: str):
    print(f"Executing task: Validate raw data {file_path}")
    is_valid = validate_raw_files(file_path)
    if not is_valid:
        raise ValueError("Data validation failed: Raw schema does not match standards.")
    return file_path

@task
def load_raw_task(file_path: str):
    print(f"Executing task: Load raw records from {file_path} to DB")
    bulk_insert_raw(file_path)

@task
def run_nlp_enrichment_task():
    print("Executing task: NLP skill extraction & enrichment")
    run_nlp_enrichment()

@task
def run_dbt_models_task():
    print("Executing task: Run dbt transformation models")
    
    import sys
    # Find dbt executable in the same directory as Python
    dbt_bin_dir = os.path.dirname(sys.executable)
    dbt_exe = os.path.join(dbt_bin_dir, "dbt.exe")
    if not os.path.exists(dbt_exe):
        dbt_exe = "dbt"
        
    dbt_dir = os.path.join(os.getcwd(), "dbt_project")
    
    print(f"Running: {dbt_exe} run")
    run_res = subprocess.run(
        [dbt_exe, "run", "--project-dir", dbt_dir, "--profiles-dir", dbt_dir],
        capture_output=True,
        text=True
    )
    print(run_res.stdout)
    if run_res.returncode != 0:
        print(run_res.stderr)
        raise RuntimeError(f"dbt run failed with exit code {run_res.returncode}")
        
    print(f"Running: {dbt_exe} test")
    test_res = subprocess.run(
        [dbt_exe, "test", "--project-dir", dbt_dir, "--profiles-dir", dbt_dir],
        capture_output=True,
        text=True
    )
    print(test_res.stdout)
    if test_res.returncode != 0:
        print(test_res.stderr)
        raise RuntimeError(f"dbt test failed with exit code {test_res.returncode}")

@flow(name="Labor-Market-ELT-Pipeline")
def run_elt_pipeline():
    # 1. Extraction (Ingestion)
    file_path = extract_jobs_task()
    
    # 2. Validation (Great Expectations)
    validated_path = validate_data_task(file_path)
    
    # 3. Load (Raw landing table)
    load_raw_task(validated_path)
    
    # 4. Enrich (NLP Skill parsing)
    run_nlp_enrichment_task()
    
    # 5. Transform (dbt modeling & schema testing)
    run_dbt_models_task()
    
    print("Pipeline run completed successfully!")

if __name__ == "__main__":
    run_elt_pipeline()
