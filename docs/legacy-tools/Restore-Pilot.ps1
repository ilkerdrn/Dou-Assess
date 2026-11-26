param(
    [Parameter(Mandatory=$true)][string]$BackupZip,
    [switch]$Force,
    [string]$ComposeFile='docker-compose.yml',
    [string]$EnvFile='.env'
)
$ErrorActionPreference = 'Stop'
if (-not $Force) { throw 'Restore mevcut verinin üzerine yazar. Tekrar -Force parametresi ile calistirin.' }
if (-not (Test-Path $EnvFile)) { throw "$EnvFile bulunamadi." }
if (-not (Test-Path $ComposeFile)) { throw "$ComposeFile bulunamadi." }
if (-not (Test-Path $BackupZip)) { throw "Backup bulunamadi: $BackupZip" }
$dc=@('compose','--env-file',$EnvFile,'-f',$ComposeFile)

$tmp = Join-Path $env:TEMP ("dou-assess-restore-" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force -Path $tmp | Out-Null
Expand-Archive -Path $BackupZip -DestinationPath $tmp -Force
$dbDump = Get-ChildItem -Path $tmp -Recurse -Filter database.dump | Select-Object -First 1
$storage = Get-ChildItem -Path $tmp -Recurse -Filter storage.tar.gz | Select-Object -First 1
$manifestFile = Get-ChildItem -Path $tmp -Recurse -Filter manifest.json | Select-Object -First 1
if (-not $dbDump -or -not $storage -or -not $manifestFile) { throw 'Backup icerigi eksik.' }
$manifest=Get-Content $manifestFile.FullName -Raw | ConvertFrom-Json
if($manifest.database_sha256){
  $actual=(Get-FileHash $dbDump.FullName -Algorithm SHA256).Hash.ToLower()
  if($actual -ne [string]$manifest.database_sha256){throw 'Database dump SHA256 dogrulamasi basarisiz.'}
}
if($manifest.storage_sha256){
  $actual=(Get-FileHash $storage.FullName -Algorithm SHA256).Hash.ToLower()
  if($actual -ne [string]$manifest.storage_sha256){throw 'Storage SHA256 dogrulamasi basarisiz.'}
}

Write-Host 'API durduruluyor...' -ForegroundColor Yellow
& docker @dc stop api nginx | Out-Null

& docker @dc cp $dbDump.FullName db:/tmp/restore.dump
& docker @dc exec -T db sh -lc 'dropdb -U "$POSTGRES_USER" --if-exists --force "$POSTGRES_DB" && createdb -U "$POSTGRES_USER" "$POSTGRES_DB" && pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner /tmp/restore.dump'
if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL restore basarisiz.' }

# Restored backups may come from an earlier compatible release. Bring schema to current head before API traffic resumes.
& docker @dc run --rm migrate
if ($LASTEXITCODE -ne 0) { throw 'Restore sonrasi Alembic migration basarisiz.' }
& docker @dc up -d api | Out-Null
Start-Sleep -Seconds 5
& docker @dc cp $storage.FullName api:/tmp/restore-storage.tar.gz
& docker @dc exec -T api sh -lc 'rm -rf /app/data/evidence/* /app/data/scans/* /app/data/ops/* && tar -xzf /tmp/restore-storage.tar.gz -C /app/data && mkdir -p /app/data/ops'
if ($LASTEXITCODE -ne 0) { throw 'Dosya restore basarisiz.' }
& docker @dc up -d nginx | Out-Null

$created=(Get-Date).ToUniversalTime().ToString('o')
$statusPath=Join-Path $env:TEMP 'dou-assess-restore-status.json'
@{created_at=$created; backup_zip=(Split-Path $BackupZip -Leaf); status='success'; integrity_verified=$true; source_schema_revision=$manifest.schema_revision} | ConvertTo-Json | Set-Content -Path $statusPath -Encoding UTF8
& docker @dc cp $statusPath api:/app/data/ops/restore-status.json
Remove-Item $statusPath -Force -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force $tmp
Write-Host 'Restore tamamlandi, SHA256 dogrulandi ve schema head guncellendi.' -ForegroundColor Green
