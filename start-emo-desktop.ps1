# Lance Emo Desktop depuis le bon dossier (evite l'erreur "fichier introuvable")
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $root
Write-Host "[Emo Desktop] $root" -ForegroundColor Cyan

$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py", "-3.11" } else { "python" }
& $py -m pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r (Join-Path $root "emo\desktop\requirements.txt") -q

$cfg = Join-Path $root "emo\desktop\config\api_keys.json"
$example = Join-Path $root "emo\desktop\config\api_keys.json.example"
if (-not (Test-Path $cfg) -and (Test-Path $example)) {
    Copy-Item $example $cfg
    Write-Host "Cree api_keys.json — configure gemini_api_key et agent_token" -ForegroundColor Yellow
}

& $py -m emo.desktop
