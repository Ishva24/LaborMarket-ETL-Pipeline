-- Create schemas
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS analytics;

-- Raw jobs landing table
CREATE TABLE IF NOT EXISTS raw.raw_jobs (
    job_id VARCHAR(100) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    company_name VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(100),
    country VARCHAR(100),
    posted_date VARCHAR(50),
    salary_min VARCHAR(50),
    salary_max VARCHAR(50),
    currency VARCHAR(10),
    work_type VARCHAR(50),
    job_description TEXT,
    is_parsed BOOLEAN DEFAULT FALSE,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Buffer table for skills parsed from descriptions
CREATE TABLE IF NOT EXISTS raw.temp_job_skills (
    job_id VARCHAR(100),
    skill_name VARCHAR(100),
    PRIMARY KEY (job_id, skill_name)
);
