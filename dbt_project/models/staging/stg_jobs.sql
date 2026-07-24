WITH source_data AS (
    SELECT * FROM {{ source('raw', 'raw_jobs') }}
)

SELECT
    job_id,
    TRIM(title) AS title,
    COALESCE(NULLIF(TRIM(company_name), ''), 'Unknown Company') AS company_name,
    COALESCE(NULLIF(TRIM(city), ''), 'Unknown City') AS city,
    COALESCE(NULLIF(TRIM(state), ''), 'Unknown State') AS state,
    COALESCE(NULLIF(TRIM(country), ''), 'Unknown Country') AS country,
    TRIM(work_type) AS work_type,
    TRIM(currency) AS currency,
    job_description,
    -- Safely convert salary strings to numeric values
    CASE 
        WHEN salary_min = '' OR salary_min IS NULL THEN NULL
        ELSE CAST(salary_min AS DECIMAL(12, 2))
    END AS salary_min,
    CASE 
        WHEN salary_max = '' OR salary_max IS NULL THEN NULL
        ELSE CAST(salary_max AS DECIMAL(12, 2))
    END AS salary_max,
    -- Safely convert string dates to Date types
    CASE 
        WHEN posted_date = '' OR posted_date IS NULL THEN NULL
        ELSE CAST(posted_date AS DATE)
    END AS posted_date,
    ingested_at
FROM source_data
