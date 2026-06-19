# Setup gratuit 24/7 — Koyeb (sans carte) + HF backup
# Usage: powershell -ExecutionPolicy Bypass -File scripts\setup-free-24-7.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$EnvFile = Join-Path $Root "emo\backend\.env"
$KoyebUrl = "https://app.koyeb.com"

Write-Host ""
Write-Host "=== Emo Online — Setup gratuit 24/7 (Koyeb) ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "NOTE: Render suspendu (impayes) — on utilise Koyeb a la place." -ForegroundColor Yellow
Write-Host ""

if (-not (Test-Path $EnvFile)) {
    Write-Host ".env introuvable" -ForegroundColor Red
    exit 1
}

function Get-EnvValue($key) {
    foreach ($line in Get-Content $EnvFile) {
        if ($line -match "^\s*$key=(.*)$") {
            $val = $Matches[1].Trim()
            if ($val.StartsWith('"') -and $val.EndsWith('"')) { $val = $val.Substring(1, $val.Length - 2) }
            return $val
        }
    }
    return ""
}

# 1. HF backup
Write-Host "[1/3] Sync HF Space (backup)..." -ForegroundColor Yellow
try {
    py -3 (Join-Path $Root "scripts\sync-hf-secrets.py") 2>$null
    py -3 (Join-Path $Root "scripts\push-hf-clean.py") 2>$null
    Write-Host "  HF OK" -ForegroundColor Green
} catch {
    Write-Host "  HF skip" -ForegroundColor DarkYellow
}

# 2. Koyeb primary
Write-Host "[2/3] Koyeb (API principale gratuite)..." -ForegroundColor Yellow
$koyebToken = Get-EnvValue "KOYEB_TOKEN"
$koyebCli = Get-Command koyeb -ErrorAction SilentlyContinue

if ($koyebToken -and $koyebCli) {
    py -3 (Join-Path $Root "scripts\sync-koyeb-secrets.py")
    Write-Host "  Koyeb env sync OK" -ForegroundColor Green
} else {
    Write-Host "  Deploy Koyeb (gratuit, sans carte) :" -ForegroundColor Yellow
    Write-Host "  1. Va sur https://app.koyeb.com/stores/github" -ForegroundColor White
    Write-Host "  2. Connecte GitHub > repo XeroxYTB/emo-online" -ForegroundColor White
    Write-Host "  3. Create Web Service :" -ForegroundColor White
    Write-Host "     - Builder: Dockerfile" -ForegroundColor DarkGray
    Write-Host "     - Dockerfile path: Dockerfile.render" -ForegroundColor DarkGray
    Write-Host "     - Port: 8010" -ForegroundColor DarkGray
    Write-Host "     - Instance: Free / Eco" -ForegroundColor DarkGray
    Write-Host "     - Region: Washington ou Frankfurt" -ForegroundColor DarkGray
    Write-Host "  4. Colle les secrets depuis emo\backend\.env" -ForegroundColor White
    Write-Host "  5. API token Koyeb > ajoute KOYEB_TOKEN dans .env > relance ce script" -ForegroundColor White
    try { Start-Process "https://app.koyeb.com/stores/github" } catch {}
}

# 3. Deploy hook info
Write-Host "[3/3] Keepalive GitHub Actions : actif (ping toutes les 8 min)" -ForegroundColor Green

Write-Host ""
Write-Host "=== Termine ===" -ForegroundColor Green
Write-Host "Frontend : https://xeroxytb.com" -ForegroundColor Cyan
Write-Host "Apres deploy Koyeb, ajoute redirect Google OAuth :" -ForegroundColor Yellow
Write-Host "  https://TON-SERVICE.koyeb.app/api/auth/google/callback" -ForegroundColor White
Write-Host ""
