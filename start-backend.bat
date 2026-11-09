@echo off
setlocal
cd /d "%~dp0backend"
where python >nul 2>&1 || (
  echo Python was not found on PATH.
  exit /b 1
)
if exist ".venv\Scripts\python.exe" (
  call .venv\Scripts\activate.bat
)
set DATABASE_URL=sqlite:///./data/researchos.db
set AI_PROVIDER=local
set CORS_ORIGINS=http://localhost:3000,http://localhost:3001,http://localhost:3002,http://localhost:3003,http://localhost:3004
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
