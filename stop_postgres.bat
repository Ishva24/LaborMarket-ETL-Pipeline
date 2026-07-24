@echo off
set "PG_BIN=%~dp0db\pg_dist\pgsql\bin\pg_ctl.exe"
set "PG_DATA=%~dp0db\pg_data"
echo Stopping local PostgreSQL...
if not exist "%PG_BIN%" (
    echo Error: PostgreSQL binaries not found.
    pause
    exit /b 1
)
"%PG_BIN%" -D "%PG_DATA%" stop
