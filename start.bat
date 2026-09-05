@echo off
rem Auto-KenBurns one-click launcher (thin ASCII wrapper; logic lives in scripts\start.ps1)
rem Port precedence: args (-BackendPort / -FrontendPort) > env BACKEND_PORT / FRONTEND_PORT > defaults in scripts\_common.ps1
chcp 65001 >nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start.ps1" %*
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" pause
exit /b %RC%
