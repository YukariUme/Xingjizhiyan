@echo off
chcp 65001 >nul
title 星计知研 · 前端 (http://localhost:5173)
cd /d %~dp0
echo [前端] 工作目录: %cd%
if not exist node_modules (
  echo [前端] 首次运行：安装依赖（可能需要几分钟，请耐心等待）...
  npm.cmd install --no-audit --no-fund
  if errorlevel 1 (
    echo.
    echo [前端] 依赖安装失败，请检查网络后重试。
    pause
    exit /b 1
  )
) else (
  echo [前端] 依赖已就绪。
)
echo [前端] 启动开发服务器 http://localhost:5173
echo [前端] 提示：不要关闭本窗口，关闭即停止前端。
echo.
npm.cmd run dev
echo.
echo [前端] 服务已退出（错误码 %errorlevel%）。
pause

