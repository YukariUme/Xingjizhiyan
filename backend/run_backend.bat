@echo off
chcp 65001 >nul
title 星计知研 · 后端 (http://127.0.0.1:8000)
cd /d %~dp0
echo [后端] 工作目录: %cd%
echo [后端] 步骤 1/3：检查依赖...
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo [后端] 依赖安装失败，请检查网络后重试。
  pause
  exit /b 1
)
echo [后端] 步骤 2/3：初始化演示数据...
python -m app.seed
echo [后端] 步骤 3/3：启动服务 http://127.0.0.1:8000
echo [后端] 提示：不要关闭本窗口，关闭即停止后端。
echo.
python -m uvicorn app.main:app --port 8000
echo.
echo [后端] 服务已退出（错误码 %errorlevel%）。
echo 如果上方出现 WinError 10013：
echo   1) 关闭本窗口，右键 dev.bat 选择“以管理员身份运行”；
echo   2) 或检查 Windows 防火墙/杀毒软件是否拦截 python.exe；
echo   3) 或改用其他端口：python -m uvicorn app.main:app --port 8001，
echo      并在 frontend/vite.config.ts 里把 target 端口同步改为 8001。
echo.
pause

