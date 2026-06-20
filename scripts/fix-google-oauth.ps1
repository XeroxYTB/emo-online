# Ajoute les origines JavaScript requises pour Google Sign-In sur xeroxytb.com
$clientId = "791552572109-va37rj7pooi3opca3bqe61h15ka8gob9.apps.googleusercontent.com"

Write-Host ""
Write-Host "=== Google OAuth — origin_mismatch ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Dans Google Cloud Console, client OAuth :" -ForegroundColor Yellow
Write-Host "  $clientId"
Write-Host ""
Write-Host "Section « Origines JavaScript autorisees », ajoute EXACTEMENT :" -ForegroundColor Green
Write-Host "  https://xeroxytb.com"
Write-Host "  https://www.xeroxytb.com"
Write-Host ""
Write-Host "Enregistre, attends 1-2 min, puis Ctrl+F5 sur xeroxytb.com/login"
Write-Host ""
Start-Process "https://console.cloud.google.com/apis/credentials"
