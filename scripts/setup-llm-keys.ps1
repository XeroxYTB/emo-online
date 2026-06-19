# Configure les clés LLM manquantes dans emo/backend/.env puis sync HF Space.
# Usage : powershell -ExecutionPolicy Bypass -File scripts\setup-llm-keys.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$EnvFile = Join-Path $Root "emo\backend\.env"
$Example = Join-Path $Root "emo\backend\.env.example"

Write-Host ""
Write-Host "=== Emo Online — Ajout des clés LLM ===" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path $EnvFile)) {
    if (Test-Path $Example) {
        Copy-Item $Example $EnvFile
        Write-Host "Créé $EnvFile depuis .env.example" -ForegroundColor Yellow
    } else {
        New-Item -ItemType File -Path $EnvFile | Out-Null
    }
}

function Get-EnvValue($key) {
    if (-not (Test-Path $EnvFile)) { return "" }
    foreach ($line in Get-Content $EnvFile) {
        if ($line -match "^\s*$key=(.*)$") { return $Matches[1].Trim().Trim('"') }
    }
    return ""
}

function Set-EnvValue($key, $value) {
    $lines = @()
    $found = $false
    if (Test-Path $EnvFile) { $lines = Get-Content $EnvFile }
    $newLines = @()
    foreach ($line in $lines) {
        if ($line -match "^\s*$key=") {
            if ($value) { $newLines += "$key=$value" }
            $found = $true
        } else {
            $newLines += $line
        }
    }
    if (-not $found -and $value) { $newLines += "$key=$value" }
    $newLines | Set-Content -Path $EnvFile -Encoding UTF8
}

$prompts = @(
    @{
        Key = "OPENROUTER_API_KEY"
        Label = "OpenRouter"
        Url = "https://openrouter.ai/keys"
        Hint = "Gratuit : Llama 3.3, Gemma 2, Qwen 2.5 (suffixe :free)"
    },
    @{
        Key = "DEEPSEEK_API_KEY"
        Label = "DeepSeek"
        Url = "https://platform.deepseek.com/api_keys"
        Hint = "DeepSeek Chat + Reasoner (R1)"
    },
    @{
        Key = "GROQ_API_KEY"
        Label = "Groq"
        Url = "https://console.groq.com/keys"
        Hint = "Llama / Gemma / Mixtral — tier gratuit"
    },
    @{
        Key = "HF_TOKEN"
        Label = "Hugging Face (HF_TOKEN)"
        Url = "https://huggingface.co/settings/tokens"
        Hint = "Token Read — modèles Llama + Kimi via router HF"
    },
    @{
        Key = "GEMINI_API_KEY"
        Label = "Google Gemini"
        Url = "https://aistudio.google.com/apikey"
        Hint = "Gemini 2.0 Flash (quota free)"
    },
    @{
        Key = "OPENAI_API_KEY"
        Label = "OpenAI"
        Url = "https://platform.openai.com/api-keys"
        Hint = "GPT-4o mini — crédits requis"
    },
    @{
        Key = "ANTHROPIC_API_KEY"
        Label = "Anthropic"
        Url = "https://console.anthropic.com/settings/keys"
        Hint = "Claude Haiku / Sonnet — crédits requis"
    }
)

foreach ($p in $prompts) {
    $current = Get-EnvValue $p.Key
    if ($current) {
        Write-Host "[OK] $($p.Label) déjà dans .env" -ForegroundColor Green
        continue
    }
    Write-Host ""
    Write-Host "--- $($p.Label) ---" -ForegroundColor White
    Write-Host $p.Hint
    Write-Host "Obtenir : $($p.Url)" -ForegroundColor DarkGray
    $open = Read-Host "Ouvrir le lien dans le navigateur ? (O/n)"
    if ($open -ne "n" -and $open -ne "N") {
        Start-Process $p.Url
    }
    $val = Read-Host "Colle la clé (Entrée vide = ignorer)"
    if ($val.Trim()) {
        Set-EnvValue $p.Key $val.Trim()
        Write-Host "  -> enregistré dans .env" -ForegroundColor Green
    }
}

# URLs prod
Set-EnvValue "EMO_PUBLIC_BACKEND_URL" "https://xroxx-emo-online-api.hf.space"
Set-EnvValue "EMO_FRONTEND_URL" "https://xeroxytb.com"
Set-EnvValue "CORS_ORIGINS" "https://xeroxytb.com,https://www.xeroxytb.com,https://xeroxytb.github.io"

Write-Host ""
$sync = Read-Host "Synchroniser vers Hugging Face Space maintenant ? (O/n)"
if ($sync -ne "n" -and $sync -ne "N") {
    $hf = Get-EnvValue "HF_TOKEN"
    if (-not $hf) {
        Write-Host "HF_TOKEN requis pour sync HF (Settings > Access Tokens sur huggingface.co)" -ForegroundColor Yellow
        $hf = Read-Host "Colle ton HF_TOKEN (Write)"
        if ($hf.Trim()) { Set-EnvValue "HF_TOKEN" $hf.Trim() }
    }
    if (Get-EnvValue "HF_TOKEN") {
        & python (Join-Path $Root "scripts\sync-hf-secrets.py")
    }
}

Write-Host ""
Write-Host "Vérification :" -ForegroundColor Cyan
& python (Join-Path $Root "scripts\check-llm-keys.py")
Write-Host ""
Write-Host "Redémarre le Space HF après sync (Settings > Restart) si besoin." -ForegroundColor DarkGray
