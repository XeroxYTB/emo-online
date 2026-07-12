@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo [Emo Terminal] Dossier: %CD%
echo.

where py >nul 2>&1
if %ERRORLEVEL% EQU 0 (
  set "PYEXE=py"
  set "PYARG=-3.11"
) else (
  set "PYEXE=python"
  set "PYARG="
)

%PYEXE% %PYARG% --version >nul 2>&1
if errorlevel 1 (
  echo Installe Python 3.11+ depuis https://www.python.org/downloads/
  pause
  exit /b 1
)

if not exist "emo\desktop\config\api_keys.json" (
  if exist "emo\desktop\config\api_keys.json.example" (
    copy /Y "emo\desktop\config\api_keys.json.example" "emo\desktop\config\api_keys.json" >nul
    echo Fichier cree: emo\desktop\config\api_keys.json
  )
)

echo Lancement Emo Desktop (mode terminal)...
%PYEXE% %PYARG% -m emo.desktop --terminal %*
if errorlevel 1 pause
endlocal
