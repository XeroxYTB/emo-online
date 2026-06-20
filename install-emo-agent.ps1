# Installe / lance Emo Agent (gere zip renomme en .exe par erreur)
$ErrorActionPreference = "Stop"
$target = Join-Path $env:LOCALAPPDATA "Emo\emo-agent.exe"
$candidates = @(
    (Join-Path $env:USERPROFILE "Downloads\Emo-Agent.zip"),
    (Join-Path $env:USERPROFILE "Downloads\Emo-Agent.exe"),
    (Join-Path $env:USERPROFILE "Desktop\Emo-Agent.zip"),
    (Join-Path $env:USERPROFILE "Desktop\Emo-Agent.exe")
)

function Test-ZipFile([string]$path) {
    $b = [System.IO.File]::ReadAllBytes($path)
  return $b.Length -ge 2 -and $b[0] -eq 0x50 -and $b[1] -eq 0x4B
}

foreach ($p in $candidates) {
    if (-not (Test-Path -LiteralPath $p)) { continue }
    if (Test-ZipFile $p) {
        Write-Host "Archive ZIP detectee: $p" -ForegroundColor Cyan
        $dest = Join-Path $env:USERPROFILE "Desktop\Emo-Agent"
        if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }
        Expand-Archive -LiteralPath $p -DestinationPath $dest -Force
        Unblock-File -LiteralPath (Join-Path $dest "start.bat") -ErrorAction SilentlyContinue
        Unblock-File -LiteralPath (Join-Path $dest "emo-agent.py") -ErrorAction SilentlyContinue
        Start-Process -FilePath (Join-Path $dest "start.bat")
        exit 0
    }
    if ($p -like "*.exe" -and (Get-Item -LiteralPath $p).Length -gt 100000) {
        Unblock-File -LiteralPath $p -ErrorAction SilentlyContinue
        New-Item -ItemType Directory -Path (Split-Path $target) -Force | Out-Null
        Copy-Item -LiteralPath $p -Destination $target -Force
        break
    }
}

if (Test-Path -LiteralPath $target) {
    Unblock-File -LiteralPath $target -ErrorAction SilentlyContinue
    Start-Process -FilePath $target
    Write-Host "OK: $target" -ForegroundColor Green
} else {
    Write-Host "Telecharge Emo-Agent.zip sur xeroxytb.com (pas .exe si c'est un zip)." -ForegroundColor Yellow
    exit 1
}
