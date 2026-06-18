@echo off
REM Deploie l'API Emo sur Fly.io (1 fois) — necessaire pour Google Auth + chat
cd /d "%~dp0\.."

where fly >nul 2>&1
if errorlevel 1 (
  echo Installe flyctl: winget install flyio.flyctl
  exit /b 1
)

echo.
echo === Deploiement Fly.io : emo-online-xeroxytb ===
echo Tu dois etre connecte: fly auth login
echo.

fly apps list 2>nul | findstr /C:"emo-online-xeroxytb" >nul
if errorlevel 1 (
  echo Creation de l'app...
  fly apps create emo-online-xeroxytb
)

if not exist "emo\backend\.env" (
  echo Fichier emo\backend\.env introuvable — copie .env.example et remplis MONGO_URL + Google
  exit /b 1
)

echo Configure les secrets depuis ton .env local...
for /f "usebackq tokens=1,* delims==" %%a in ("emo\backend\.env") do (
  if /i "%%a"=="MONGO_URL" set MONGO_URL=%%b
  if /i "%%a"=="GOOGLE_CLIENT_ID" set GOOGLE_CLIENT_ID=%%b
  if /i "%%a"=="GOOGLE_CLIENT_SECRET" set GOOGLE_CLIENT_SECRET=%%b
  if /i "%%a"=="OPENAI_API_KEY" set OPENAI_API_KEY=%%b
)

fly secrets set ^
  MONGO_URL=%MONGO_URL% ^
  DB_NAME=emo ^
  EMO_PUBLIC_BACKEND_URL=https://emo-online-xeroxytb.fly.dev ^
  EMO_FRONTEND_URL=https://xeroxytb.github.io/emo-online ^
  CORS_ORIGINS=https://xeroxytb.github.io ^
  GOOGLE_CLIENT_ID=%GOOGLE_CLIENT_ID% ^
  GOOGLE_CLIENT_SECRET=%GOOGLE_CLIENT_SECRET% ^
  OPENAI_API_KEY=%OPENAI_API_KEY% ^
  --app emo-online-xeroxytb

echo Deploiement Docker...
fly deploy --app emo-online-xeroxytb

echo.
echo OK — teste: https://emo-online-xeroxytb.fly.dev/api/health
echo Puis Google login sur: https://xeroxytb.github.io/emo-online
