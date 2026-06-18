@echo off
REM Demarrer le backend Emo (Python 3.11 + venv)
cd /d "%~dp0"

where py >nul 2>&1
if errorlevel 1 (
  echo Installe Python 3.11: winget install Python.Python.3.11
  exit /b 1
)

set VENV=.venv311

if not exist %VENV%\Scripts\python.exe (
  echo Creation du venv Python 3.11...
  py -3.11 -m venv %VENV%
  if errorlevel 1 exit /b 1
)

call %VENV%\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt

if not exist .env (
  echo Copie .env.example vers .env — configure MONGO_URL
  copy /Y .env.example .env
)

echo.
echo Backend sur http://127.0.0.1:8010
python -m uvicorn server:app --reload --port 8010
