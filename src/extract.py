import os
import json
import random
import pandas as pd
from datetime import datetime, timedelta

def generate_mock_jobs(num_jobs=150):
    """Generates realistic job posting data for testing the ELT pipeline."""
    job_titles = [
        "Data Engineer", "Senior Data Engineer", "Analytics Engineer",
        "Python Developer", "Backend Software Engineer", "DevOps Engineer",
        "Data Analyst", "Machine Learning Engineer", "Cloud Architect",
        "Database Administrator", "Fullstack Developer (React/Python)"
    ]
    
    companies = [
        "TechCorp Solutions", "FinTech Dynamics", "HealthAI Systems",
        "Global Retail Group", "CloudStream", "Quantum Data Corp",
        "GreenTech Ventures", "LogiChain Innovations", "DataBricks Solutions"
    ]
    
    cities = [
        ("San Francisco", "CA", "USA"),
        ("New York", "NY", "USA"),
        ("Austin", "TX", "USA"),
        ("Seattle", "WA", "USA"),
        ("Chicago", "IL", "USA"),
        ("London", None, "UK"),
        ("Berlin", None, "Germany"),
        ("Toronto", "ON", "Canada"),
        ("Bangalore", "KA", "India")
    ]
    
    work_types = ["Remote", "Hybrid", "Onsite"]
    currencies = ["USD", "GBP", "EUR", "INR", "CAD"]
    
    # Text descriptions filled with keywords for NLP matcher to pick up
    descriptions = [
        "We are looking for a developer skilled in Python, SQL, and database systems. Experience with Docker and Tableau is highly desired.",
        "Join our team as a Data Engineer. You will build pipelines using Spark, Scala, and dbt. Kubernetes and Airflow are a plus.",
        "Seeking a Python Developer to write clean code, automate testing, and deploy to AWS. Must know Docker and Git.",
        "We need an Analytics Engineer. You will model data using SQL and dbt, build dashboards in Tableau, and work with BigQuery.",
        "Looking for a Machine Learning Engineer. Skills required: Python, Pandas, PySpark, AWS, and ML models deployment.",
        "Database developer position. Strong experience in SQL, PostgreSQL, Docker, database performance tuning, and Tableau dashboards.",
        "DevOps Engineer wanted. Deploy systems using Kubernetes, Docker, AWS, and automate CI/CD pipelines.",
        "Data Analyst role. Analyze transaction data using SQL and Excel, visualize in Tableau, and code automated reports in Python."
    ]
    
    jobs_data = []
    base_date = datetime.now() - timedelta(days=30)
    
    for i in range(num_jobs):
        job_id = f"job-{1000 + i}"
        title = random.choice(job_titles)
        company = random.choice(companies)
        city, state, country = random.choice(cities)
        work_type = random.choice(work_types)
        
        # Random salary ranges
        curr = random.choice(currencies)
        if curr == "USD":
            sal_min = random.randint(70000, 110000)
            sal_max = sal_min + random.randint(15000, 45000)
        elif curr == "GBP":
            sal_min = random.randint(50000, 80000)
            sal_max = sal_min + random.randint(10000, 30000)
        elif curr == "EUR":
            sal_min = random.randint(55000, 85000)
            sal_max = sal_min + random.randint(10000, 30000)
        elif curr == "INR":
            sal_min = random.randint(800000, 1500000)
            sal_max = sal_min + random.randint(300000, 800000)
        else: # CAD
            sal_min = random.randint(80000, 120000)
            sal_max = sal_min + random.randint(15000, 35000)
            
        posted_date = (base_date + timedelta(days=random.randint(0, 30))).strftime("%Y-%m-%d")
        desc = random.choice(descriptions)
        
        # Introduce some missing salary values to test imputation logic (approx 15% missingness)
        if random.random() < 0.15:
            sal_min = ""
            sal_max = ""
            
        jobs_data.append({
            "job_id": job_id,
            "title": title,
            "company_name": company,
            "city": city,
            "state": state if state else "",
            "country": country,
            "posted_date": posted_date,
            "salary_min": str(sal_min),
            "salary_max": str(sal_max),
            "currency": curr,
            "work_type": work_type,
            "job_description": desc
        })
        
    return pd.DataFrame(jobs_data)

def fetch_api_data():
    """Simulates API fetch and saves raw CSV payload in the data/raw directory."""
    print("Starting extraction task...")
    
    # Create landing directory
    os.makedirs("data/raw", exist_ok=True)
    
    # Generate mock data
    df = generate_mock_jobs(num_jobs=150)
    
    # Generate timestamped filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"data/raw/raw_jobs_{timestamp}.csv"
    
    # Save file
    df.to_csv(output_filename, index=False)
    print(f"Extraction complete. Saved {len(df)} raw postings to {output_filename}")
    
    return output_filename

if __name__ == "__main__":
    fetch_api_data()
