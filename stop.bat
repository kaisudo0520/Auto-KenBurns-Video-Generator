@echo off
rem Auto-KenBurns stop script (thin ASCII wrapper; logic lives in scripts\stop.ps1)
rem Port precedence: args > scripts\.running-ports.json (written by start) > env BACKEND_PORT / FRONTEND_PORT > defaults in scripts\_common.ps1
chcp 65001 >nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\stop.ps1" %*
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" pause
exit /b %RC%
