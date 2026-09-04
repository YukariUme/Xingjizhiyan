@echo off
chcp 65001 >nul
cd /d %~dp0backend
python -m app.check_llm
pause
