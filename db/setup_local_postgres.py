import os
import sys
import zipfile
import requests
import subprocess
import time

def download_file(url, dest_path):
    print(f"Downloading {url}...")
    response = requests.get(url, stream=True)
    response.raise_for_status()
    total_size = int(response.headers.get('content-length', 0))
    block_size = 1024 * 1024  # 1MB blocks
    downloaded = 0
    
    with open(dest_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=block_size):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    percent = (downloaded / total_size) * 100
                    print(f"Progress: {percent:.1f}% ({downloaded / (1024*1024):.1f} MB / {total_size / (1024*1024):.1f} MB)", end='\r')
                else:
                    print(f"Downloaded {downloaded / (1024*1024):.1f} MB", end='\r')
    print("\nDownload complete.")

def main():
    db_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(db_dir)
    
    zip_url = "https://get.enterprisedb.com/postgresql/postgresql-15.3-1-windows-x64-binaries.zip"
    zip_dest = os.path.join(db_dir, "postgresql-15.3.zip")
    extract_path = os.path.join(db_dir, "pg_dist")
    
    # 1. Download PostgreSQL zip if not already downloaded
    if not os.path.exists(zip_dest) and not os.path.exists(extract_path):
        download_file(zip_url, zip_dest)
    else:
        print("Zip package already exists or extracted.")
        
    # 2. Extract ZIP
    if not os.path.exists(extract_path):
        print(f"Extracting to {extract_path}...")
        os.makedirs(extract_path, exist_ok=True)
        with zipfile.ZipFile(zip_dest, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
        print("Extraction complete.")
        # Cleanup zip file to free space
        try:
            os.remove(zip_dest)
            print("Cleaned up zip file.")
        except Exception as e:
            print(f"Failed to remove zip: {e}")
            
    # Define binary paths
    pg_bin_dir = os.path.join(extract_path, "pgsql", "bin")
    initdb_path = os.path.join(pg_bin_dir, "initdb.exe")
    pg_ctl_path = os.path.join(pg_bin_dir, "pg_ctl.exe")
    createdb_path = os.path.join(pg_bin_dir, "createdb.exe")
    psql_path = os.path.join(pg_bin_dir, "psql.exe")
    
    pg_data_dir = os.path.join(db_dir, "pg_data")
    pw_file = os.path.join(db_dir, "pw.txt")
    log_file = os.path.join(db_dir, "pg_log.txt")
    
    # 3. Initialize database if data directory is empty
    if not os.path.exists(pg_data_dir):
        print("Initializing database cluster...")
        os.makedirs(pg_data_dir, exist_ok=True)
        
        # Write password to file
        password = "admin_password_998"
        with open(pw_file, 'w', encoding='utf-8') as f:
            f.write(password)
            
        try:
            # Run initdb
            cmd = [
                initdb_path,
                "-D", pg_data_dir,
                "-U", "admin_user",
                f"--pwfile={pw_file}",
                "--auth=scram-sha-256"
            ]
            print(f"Running: {' '.join(cmd)}")
            subprocess.run(cmd, check=True)
            print("Database cluster initialized successfully.")
        finally:
            if os.path.exists(pw_file):
                os.remove(pw_file)
                
    # 4. Start database server
    print("Starting PostgreSQL server...")
    start_cmd = [
        pg_ctl_path,
        "-D", pg_data_dir,
        "-l", log_file,
        "start"
    ]
    print(f"Running: {' '.join(start_cmd)}")
    subprocess.run(start_cmd, check=True)
    time.sleep(3) # Wait for server to start
    
    # 5. Create database if it does not exist
    try:
        # Check if DB exists or just run createdb and catch if it already exists
        print("Creating 'labor_market' database...")
        create_db_cmd = [
            createdb_path,
            "-U", "admin_user",
            "-p", "5432",
            "-h", "localhost",
            "labor_market"
        ]
        # Set PGPASSWORD env variable for authentication
        env = os.environ.copy()
        env["PGPASSWORD"] = "admin_password_998"
        
        subprocess.run(create_db_cmd, env=env, check=True)
        print("Database 'labor_market' created.")
    except subprocess.CalledProcessError as e:
        print(f"Database creation skipped or failed (it might already exist). details: {e}")
        
    # 6. Initialize schemas and tables using init_raw.sql
    try:
        print("Initializing database tables from init_raw.sql...")
        init_sql_path = os.path.join(db_dir, "init_raw.sql")
        init_db_schema_cmd = [
            psql_path,
            "-U", "admin_user",
            "-p", "5432",
            "-h", "localhost",
            "-d", "labor_market",
            "-f", init_sql_path
        ]
        env = os.environ.copy()
        env["PGPASSWORD"] = "admin_password_998"
        subprocess.run(init_db_schema_cmd, env=env, check=True)
        print("Database schemas initialized.")
    except Exception as e:
        print(f"Failed to initialize schemas: {e}")
        
    print("\nLocal user-space PostgreSQL setup is complete and running!")
    print("To stop it, run:")
    print(f'"{pg_ctl_path}" -D "{pg_data_dir}" stop')

if __name__ == "__main__":
    main()
