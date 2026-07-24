import os
import pandas as pd
import psycopg2
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# Set Page Config
st.set_page_config(
    page_title="Labor Market Insights & Salary Analytics",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling (Dark Glassmorphism Theme)
st.markdown("""
    <style>
    .main {
        background-color: #0f111a;
        color: #ffffff;
    }
    .stApp {
        background-color: #0f111a;
    }
    div[data-testid="stMetricValue"] {
        font-size: 32px;
        font-weight: 700;
        color: #00ffcc;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 16px;
        color: #8b9bb4;
    }
    h1, h2, h3 {
        color: #ffffff;
        font-family: 'Outfit', 'Inter', sans-serif;
    }
    .metric-card {
        background: rgba(255, 255, 255, 0.03);
        border-radius: 12px;
        padding: 20px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
        backdrop-filter: blur(5px);
        -webkit-backdrop-filter: blur(5px);
    }
    </style>
""", unsafe_allow_html=True)

# Database Connection Helper
@st.cache_resource
def get_db_connection():
    """Establishes database connection using env vars or default localhost config."""
    host = os.getenv("DB_HOST", "localhost")
    db_name = os.getenv("DB_NAME", "labor_market")
    user = os.getenv("DB_USER", "admin_user")
    password = os.getenv("DB_PASSWORD", "admin_password_998")
    port = os.getenv("DB_PORT", "5432")
    
    try:
        conn = psycopg2.connect(
            host=host,
            database=db_name,
            user=user,
            password=password,
            port=port
        )
        conn.autocommit = True
        return conn
    except Exception as e:
        st.error(f"Database Connection Error: {e}")
        return None

# Data Fetching Helpers
@st.cache_data(ttl=60)
def fetch_kpis(_conn):
    """Fetches high-level metrics."""
    queries = {
        "total_jobs": "SELECT COUNT(*) FROM analytics.fct_jobs;",
        "total_companies": "SELECT COUNT(*) FROM analytics.dim_companies;",
        "total_skills": "SELECT COUNT(*) FROM analytics.dim_skills;",
        "avg_salary": "SELECT ROUND(CAST(AVG(salary_midpoint) AS numeric), 2) FROM analytics.fct_jobs WHERE salary_midpoint > 0;"
    }
    
    kpis = {}
    with _conn.cursor() as cur:
        for name, sql in queries.items():
            try:
                cur.execute(sql)
                kpis[name] = cur.fetchone()[0]
            except Exception:
                kpis[name] = 0
    return kpis

@st.cache_data(ttl=60)
def fetch_job_data(_conn):
    """Fetches main jobs fact table with company and location dimensions joined."""
    sql = """
        SELECT 
            j.job_id,
            j.job_title,
            c.company_name,
            l.city,
            l.state,
            l.country,
            j.posted_date,
            j.salary_min,
            j.salary_max,
            j.salary_midpoint,
            j.currency,
            j.work_type
        FROM analytics.fct_jobs j
        JOIN analytics.dim_companies c ON j.company_key = c.company_key
        JOIN analytics.dim_locations l ON j.location_key = l.location_key;
    """
    try:
        return pd.read_sql(sql, _conn)
    except Exception as e:
        st.warning(f"Error fetching jobs: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def fetch_skill_density(_conn):
    """Fetches technology skill count and matching salary profiles."""
    sql = """
        SELECT 
            s.skill_name, 
            s.skill_category,
            COUNT(b.job_key) AS job_count,
            ROUND(CAST(AVG(j.salary_midpoint) AS numeric), 2) AS avg_salary
        FROM analytics.dim_skills s
        JOIN analytics.bridge_job_skills b ON s.skill_key = b.skill_key
        JOIN analytics.fct_jobs j ON b.job_key = j.job_key
        GROUP BY s.skill_name, s.skill_category
        ORDER BY job_count DESC;
    """
    try:
        return pd.read_sql(sql, _conn)
    except Exception as e:
        st.warning(f"Error fetching skill density: {e}")
        return pd.DataFrame()

# Main Dashboard App Flow
def main():
    st.title("💼 Labor Market & Salary Analytics Dashboard")
    st.markdown("An interactive, live analytical view of market demand, salaries, and developer skill density.")
    st.write("---")
    
    conn = get_db_connection()
    if not conn:
        st.warning("⚠️ Waiting for PostgreSQL database container to initialize. Please confirm the database schema is loaded and the Docker containers are running.")
        return
        
    # Sidebar
    st.sidebar.header("Filter Analytics")
    df_jobs = fetch_job_data(conn)
    
    if df_jobs.empty:
        st.info("📊 Database is connected but appears empty. Please run the ETL pipeline (`python main.py` or run docker flow) to ingest and process data.")
        return
        
    # Sidebar Filters
    all_countries = ["All"] + list(df_jobs["country"].unique())
    selected_country = st.sidebar.selectbox("Country", all_countries)
    
    all_work_types = ["All"] + list(df_jobs["work_type"].unique())
    selected_work_type = st.sidebar.selectbox("Work Type", all_work_types)
    
    # Filter dataset
    filtered_df = df_jobs.copy()
    if selected_country != "All":
        filtered_df = filtered_df[filtered_df["country"] == selected_country]
    if selected_work_type != "All":
        filtered_df = filtered_df[filtered_df["work_type"] == selected_work_type]
        
    # KPIs Layout
    kpis = fetch_kpis(conn)
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(label="Total Job Postings", value=f"{kpis['total_jobs']:,}")
    with col2:
        st.metric(label="Hiring Companies", value=f"{kpis['total_companies']:,}")
    with col3:
        st.metric(label="Skills Tracked", value=f"{kpis['total_skills']:,}")
    with col4:
        avg_sal = kpis.get('avg_salary')
        avg_sal_str = f"${avg_sal:,.2f}" if avg_sal else "$0.00"
        st.metric(label="Average Salary (Midpoint)", value=avg_sal_str)
        
    st.write("---")
    
    # Grid: Salary Distribution & Skill Demand
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        st.subheader("Salary Distribution by Job Title")
        job_titles = ["All"] + list(filtered_df["job_title"].unique())
        selected_title = st.selectbox("Select Job Role", job_titles)
        
        salary_df = filtered_df.copy()
        if selected_title != "All":
            salary_df = salary_df[salary_df["job_title"] == selected_title]
            
        if not salary_df.empty:
            fig_box = px.box(
                salary_df, 
                x="job_title", 
                y="salary_midpoint", 
                color="work_type",
                title=f"Salary Ranges for {selected_title}",
                labels={"salary_midpoint": "Salary (USD equivalent)", "job_title": "Job Title"},
                template="plotly_dark",
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            st.plotly_chart(fig_box, use_container_width=True)
        else:
            st.write("No salary data matching selections.")
            
    with chart_col2:
        st.subheader("Top Demanded Skills vs. Median Salary")
        df_skills = fetch_skill_density(conn)
        
        if not df_skills.empty:
            fig_bubble = px.scatter(
                df_skills,
                x="job_count",
                y="avg_salary",
                size="job_count",
                color="skill_category",
                hover_name="skill_name",
                title="Skill Popularity vs. Average Salary",
                labels={"job_count": "Job Frequency (Demand)", "avg_salary": "Average Salary (USD)"},
                template="plotly_dark",
                size_max=40
            )
            st.plotly_chart(fig_bubble, use_container_width=True)
        else:
            st.write("No skill data matching selections.")
            
    st.write("---")
    
    # Geographic Analytics
    geo_col1, geo_col2 = st.columns([1, 2])
    
    with geo_col1:
        st.subheader("Job Openings by Work Type")
        work_counts = filtered_df["work_type"].value_counts().reset_index()
        work_counts.columns = ["work_type", "count"]
        fig_pie = px.pie(
            work_counts, 
            values="count", 
            names="work_type", 
            hole=0.4,
            template="plotly_dark",
            color_discrete_sequence=px.colors.qualitative.Safe
        )
        st.plotly_chart(fig_pie, use_container_width=True)
        
    with geo_col2:
        st.subheader("Job Openings by Location")
        loc_df = filtered_df.groupby(["city", "country"]).size().reset_index(name="job_count")
        loc_df = loc_df.sort_values(by="job_count", ascending=False).head(15)
        fig_bar = px.bar(
            loc_df, 
            x="job_count", 
            y="city", 
            color="country",
            orientation="h",
            title="Top 15 Cities by Job Openings",
            template="plotly_dark"
        )
        st.plotly_chart(fig_bar, use_container_width=True)

if __name__ == "__main__":
    main()
