@echo off
if "%1"=="" (
    echo Usage: restore.bat ^<filename.sql^>
    exit /b
)
echo Restoring database from %1...
cat %1 | docker exec -i dfr_db psql -U postgres
echo Restore complete!
