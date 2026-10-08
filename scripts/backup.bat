@echo off
echo Backing up PostgreSQL database...
docker exec -t dfr_db pg_dumpall -c -U postgres > dump_dfr_%date:~10,4%%date:~4,2%%date:~7,2%.sql
echo Backup complete!
