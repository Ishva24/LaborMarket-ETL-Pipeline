import os
import psycopg2
from psycopg2.extras import execute_values

def get_db_connection():
    host = os.getenv("DB_HOST", "localhost")
    db_name = os.getenv("DB_NAME", "labor_market")
    user = os.getenv("DB_USER", "admin_user")
    password = os.getenv("DB_PASSWORD", "admin_password_998")
    port = os.getenv("DB_PORT", "5432")
    
    return psycopg2.connect(
        host=host,
        database=db_name,
        user=user,
        password=password,
        port=port
    )

def extract_skills_regex(description, target_skills):
    """Fallback regex extractor if spaCy is not installed."""
    import re
    matched = []
    desc_lower = description.lower()
    for skill in target_skills:
        # Match word boundaries around skill
        pattern = r'\b' + re.escape(skill.lower()) + r'\b'
        # Special handling for names with symbols
        if skill.lower() in ['react.js', 'reactjs']:
            pattern = r'\b(react\.js|reactjs|react)\b'
        elif skill.lower() == 'c#':
            pattern = r'\bc#\b'
        elif skill.lower() == 'c++':
            pattern = r'\bc\+\+\b'
            
        if re.search(pattern, desc_lower):
            matched.append(skill)
    return matched

def run_nlp_enrichment():
    """Extracts technologies and skills from raw job descriptions using spaCy (or Regex fallback)."""
    print("Initializing skill extraction task...")
    
    target_skills = [
        "Python", "SQL", "Docker", "Tableau", "AWS", "Spark", "Scala", 
        "Kubernetes", "dbt", "Airflow", "Excel", "Pandas", "PySpark", 
        "React", "Git", "BigQuery", "PostgreSQL", "Snowflake"
    ]
    
    # Try importing spaCy
    try:
        import spacy
        from spacy.matcher import PhraseMatcher
        print("Using spaCy PhraseMatcher for NLP skill extraction...")
        try:
            nlp = spacy.load("en_core_web_sm")
        except OSError:
            import sys
            print("Downloading spaCy en_core_web_sm model...")
            os.system(f'"{sys.executable}" -m spacy download en_core_web_sm')
            nlp = spacy.load("en_core_web_sm")
            
        matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
        patterns = [nlp.make_doc(text) for text in target_skills]
        matcher.add("SKILL_PATTERNS", patterns)
        use_spacy = True
    except ImportError:
        print("Warning: spaCy or PhraseMatcher not available. Falling back to regex parser.")
        use_spacy = False
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Fetch only records that are not yet parsed
        cursor.execute("SELECT job_id, job_description FROM raw.raw_jobs WHERE is_parsed = FALSE;")
        records = cursor.fetchall()
        
        if not records:
            print("No new job descriptions to parse.")
            return
            
        parsed_skills_data = []
        skill_map = {s.lower(): s for s in target_skills}
        
        for row in records:
            job_id, description = row[0], row[1] or ""
            
            if use_spacy:
                doc = nlp(description)
                matches = matcher(doc)
                # Deduplicate and normalize match names preserving original target casing
                matched_skills = list(set([skill_map[doc[start:end].text.lower()] for _, start, end in matches]))
            else:
                matched_skills = extract_skills_regex(description, target_skills)
                
            for skill in matched_skills:
                parsed_skills_data.append((job_id, skill))
                
        # Insert skill matches into the buffer table
        if parsed_skills_data:
            execute_values(
                cursor,
                "INSERT INTO raw.temp_job_skills (job_id, skill_name) VALUES %s ON CONFLICT DO NOTHING;",
                parsed_skills_data
            )
            
        # Mark raw jobs as parsed
        job_ids = [row[0] for row in records]
        cursor.execute(
            "UPDATE raw.raw_jobs SET is_parsed = TRUE WHERE job_id = ANY(%s);",
            (job_ids,)
        )
        
        conn.commit()
        print(f"Skill extraction complete. Processed {len(records)} job descriptions. Extracted {len(parsed_skills_data)} skills.")
        
    except Exception as e:
        conn.rollback()
        print(f"Failed during skill extraction: {e}")
        raise e
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    run_nlp_enrichment()
