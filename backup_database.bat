@echo off
echo ========================================================
echo Generando Respaldo Nativo de SQL Server (app_maestria)
echo ========================================================
set BACKUP_DIR=%~dp0database\backups
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"
set BACKUP_FILE=%BACKUP_DIR%\app_maestria_%date:~-4,4%%date:~-7,2%%date:~-10,2%_%time:~0,2%%time:~3,2%%time:~6,2%.bak
set BACKUP_FILE=%BACKUP_FILE: =0%

sqlcmd -S "." -C -E -Q "BACKUP DATABASE [app_maestria] TO DISK = N'%BACKUP_FILE%' WITH NOFORMAT, NOINIT, NAME = N'app_maestria-Full Database Backup', SKIP, NOREWIND, NOUNLOAD, STATS = 10"

echo Respaldo guardado en: %BACKUP_FILE%
pause
