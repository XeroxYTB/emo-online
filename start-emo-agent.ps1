# Demarre l'agent Emo local (headless) pour impression / pilotage PC depuis xeroxytb.com
$ErrorActionPreference = 'Stop'

$emoDir = Join-Path $env:LOCALAPPDATA 'Emo'
$agent = Join-Path $emoDir 'emo-agent.exe'
$src = 'H:\Emo Online Final\emo\backend\agent_binaries\emo-agent-windows-amd64.exe'

if (-not (Test-Path $emoDir)) { New-Item -ItemType Directory -Path $emoDir -Force | Out-Null }
if (Test-Path $src) { Copy-Item $src $agent -Force }

if (-not (Test-Path $agent)) {
    Write-Host "emo-agent.exe introuvable. Telechargez Emo-Agent depuis xeroxytb.com > Parametres > Agent." -ForegroundColor Red
    exit 1
}

$token = (Get-Content (Join-Path $emoDir 'token.txt') -Raw -ErrorAction SilentlyContinue).Trim()
$backend = (Get-Content (Join-Path $emoDir 'backend.txt') -Raw -ErrorAction SilentlyContinue).Trim()
if (-not $backend) { $backend = 'https://xroxx-emo-online-api.hf.space' }

if (-not $token) {
    Write-Host "token.txt manquant dans $emoDir - connectez-vous via Emo-Agent.exe une fois." -ForegroundColor Red
    exit 1
}

$existing = Get-Process emo-agent -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Agent deja actif (PID $($existing.Id -join ','))" -ForegroundColor Green
    exit 0
}

Start-Process -FilePath $agent -ArgumentList @('--headless', '--backend', $backend, '--token', $token) -WindowStyle Hidden
Start-Sleep 2

try {
    $hb = Invoke-RestMethod -Uri "$backend/api/agent/heartbeat?token=$token" -Method POST -TimeoutSec 10
    if ($hb.ok) {
        Write-Host "Agent Emo en ligne ($backend)" -ForegroundColor Green
    }
} catch {
    Write-Host "Agent demarre mais heartbeat echoue: $($_.Exception.Message)" -ForegroundColor Yellow
}
