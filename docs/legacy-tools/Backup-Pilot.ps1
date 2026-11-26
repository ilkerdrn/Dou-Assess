param(
  [string]$ComposeFile='docker-compose.yml',
  [string]$EnvFile='.env'
)
$ErrorActionPreference = 'Stop'
if (-not (Test-Path $EnvFile)) { throw "$EnvFile bulunamadi." }
if (-not (Test-Path $ComposeFile)) { throw "$ComposeFile bulunamadi." }
$dc=@('compose','--env-file',$EnvFile,'-f',$ComposeFile)
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$dir = Join-Path (Get-Location) "backups\DOU-Assess-$stamp"
New-Item -ItemType Directory -Force -Path $dir | Out-Null

Write-Host "PostgreSQL backup aliniyor..." -ForegroundColor Yellow
& docker @dc exec -T db sh -lc 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc -f /tmp/dou_assess.dump'
if ($LASTEXITCODE -ne 0) { throw 'pg_dump basarisiz.' }
& docker @dc cp db:/tmp/dou_assess.dump "$dir\database.dump"
if ($LASTEXITCODE -ne 0) { throw 'Database dump hosta kopyalanamadi.' }

Write-Host "Kanit/tarama/operasyon dosyalari backup aliniyor..." -ForegroundColor Yellow
& docker @dc exec -T api sh -lc 'tar -czf /tmp/dou_storage.tar.gz -C /app/data evidence scans ops'
if ($LASTEXITCODE -ne 0) { throw 'storage tar basarisiz.' }
& docker @dc cp api:/tmp/dou_storage.tar.gz "$dir\storage.tar.gz"
if ($LASTEXITCODE -ne 0) { throw 'Storage arsivi hosta kopyalanamadi.' }

$dbHash=(Get-FileHash "$dir\database.dump" -Algorithm SHA256).Hash.ToLower()
$storageHash=(Get-FileHash "$dir\storage.tar.gz" -Algorithm SHA256).Hash.ToLower()
$created=(Get-Date).ToUniversalTime().ToString('o')
$schema=((& docker @dc exec -T api alembic current) | Out-String).Trim()
$manifest = @{
  version='6.19'; created_at=$created; schema_revision=$schema;
  database='database.dump'; storage='storage.tar.gz';
  database_sha256=$dbHash; storage_sha256=$storageHash
} | ConvertTo-Json
Set-Content -Path "$dir\manifest.json" -Value $manifest -Encoding UTF8
$zip = "$dir.zip"
Compress-Archive -Path "$dir\*" -DestinationPath $zip -Force
$zipHash=(Get-FileHash $zip -Algorithm SHA256).Hash.ToLower()

$statusPath=Join-Path $env:TEMP 'dou-assess-backup-status.json'
@{created_at=$created; backup_zip=(Split-Path $zip -Leaf); sha256=$zipHash; database_sha256=$dbHash; storage_sha256=$storageHash; schema_revision=$schema; status='success'} | ConvertTo-Json | Set-Content -Path $statusPath -Encoding UTF8
& docker @dc exec -T api sh -lc 'mkdir -p /app/data/ops'
& docker @dc cp $statusPath api:/app/data/ops/backup-status.json
Remove-Item $statusPath -Force -ErrorAction SilentlyContinue
Write-Host "Backup hazir: $zip" -ForegroundColor Green
Write-Host "SHA256: $zipHash" -ForegroundColor DarkGray
Write-Output $zip
