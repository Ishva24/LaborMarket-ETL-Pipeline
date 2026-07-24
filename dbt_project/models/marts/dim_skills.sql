WITH skills AS (
    SELECT DISTINCT skill_name
    FROM {{ ref('stg_skills') }}
    WHERE skill_name IS NOT NULL AND skill_name != ''
)

SELECT
    MD5(skill_name) AS skill_key,
    skill_name,
    CASE 
        WHEN skill_name IN ('Python', 'Scala', 'SQL') THEN 'Programming Language'
        WHEN skill_name IN ('Docker', 'Kubernetes') THEN 'DevOps / Containers'
        WHEN skill_name IN ('dbt', 'Airflow', 'Spark', 'PySpark') THEN 'Data Engineering'
        WHEN skill_name IN ('Tableau', 'Excel') THEN 'Analytics / BI'
        WHEN skill_name IN ('AWS', 'BigQuery', 'Snowflake', 'PostgreSQL') THEN 'Cloud & Database'
        ELSE 'Other Technical Skill'
    END AS skill_category
FROM skills
