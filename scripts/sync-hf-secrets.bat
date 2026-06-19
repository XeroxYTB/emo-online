@echo off
cd /d "%~dp0.."
echo Sync secrets HF Space ^(Xroxx/emo-online-api^)...
python scripts\sync-hf-secrets.py
if errorlevel 1 (
  echo.
  echo Echec. Verifie HF_TOKEN dans emo\backend\.env
  pause
  exit /b 1
)
echo.
echo OK. Redemarre le Space sur huggingface.co si les clés ne sont pas prises en compte.
pause
