$ErrorActionPreference = 'Stop'
if (-not (Test-Path ".\.env")) { throw ".env bulunamadi." }
docker compose --env-file .env down
if ($LASTEXITCODE -ne 0) { throw "Servisler kapatilamadi." }
Write-Host "DOU Assess kapatildi. Docker volume verileri KORUNDU." -ForegroundColor Green
