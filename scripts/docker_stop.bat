@echo off
rem ==============================================================================
rem Irish Lotto System - Docker Stop Script (Windows Batch)
rem ==============================================================================
setlocal
cd /d "%~dp0\.."

echo ====================================================================
echo  Irish Lotto System - Stopping Docker Containers (Windows Batch)
echo ====================================================================

docker compose down --remove-orphans

echo >> Docker services stopped.
endlocal
