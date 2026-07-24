WITH raw_jobs AS (
    SELECT * FROM {{ ref('stg_jobs') }}
),

overall_stats AS (
    SELECT
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY salary_min) AS overall_med_min,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY salary_max) AS overall_med_max
    FROM raw_jobs
),

title_stats AS (
    SELECT 
        title,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY salary_min) AS title_med_min,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY salary_max) AS title_med_max
    FROM raw_jobs
    GROUP BY title
),

imputed_jobs AS (
    SELECT
        j.job_id,
        j.title,
        j.company_name,
        j.city,
        j.state,
        j.country,
        j.work_type,
        j.currency,
        j.posted_date,
        -- Impute salary_min: original -> title median -> overall median -> 0.0 fallback
        COALESCE(
            j.salary_min, 
            t.title_med_min, 
            (SELECT overall_med_min FROM overall_stats), 
            0.0
        ) AS salary_min,
        -- Impute salary_max: original -> title median -> overall median -> 0.0 fallback
        COALESCE(
            j.salary_max, 
            t.title_med_max, 
            (SELECT overall_med_max FROM overall_stats), 
            0.0
        ) AS salary_max
    FROM raw_jobs j
    LEFT JOIN title_stats t ON j.title = t.title
)

SELECT
    MD5(j.job_id) AS job_key,
    j.job_id,
    j.title AS job_title,
    MD5(j.company_name) AS company_key,
    MD5(COALESCE(j.city, '') || '-' || COALESCE(j.state, '') || '-' || COALESCE(j.country, '')) AS location_key,
    j.posted_date,
    j.salary_min,
    j.salary_max,
    (j.salary_min + j.salary_max) / 2.0 AS salary_midpoint,
    j.currency,
    j.work_type
FROM imputed_jobs j
