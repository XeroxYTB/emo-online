# Fly.io deploy — une commande après ajout carte bancaire sur fly.io/billing
# Usage: powershell -ExecutionPolicy Bypass -File scripts\deploy-fly.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$EnvFile = Join-Path $Root "emo\backend\.env"
$FlyApp = "emo-online-xeroxytb"
$FlyUrl = "https://emo-online-xeroxytb.fly.dev"
$FlyBin = Join-Path $env:USERPROFILE ".fly\bin\flyctl.exe"

Write-Host ""
Write-Host "=== Emo Online - Deploy Fly.io 24/7 ===" -ForegroundColor Cyan

if (-not (Test-Path $FlyBin)) {
    iwr https://fly.io/install.ps1 -useb | iex
}

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

$SecretKeys = @(
    "MONGO_URL", "DB_NAME", "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET",
    "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GROQ_API_KEY",
    "OPENROUTER_API_KEY", "DEEPSEEK_API_KEY", "HF_TOKEN", "HUGGINGFACE_API_KEY",
    "EMERGENT_LLM_KEY", "STRIPE_API_KEY", "STRIPE_BASIC_LINK", "STRIPE_PREMIUM_LINK",
    "STRIPE_ULTRA_LINK", "EMO_ADMIN_EMAILS", "EMO_PRODUCT_KEYS", "EMO_USE_SALES_LLM_KEYS"
)

$DupMap = @{
    "SALES_OPENAI_API_KEY" = "OPENAI_API_KEY"
    "SALES_ANTHROPIC_API_KEY" = "ANTHROPIC_API_KEY"
    "SALES_GEMINI_API_KEY" = "GEMINI_API_KEY"
    "SALES_GROQ_API_KEY" = "GROQ_API_KEY"
    "SALES_OPENROUTER_API_KEY" = "OPENROUTER_API_KEY"
    "SALES_DEEPSEEK_API_KEY" = "DEEPSEEK_API_KEY"
    "SALES_HF_TOKEN" = "HF_TOKEN"
}

$FlyEnv = @{
    "EMO_PUBLIC_BACKEND_URL" = $FlyUrl
    "EMO_FRONTEND_URL" = "https://xeroxytb.com"
    "CORS_ORIGINS" = "https://xeroxytb.com,https://www.xeroxytb.com,https://xeroxytb.github.io"
    "GOOGLE_REDIRECT_URI" = "$FlyUrl/api/auth/google/callback"
    "EMO_SERVE_FRONTEND" = "false"
    "EMO_DEV_MODE" = "false"
    "EMO_USE_SALES_LLM_KEYS" = "true"
    "PORT" = "8010"
}

Push-Location $Root
try {
    $apps = & $FlyBin apps list 2>&1 | Out-String
    if ($apps -notmatch $FlyApp) {
        & $FlyBin apps create $FlyApp --org personal
    }

    $pairs = New-Object System.Collections.Generic.List[string]
    foreach ($k in $SecretKeys) {
        $v = Get-EnvValue $k
        if ($v) { [void]$pairs.Add("${k}=$v") }
    }
    foreach ($sales in $DupMap.Keys) {
        if (-not (Get-EnvValue $sales)) {
            $src = Get-EnvValue $DupMap[$sales]
            if ($src) { [void]$pairs.Add("${sales}=$src") }
        }
    }
    foreach ($ek in $FlyEnv.Keys) {
        [void]$pairs.Add("${ek}=$($FlyEnv[$ek])")
    }

    Write-Host "Secrets: $($pairs.Count)" -ForegroundColor Cyan
    & $FlyBin secrets set $pairs.ToArray() --app $FlyApp
    & $FlyBin deploy --app $FlyApp --ha=false
    Write-Host "OK: $FlyUrl" -ForegroundColor Green
    Write-Host "Google redirect: $FlyUrl/api/auth/google/callback" -ForegroundColor Yellow
}
finally {
    Pop-Location
}
