WITH source_data AS (
    SELECT * FROM {{ source('raw', 'temp_job_skills') }}
)

SELECT
    job_id,
    TRIM(skill_name) AS skill_name
FROM source_data
