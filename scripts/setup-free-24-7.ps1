# Setup hebergement gratuit 24/7 — Render + HF backup + keepalive auto
# Usage: powershell -ExecutionPolicy Bypass -File scripts\setup-free-24-7.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$EnvFile = Join-Path $Root "emo\backend\.env"
$RenderDeployUrl = "https://render.com/deploy?repo=https://github.com/XeroxYTB/emo-online"

Write-Host ""
Write-Host "=== Emo Online — Setup gratuit 24/7 ===" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path $EnvFile)) {
    Write-Host "Copie .env.example vers emo\backend\.env et configure les cles." -ForegroundColor Red
    exit 1
}

# 1. Sync Hugging Face (backup)
Write-Host "[1/3] Sync secrets Hugging Face..." -ForegroundColor Yellow
try {
    py -3 (Join-Path $Root "scripts\sync-hf-secrets.py")
    Write-Host "  HF OK" -ForegroundColor Green
} catch {
    Write-Host "  HF skip (HF_TOKEN manquant ou erreur)" -ForegroundColor DarkYellow
}

# 2. Sync Render (primary gratuit)
Write-Host "[2/3] Sync secrets Render.com..." -ForegroundColor Yellow
$renderKey = ""
foreach ($line in Get-Content $EnvFile) {
    if ($line -match "^\s*RENDER_API_KEY=(.*)$") { $renderKey = $Matches[1].Trim(); break }
}

if ($renderKey) {
    py -3 (Join-Path $Root "scripts\sync-render-secrets.py")
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  Render OK — https://emo-online-api.onrender.com" -ForegroundColor Green
    }
} else {
    Write-Host "  RENDER_API_KEY absent — deploy Render en 1 clic :" -ForegroundColor Yellow
    Write-Host "  $RenderDeployUrl" -ForegroundColor White
    Write-Host ""
    Write-Host "  Apres le deploy :" -ForegroundColor DarkGray
    Write-Host "  1. Dashboard Render > Account > API Keys > creer une cle" -ForegroundColor DarkGray
    Write-Host "  2. Ajoute RENDER_API_KEY=... dans emo\backend\.env" -ForegroundColor DarkGray
    Write-Host "  3. Relance ce script" -ForegroundColor DarkGray
    try { Start-Process $RenderDeployUrl } catch {}
}

# 3. Push HF code
Write-Host "[3/3] Push code vers HF Space..." -ForegroundColor Yellow
Push-Location $Root
try {
    git -c safe.directory="$Root" push space HEAD:main 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) { Write-Host "  HF deploy OK" -ForegroundColor Green }
    else { Write-Host "  HF push skip (remote space ou token)" -ForegroundColor DarkYellow }
} catch {
    Write-Host "  HF push skip" -ForegroundColor DarkYellow
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "=== Setup termine ===" -ForegroundColor Green
Write-Host "API principale (gratuit 24/7) : https://emo-online-api.onrender.com" -ForegroundColor Cyan
Write-Host "Backup HF                    : https://xroxx-emo-online-api.hf.space" -ForegroundColor DarkGray
Write-Host "Frontend                     : https://xeroxytb.com" -ForegroundColor Cyan
Write-Host ""
Write-Host "Keepalive GitHub Actions : actif (ping toutes les 8 min)" -ForegroundColor DarkGray
Write-Host "Google OAuth redirect URI a ajouter :" -ForegroundColor Yellow
Write-Host "  https://emo-online-api.onrender.com/api/auth/google/callback" -ForegroundColor White
Write-Host ""
