SELECT
    MD5(job_id) AS job_key,
    MD5(skill_name) AS skill_key
FROM {{ ref('stg_skills') }}
