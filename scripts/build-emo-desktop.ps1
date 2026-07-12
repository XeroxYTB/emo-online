# Build Emo-Desktop.exe (PyInstaller) — Windows x64
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$Py = "py"
$PyArg = @("-3.11")
& $Py @PyArg --version 2>$null
if ($LASTEXITCODE -ne 0) { $Py = "python"; $PyArg = @() }

function Invoke-PipWithSsl {
    param([string[]]$PipArgs)
    & $Py @PyArg -c @"
import subprocess, sys
try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    import os
    try:
        import certifi
        os.environ.setdefault('SSL_CERT_FILE', certifi.where())
        os.environ.setdefault('REQUESTS_CA_BUNDLE', certifi.where())
    except ImportError:
        pass
args = [sys.executable, '-m', 'pip'] + sys.argv[1:]
code = subprocess.call(args)
if code != 0:
    trusted = ['--trusted-host', 'pypi.org', '--trusted-host', 'pypi.python.org', '--trusted-host', 'files.pythonhosted.org']
    code = subprocess.call([sys.executable, '-m', 'pip'] + sys.argv[1:] + trusted)
raise SystemExit(code)
"@ @PipArgs
    if ($LASTEXITCODE -ne 0) { throw "pip failed: $PipArgs" }
}

Write-Host "[build] pip install pyinstaller + desktop deps..."
Invoke-PipWithSsl @("-q", "install", "pyinstaller", "-r", "emo\desktop\requirements.txt")

$OutDir = Join-Path $Root "emo\backend\agent_binaries"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

Write-Host "[build] PyInstaller (peut prendre 2-5 min)..."
& $Py @PyArg -m PyInstaller `
  --noconfirm `
  --clean `
  --onefile `
  --windowed `
  --name "Emo-Desktop" `
  --paths "$Root" `
  --hidden-import "emo.desktop" `
  --hidden-import "emo.desktop.ui" `
  --hidden-import "emo.desktop.core.live_session" `
  --hidden-import "emo.desktop.core.tool_executor" `
  --hidden-import "emo.desktop.core.tool_declarations" `
  --hidden-import "truststore" `
  --hidden-import "certifi" `
  --hidden-import "pip_system_certs.wrapt_requests" `
  --collect-submodules "google.genai" `
  --collect-all "PyQt6" `
  --collect-all "edge_tts" `
  "emo\desktop\_launcher.py"

$Built = Join-Path $Root "dist\Emo-Desktop.exe"
if (-not (Test-Path $Built)) {
  Write-Error "Build echoue: dist\Emo-Desktop.exe introuvable"
}
Copy-Item -Force $Built (Join-Path $OutDir "Emo-Desktop.exe")
Write-Host "[build] OK -> emo\backend\agent_binaries\Emo-Desktop.exe"
Get-Item (Join-Path $OutDir "Emo-Desktop.exe") | Select-Object Name, Length, LastWriteTime
