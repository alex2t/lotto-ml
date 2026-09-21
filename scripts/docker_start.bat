@echo off
rem ==============================================================================
rem Irish Lotto System - Docker Launcher (Windows Batch)
rem Runs drawpick.py data engine, then launches both web front ends
rem ==============================================================================
setlocal
cd /d "%~dp0\.."

echo ====================================================================
echo  Irish Lotto System - Docker Launcher (Windows Batch)
echo ====================================================================

docker --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Docker is not installed or not running.
    echo Please make sure Docker Desktop is running.
    pause
    exit /b 1
)

if not exist "data\analysis" mkdir "data\analysis"

echo [Step 1/2] Running data-engine to generate/update ~24 JSON artifacts...
docker compose run --rm data-engine
if %ERRORLEVEL% neq 0 (
    echo ERROR: Data engine execution failed!
    pause
    exit /b %ERRORLEVEL%
)

echo [Step 2/2] Starting the web front ends...
docker compose up -d --no-deps streamlit-web nextjs-web
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to start the web front ends!
    pause
    exit /b %ERRORLEVEL%
)

echo ====================================================================
echo  SUCCESS: Data analysis complete and both front ends are running!
echo  Streamlit dashboard: http://localhost:8501
echo  Next.js site: http://localhost:3000
echo  To stop: run scripts\docker_stop.bat
echo ====================================================================
endlocal
