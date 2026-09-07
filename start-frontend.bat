@echo off
setlocal
cd /d "%~dp0frontend"
where node >nul 2>&1 || (
  echo Node.js was not found on PATH.
  exit /b 1
)
if not exist "node_modules" (
  echo Installing frontend dependencies...
  call npm install || exit /b 1
)
set NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
call npm run dev
