param([switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding=[System.Text.Encoding]::UTF8
$OutputEncoding=[System.Text.Encoding]::UTF8

Write-Host "DOU Assess 6.19 Final Server Ready başlatılıyor..." -ForegroundColor Cyan

if (-not (Test-Path ".\docker-compose.yml")) { throw "Bu komutu DOU Assess proje klasöründe çalıştırın." }
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw "Docker bulunamadı. Önce Docker Desktop kurup çalıştırın." }
try { docker info | Out-Null } catch { throw "Docker Desktop çalışmıyor. Docker Desktop'ı açıp tekrar deneyin." }

if (-not (Test-Path ".\.env")) {
    if (-not (Test-Path ".\.env.pilot")) { throw ".env.pilot bulunamadı." }
    Copy-Item ".\.env.pilot" ".\.env"
    $generatedDbPassword = "DouA_" + [guid]::NewGuid().ToString('N')
    (Get-Content ".\.env") -replace '^POSTGRES_PASSWORD=.*$', ("POSTGRES_PASSWORD=" + $generatedDbPassword) | Set-Content ".\.env" -Encoding UTF8
    Write-Host ".env pilot ayarlarından güvenli rastgele DB parolasıyla oluşturuldu." -ForegroundColor Yellow
}

docker compose --env-file .env config --quiet
if ($LASTEXITCODE -ne 0) { throw "docker-compose.yml veya .env geçersiz." }

docker compose --env-file .env up --build -d
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Docker Compose başlatma sırasında hata verdi. Gerçek servis durumu:" -ForegroundColor Red
    docker compose --env-file .env ps -a

    Write-Host "`n===== MIGRATION LOG =====" -ForegroundColor Cyan
    docker compose --env-file .env logs migrate --tail=160
    Write-Host "`n===== API LOG =====" -ForegroundColor Cyan
    docker compose --env-file .env logs api --tail=160
    Write-Host "`n===== NGINX LOG =====" -ForegroundColor Cyan
    docker compose --env-file .env logs nginx --tail=100

    $port = 8080
    $portLine = Get-Content .env | Where-Object { $_ -match '^HTTP_PORT=' } | Select-Object -First 1
    if ($portLine) { $candidate = ($portLine -split '=',2)[1].Trim(); if ($candidate -match '^\d+$') { $port = [int]$candidate } }
    $listener = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($listener) {
        Write-Host "`nPort $port başka bir süreç tarafından dinleniyor. PID: $($listener.OwningProcess)" -ForegroundColor Yellow
    } else {
        Write-Host "`nPort $port boş görünüyor; hata port çakışması değil. Yukarıdaki servis loguna bakın." -ForegroundColor Yellow
    }
    throw "Docker servisleri başlatılamadı. Yukarıdaki migrate/api/nginx logu gerçek nedeni gösteriyor."
}

$port = 8080
$portLine = Get-Content .env | Where-Object { $_ -match '^HTTP_PORT=' } | Select-Object -First 1
if ($portLine) { $candidate = ($portLine -split '=',2)[1].Trim(); if ($candidate -match '^\d+$') { $port = [int]$candidate } }
$base = "http://localhost:$port"

Write-Host "API ve PostgreSQL hazırlanıyor..." -ForegroundColor Yellow
$ready = $false; $r=$null
for ($i=0; $i -lt 60; $i++) {
    Start-Sleep -Seconds 2
    try { $r = Invoke-RestMethod "$base/api/ready" -TimeoutSec 3; if ($r.status -eq 'ready') { $ready = $true; break } } catch {}
}
if ($ready -and $r.schema_revision -ne '0018_classic_assessment_standard') { $ready=$false; Write-Host "Beklenmeyen schema: $($r.schema_revision)" -ForegroundColor Red }
if (-not $ready) {
    docker compose --env-file .env ps
    docker compose --env-file .env logs migrate --tail=120
    docker compose --env-file .env logs api --tail=160
    throw "API hazır duruma gelmedi."
}

Write-Host ""
Write-Host "DOU ASSESS 6.19 FINAL SERVER READY HAZIR" -ForegroundColor Green
Write-Host "Adres : $base"
Write-Host "DB    : $($r.database_dialect)"
Write-Host "Sürüm : $($r.version)"
Write-Host "Schema: $($r.schema_revision)"
Write-Host ""
Write-Host "Giriş ekranında pilot kullanıcı seçerek sisteme girebilirsiniz." -ForegroundColor Cyan
Write-Host "Doğrulama: powershell -ExecutionPolicy Bypass -File .\Verify-6.19.ps1" -ForegroundColor Cyan
if (-not $NoBrowser) { Start-Process $base }
