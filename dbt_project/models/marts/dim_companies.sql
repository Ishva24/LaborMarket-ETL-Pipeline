WITH companies AS (
    SELECT DISTINCT company_name
    FROM {{ ref('stg_jobs') }}
    WHERE company_name IS NOT NULL AND company_name != ''
)

SELECT
    MD5(company_name) AS company_key,
    company_name
FROM companies
