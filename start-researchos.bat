@echo off
setlocal
cd /d "%~dp0"
where python >nul 2>&1 || (echo Python was not found on PATH. & exit /b 1)
where node >nul 2>&1 || (echo Node.js was not found on PATH. & exit /b 1)
start "ResearchOS Backend" cmd /k "call "%~dp0start-backend.bat""
start "ResearchOS Frontend" cmd /k "call "%~dp0start-frontend.bat""
echo ResearchOS is starting.
echo Frontend: http://localhost:3000/workspace
echo Backend:  http://localhost:8000/docs
echo Health:   http://localhost:8000/health/dependencies
