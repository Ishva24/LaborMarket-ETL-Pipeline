@echo off
set "PG_BIN=%~dp0db\pg_dist\pgsql\bin\pg_ctl.exe"
set "PG_DATA=%~dp0db\pg_data"
set "PG_LOG=%~dp0db\pg_log.txt"
echo Starting local PostgreSQL...
if not exist "%PG_BIN%" (
    echo Error: PostgreSQL binaries not found. Please run "python db\setup_local_postgres.py" first to set up.
    pause
    exit /b 1
)
"%PG_BIN%" -D "%PG_DATA%" -l "%PG_LOG%" start
