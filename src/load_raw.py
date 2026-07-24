import os
import psycopg2

def get_db_connection():
    """Establishes database connection using env vars with localhost fallbacks."""
    host = os.getenv("DB_HOST", "localhost")
    db_name = os.getenv("DB_NAME", "labor_market")
    user = os.getenv("DB_USER", "admin_user")
    password = os.getenv("DB_PASSWORD", "admin_password_998")
    port = os.getenv("DB_PORT", "5432")
    
    return psycopg2.connect(
        host=host,
        database=db_name,
        user=user,
        password=password,
        port=port
    )

def bulk_insert_raw(file_path: str):
    """Loads CSV raw records into the raw.raw_jobs database table idempotently."""
    print(f"Loading raw records from {file_path} to PostgreSQL...")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 1. Create a temp staging table to handle duplicates safely
        cursor.execute("""
            CREATE TEMP TABLE temp_stage_jobs (
                job_id VARCHAR(100),
                title VARCHAR(255),
                company_name VARCHAR(255),
                city VARCHAR(100),
                state VARCHAR(100),
                country VARCHAR(100),
                posted_date VARCHAR(50),
                salary_min VARCHAR(50),
                salary_max VARCHAR(50),
                currency VARCHAR(10),
                work_type VARCHAR(50),
                job_description TEXT
            ) ON COMMIT DROP;
        """)
        
        # 2. Bulk copy the CSV file into the temp staging table
        with open(file_path, 'r', encoding='utf-8') as f:
            cursor.copy_expert("""
                COPY temp_stage_jobs (
                    job_id, title, company_name, city, state, country, 
                    posted_date, salary_min, salary_max, currency, 
                    work_type, job_description
                ) FROM STDIN WITH CSV HEADER;
            """, f)
            
        # 3. Upsert from staging table into main raw table
        cursor.execute("""
            INSERT INTO raw.raw_jobs (
                job_id, title, company_name, city, state, country,
                posted_date, salary_min, salary_max, currency, work_type, job_description
            )
            SELECT 
                job_id, title, company_name, city, state, country,
                posted_date, salary_min, salary_max, currency, work_type, job_description
            FROM temp_stage_jobs
            ON CONFLICT (job_id) DO UPDATE SET
                title = EXCLUDED.title,
                company_name = EXCLUDED.company_name,
                city = EXCLUDED.city,
                state = EXCLUDED.state,
                country = EXCLUDED.country,
                posted_date = EXCLUDED.posted_date,
                salary_min = EXCLUDED.salary_min,
                salary_max = EXCLUDED.salary_max,
                currency = EXCLUDED.currency,
                work_type = EXCLUDED.work_type,
                job_description = EXCLUDED.job_description,
                is_parsed = FALSE, -- reset parse flag so spaCy re-parses modified postings
                ingested_at = CURRENT_TIMESTAMP;
        """)
        cursor.execute("SELECT COUNT(*) FROM temp_stage_jobs;")
        record_count = cursor.fetchone()[0]
        
        conn.commit()
        print(f"Loaded {record_count} records into raw.raw_jobs successfully.")
        
    except Exception as e:
        conn.rollback()
        print(f"Failed to load raw records: {e}")
        raise e
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        bulk_insert_raw(sys.argv[1])
    else:
        print("Please provide a CSV file path to load.")
