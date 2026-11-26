$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

Write-Host ''
Write-Host 'DOU Assess · Local Pilot UAT 1-9' -ForegroundColor Cyan
Write-Host 'Kapsam: UI/auth, ders/ogrenci/OC-PC, soru bankasi, Vize/Final, OMR, analiz, MEDEK/evidence, OBS Excel.'
Write-Host 'Not: Kurumsal production entegrasyonlari (adim 10) bu testin disindadir.' -ForegroundColor Yellow
Write-Host ''

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw 'Docker komutu bulunamadi. Docker Desktop kurulu ve acik olmalidir.'
}

if (-not (Test-Path '.env')) {
    if (Test-Path '.env.pilot') { Copy-Item '.env.pilot' '.env' }
    else { throw '.env veya .env.pilot bulunamadi.' }
}

$ready = $false
try {
    $r = Invoke-WebRequest -UseBasicParsing -Uri 'http://localhost:8080/api/ready' -TimeoutSec 5
    if ($r.StatusCode -eq 200) { $ready = $true }
} catch {}
if (-not $ready) {
    Write-Host 'Pilot servis calismiyor; Start-Pilot.ps1 cagriliyor...' -ForegroundColor Yellow
    powershell -ExecutionPolicy Bypass -File .\Start-Pilot.ps1
}

$cid = (docker compose --env-file .env ps -q api).Trim()
if (-not $cid) { throw 'API container bulunamadi.' }

$out = Join-Path $Root 'UAT-1-9-Outputs'
if (Test-Path $out) { Remove-Item $out -Recurse -Force }
New-Item -ItemType Directory -Path $out | Out-Null

Write-Host '1-9 kabul senaryosu calistiriliyor...' -ForegroundColor Cyan
docker exec $cid sh -lc 'rm -rf /tmp/dou-uat-1-9 && mkdir -p /tmp/dou-uat-1-9 && DOU_UAT_OUTPUT=/tmp/dou-uat-1-9 python tests/acceptance/validate_pilot_1_9.py'
if ($LASTEXITCODE -ne 0) { throw 'UAT senaryosu basarisiz oldu.' }

docker cp "${cid}:/tmp/dou-uat-1-9/." $out | Out-Null

Write-Host ''
Write-Host 'UAT 1-9 TAMAMLANDI.' -ForegroundColor Green
Write-Host "Ciktilar: $out" -ForegroundColor Green
Write-Host 'Rapor: UAT-1-9-Outputs\UAT-1-9-REPORT.md'
Write-Host ''
