# Setup gratuit 24/7 — Hugging Face Spaces (sans carte bancaire)
# Usage: powershell -ExecutionPolicy Bypass -File scripts\setup-free-24-7.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$EnvFile = Join-Path $Root "emo\backend\.env"
$HfSpaceUrl = "https://xroxx-emo-online-api.hf.space"

Write-Host ""
Write-Host "=== Emo Online — Setup gratuit (HF Spaces, sans carte) ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Koyeb, Fly.io et Render demandent une carte bancaire." -ForegroundColor Yellow
Write-Host "Solution 100% gratuite : Hugging Face Spaces (deja configure)." -ForegroundColor Green
Write-Host ""

if (-not (Test-Path $EnvFile)) {
    Write-Host ".env introuvable : copie emo\backend\.env.example vers emo\backend\.env" -ForegroundColor Red
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

# 1. Sync secrets + deploy HF
Write-Host "[1/2] Sync HF Space..." -ForegroundColor Yellow
$hfToken = Get-EnvValue "HF_TOKEN"
if (-not $hfToken) {
    Write-Host "  HF_TOKEN manquant dans emo\backend\.env" -ForegroundColor Red
    Write-Host "  Cree un token Write : https://huggingface.co/settings/tokens" -ForegroundColor White
    Write-Host "  Ajoute aussi HF_TOKEN dans GitHub > Settings > Secrets (repo emo-online)" -ForegroundColor White
} else {
    try {
        py -3 (Join-Path $Root "scripts\sync-hf-secrets.py")
        py -3 (Join-Path $Root "scripts\push-hf-clean.py")
        Write-Host "  HF deploy OK" -ForegroundColor Green
    } catch {
        Write-Host "  HF deploy echoue (SSL local ?) — le push GitHub Actions le fera au prochain push main" -ForegroundColor DarkYellow
    }
}

# 2. Keepalive info
Write-Host "[2/2] Keepalive GitHub Actions (ping toutes les 12 min)" -ForegroundColor Yellow
Write-Host "  Workflow : .github/workflows/free-24-7.yml" -ForegroundColor DarkGray
Write-Host "  Pas besoin de EMO_API_URL si tu restes sur HF (defaut deja bon)" -ForegroundColor DarkGray

Write-Host ""
Write-Host "=== Termine ===" -ForegroundColor Green
Write-Host "Frontend : https://xeroxytb.com" -ForegroundColor Cyan
Write-Host "API      : $HfSpaceUrl" -ForegroundColor Cyan
Write-Host ""
Write-Host "Checklist :" -ForegroundColor Yellow
Write-Host "  1. Space HF public + secrets (MONGO_URL, GOOGLE_*, GROQ_API_KEY, etc.)" -ForegroundColor White
Write-Host "  2. GitHub secret HF_TOKEN (Write)" -ForegroundColor White
Write-Host "  3. Google OAuth redirect : $HfSpaceUrl/api/auth/google/callback" -ForegroundColor White
Write-Host "  4. Test : $HfSpaceUrl/api/ping" -ForegroundColor White
Write-Host ""
