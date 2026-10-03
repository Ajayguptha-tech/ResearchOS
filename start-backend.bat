@echo off
setlocal
cd /d "%~dp0backend"
where python >nul 2>&1 || (
  echo Python was not found on PATH.
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  echo Creating backend virtual environment...
  python -m venv .venv || exit /b 1
)
call .venv\Scripts\activate.bat
python -m pip install -r requirements.txt || exit /b 1
set DATABASE_URL=sqlite:///./data/researchos.db
set AI_PROVIDER=local
set CORS_ORIGINS=http://localhost:3000,http://localhost:3001,http://localhost:3002,http://localhost:3003,http://localhost:3004
REM Email provider is loaded from backend/.env (defaults to resend/smtp as configured)
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
