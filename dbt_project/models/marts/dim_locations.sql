WITH locations AS (
    SELECT DISTINCT city, state, country
    FROM {{ ref('stg_jobs') }}
    WHERE (city IS NOT NULL AND city != '') 
       OR (state IS NOT NULL AND state != '')
       OR (country IS NOT NULL AND country != '')
)

SELECT
    MD5(COALESCE(city, '') || '-' || COALESCE(state, '') || '-' || COALESCE(country, '')) AS location_key,
    city,
    state,
    country
FROM locations
