@echo off
rem ============================================
rem  XingJiZhiYan launcher: PG + backend + frontend
rem ============================================
title XingJiZhiYan Launcher
echo ============================================
echo   XingJiZhiYan Teaching-Learning-Research Platform
echo ============================================
echo.
echo Starting PostgreSQL (port 5433) ...
call "%~dp0start_pg.bat"
echo.
echo Starting backend and frontend (two new windows) ...
start "jbgs-backend" cmd /k "cd /d %~dp0backend && call run_backend.bat"
start "jbgs-frontend" cmd /k "cd /d %~dp0frontend && call run_frontend.bat"
echo Waiting for services ...
timeout /t 8 >nul
call :check 8000 backend http://127.0.0.1:8000/api/health
call :check 5173 frontend http://localhost:5173/
echo.
echo Open: http://localhost:5173
echo If backend window shows WinError 10013, close this window and run
echo dev.bat as Administrator. If it shows connection timeout, run start_pg.bat first.
echo.
pause
exit /b

:check
netstat -ano | findstr ":%1 " | findstr "LISTENING" >nul 2>&1
if %errorlevel%==0 (
  echo [%2] up ✓  %3
) else (
  echo [%2] NOT ready - check the %2 window output.
)
exit /b 0
