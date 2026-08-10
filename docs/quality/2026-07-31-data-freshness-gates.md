# Data Freshness Gates for Labor Market Pipelines

Labor-market analytics can drift quickly when postings expire, locations normalize differently, or skill taxonomies change. A freshness gate should track latest posted date, stale record ratio, duplicate job IDs, source coverage, and load timestamp. These checks protect downstream dbt marts and dashboards from stale trend conclusions.
