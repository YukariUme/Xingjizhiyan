@echo off
rem ============================================
rem  Start local PostgreSQL (port 5433)
rem  Idempotent: skips if already running
rem ============================================

set "PG_BIN=C:\Program Files\PostgreSQL\17\bin"
set "PGDATA=D:\MyStudy\2026Summer\jbgs\backend\data\pgdata"
set "PGPORT=5433"

netstat -ano | findstr ":%PGPORT% " | findstr "LISTENING" >nul 2>&1
if not errorlevel 1 (
  echo [PostgreSQL] already running on port %PGPORT%
  exit /b 0
)

echo [PostgreSQL] starting on port %PGPORT% ...
"%PG_BIN%\pg_ctl.exe" start -D "%PGDATA%" -o "-p %PGPORT%" -l "%PGDATA%\server.log" -w
if not errorlevel 1 (
  echo [PostgreSQL] started
  exit /b 0
)

echo [PostgreSQL] pg_ctl unavailable, starting postgres.exe directly ...
powershell -NoProfile -Command "Start-Process -FilePath '%PG_BIN%\postgres.exe' -ArgumentList '-D \"%PGDATA%\" -p %PGPORT%' -WindowStyle Hidden"
timeout /t 4 >nul
netstat -ano | findstr ":%PGPORT% " | findstr "LISTENING" >nul 2>&1
if not errorlevel 1 (
  echo [PostgreSQL] started
) else (
  echo [PostgreSQL] FAILED, check "%PGDATA%\server.log"
)
exit /b 0
