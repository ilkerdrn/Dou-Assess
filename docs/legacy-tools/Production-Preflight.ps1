param([string]$EnvFile = '.env.production')
$ErrorActionPreference='Stop'
function Fail($msg){throw "PRODUCTION PREFLIGHT BASARISIZ: $msg"}
if(-not(Test-Path $EnvFile)){Fail "$EnvFile bulunamadi. .env.production.example dosyasini kopyalayip Bilgi Islem degerleriyle doldurun."}
if(-not(Test-Path '.\docker-compose.production.yml')){Fail 'docker-compose.production.yml bulunamadi'}
if(-not(Test-Path '.\secrets\postgres_password.txt')){Fail 'secrets\postgres_password.txt bulunamadi'}
$secret=(Get-Content '.\secrets\postgres_password.txt' -Raw).Trim()
if($secret.Length -lt 24){Fail 'PostgreSQL production parolasi en az 24 karakter olmali'}
$content=Get-Content $EnvFile -Raw
if($content -match 'CHANGE_ME'){Fail 'Production env icinde CHANGE_ME placeholder kalmis'}
$required=@('PUBLIC_HOSTNAME','ALLOWED_HOSTS','TRUSTED_PROXY_CIDRS','ENTRA_TENANT_ID','ENTRA_CLIENT_ID','ENTRA_AUDIENCE','ENTRA_ALLOWED_CLIENT_IDS','ENTRA_REQUIRED_SCOPES','ENTRA_LOGIN_SCOPES','ENTRA_REDIRECT_URI','MAX_BATCH_UPLOAD_MB','MAX_REQUEST_MB','MAX_PDF_PAGES','MAX_IMAGE_MEGAPIXELS','DB_POOL_SIZE','DB_STATEMENT_TIMEOUT_MS')
foreach($k in $required){if($content -notmatch "(?m)^$k=.+$"){Fail "$k eksik"}}
function EnvInt($name){$m=[regex]::Match($content,"(?m)^$name=(\d+)\s*$");if(-not $m.Success){Fail "$name sayisal degil"};return [int]$m.Groups[1].Value}
$single=EnvInt 'MAX_UPLOAD_MB';$batch=EnvInt 'MAX_BATCH_UPLOAD_MB';$request=EnvInt 'MAX_REQUEST_MB'
if($batch -lt $single){Fail 'MAX_BATCH_UPLOAD_MB >= MAX_UPLOAD_MB olmali'}
if($request -lt $batch){Fail 'MAX_REQUEST_MB >= MAX_BATCH_UPLOAD_MB olmali'}
if($request -gt 64){Fail 'MAX_REQUEST_MB en fazla 64 olmali; production NGINX client_max_body_size 64m ile sinirli'}
& docker compose --env-file $EnvFile -f docker-compose.production.yml config --quiet
if($LASTEXITCODE -ne 0){Fail 'Production compose config gecersiz'}
$compose=Get-Content '.\docker-compose.production.yml' -Raw
if($compose -match '--forwarded-allow-ips'){Fail 'Uvicorn forwarded-allow-ips production ortamında kullanılmamalı; güvenilir proxy kontrolü uygulama katmanında yapılır'}
foreach($token in @('read_only: true','no-new-privileges:true','cap_drop:','RATE_LIMIT_ENABLED: "true"','--workers", "2"','--no-proxy-headers','scan_data:/app/data/scans')){if($compose -notmatch [regex]::Escape($token)){Fail "Container hardening kontrati eksik: $token"}}
$nginx=Get-Content '.\nginx\production.conf' -Raw
foreach($token in @('limit_req_status 429','client_max_body_size 64m','limit_conn_status 429')){if($nginx -notmatch [regex]::Escape($token)){Fail "NGINX hardening eksik: $token"}}
Write-Host 'PRODUCTION PREFLIGHT BASARILI' -ForegroundColor Green
Write-Host 'Not: Entra app registration, TLS reverse proxy, KVKK saklama politikasi ve hedef sunucu yuk testi Bilgi Islem ile sahada dogrulanmalidir.' -ForegroundColor Yellow
