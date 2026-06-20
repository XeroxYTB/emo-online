# Demarre Spouleur + services Canon — necessite admin
# Usage: clic droit > Executer en tant qu'administrateur

$ErrorActionPreference = 'Stop'

Write-Host "=== Reparation impression (Spouleur + Canon) ===" -ForegroundColor Cyan

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "Elevation requise..." -ForegroundColor Yellow
    Start-Process powershell -Verb RunAs -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Wait
    exit $LASTEXITCODE
}

function Start-CanonServices {
    $canon = Get-Service -ErrorAction SilentlyContinue | Where-Object {
        $_.DisplayName -match 'Canon|CNM|ijplm|MB2700' -or $_.Name -match 'Canon|CNM|IJPLM'
    }
    foreach ($s in $canon) {
        if ($s.StartType -eq 'Disabled') {
            Set-Service $s.Name -StartupType Automatic -ErrorAction SilentlyContinue
        }
        if ($s.Status -ne 'Running') {
            Write-Host "Demarrage: $($s.DisplayName)..." -ForegroundColor Yellow
            Start-Service $s.Name -ErrorAction SilentlyContinue
        }
        $after = Get-Service $s.Name
        Write-Host "  $($after.DisplayName): $($after.Status)" -ForegroundColor $(if ($after.Status -eq 'Running') { 'Green' } else { 'Red' })
    }
}

# Jobs retenus (souvent apres panne service Canon)
$canonPrinter = Get-Printer -ErrorAction SilentlyContinue | Where-Object { $_.Name -match 'Canon' -and $_.PrinterStatus -eq 'Normal' } | Select-Object -First 1
if ($canonPrinter) {
    Get-PrintJob -PrinterName $canonPrinter.Name -ErrorAction SilentlyContinue | ForEach-Object {
        Write-Host "Job retenu detecte: $($_.DocumentName)" -ForegroundColor Yellow
        Remove-PrintJob -PrinterName $canonPrinter.Name -ID $_.Id -ErrorAction SilentlyContinue
    }
}

Start-CanonServices

# Nettoyage file spooler bloquee
$spoolDir = "$env:SystemRoot\System32\spool\PRINTERS"
Get-ChildItem $spoolDir -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue

Set-Service Spooler -StartupType Automatic
Restart-Service Spooler -Force
Start-Sleep 2

$svc = Get-Service Spooler
Write-Host "Spooler: $($svc.Status)" -ForegroundColor $(if ($svc.Status -eq 'Running') { 'Green' } else { 'Red' })

if ($svc.Status -eq 'Running') {
    Get-Printer | Where-Object { $_.Name -notmatch 'Fax|OneNote|XPS|PDF' } | Select-Object Name, PrinterStatus | Format-Table -AutoSize
    Write-Host "Impression OK — relancez le document si besoin." -ForegroundColor Green
} else {
    Write-Host "Echec Spooler. Verifiez USB Canon + redemarrez le PC." -ForegroundColor Red
    exit 1
}
