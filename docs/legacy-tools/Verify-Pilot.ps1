$ErrorActionPreference = 'Stop'

function Fail($msg) { throw "PILOT KABUL TESTI BASARISIZ: $msg" }

function Api($method, $path, $body=$null, $headers=$null) {
    $uri = "$script:Base$path"
    try {
        $args = @{
            Uri = $uri
            Method = $method
            ContentType = 'application/json'
            TimeoutSec = 25
        }
        if ($headers) { $args['Headers'] = $headers }
        if ($null -ne $body) { $args['Body'] = ($body | ConvertTo-Json -Depth 16) }
        return Invoke-RestMethod @args
    } catch {
        Write-Host "HTTP hata: $method $uri" -ForegroundColor Red
        if ($_.ErrorDetails.Message) { Write-Host $_.ErrorDetails.Message -ForegroundColor Red }
        throw
    }
}

function ExpectHttp($expected, $method, $path, $body=$null, $headers=$null) {
    $uri = "$script:Base$path"
    try {
        $args = @{
            Uri = $uri
            Method = $method
            ContentType = 'application/json'
            TimeoutSec = 25
        }
        if ($headers) { $args['Headers'] = $headers }
        if ($null -ne $body) { $args['Body'] = ($body | ConvertTo-Json -Depth 16) }
        Invoke-RestMethod @args | Out-Null
        if ($expected -ge 400) { Fail "$method $path icin HTTP $expected bekleniyordu fakat istek basarili oldu" }
        return
    } catch {
        $status = $null
        if ($_.Exception.Response -and $_.Exception.Response.StatusCode) { $status = [int]$_.Exception.Response.StatusCode }
        if ($status -ne $expected) {
            if ($_.ErrorDetails.Message) { Write-Host $_.ErrorDetails.Message -ForegroundColor Red }
            Fail "$method $path icin HTTP $expected bekleniyordu, gelen: $status"
        }
    }
}

if (-not (Test-Path '.\.env')) { Fail '.env bulunamadi' }
$port = 8080
$line = Get-Content .env | Where-Object { $_ -match '^HTTP_PORT=' } | Select-Object -First 1
if ($line) { $v = ($line -split '=',2)[1].Trim(); if ($v -match '^\d+$') { $port = [int]$v } }
$script:Base = "http://localhost:$port"
$stamp = Get-Date -Format 'yyyyMMddHHmmss'

Write-Host 'DOU Assess 6.19 gercek Docker/PostgreSQL/Identity/RBAC kabul testi' -ForegroundColor Cyan

$ready = Api GET '/api/ready'
if ($ready.status -ne 'ready') { Fail 'ready endpoint basarisiz' }
if ($ready.database_dialect -ne 'postgresql') { Fail "PostgreSQL bekleniyordu, gelen: $($ready.database_dialect)" }
if ($ready.version -notlike '*6.19*') { Fail "6.19 bekleniyordu, gelen: $($ready.version)" }
if ($ready.schema_revision -ne '0018_classic_assessment_standard') { Fail "0018 schema bekleniyordu: $($ready.schema_revision)" }
Write-Host "[PASS] PostgreSQL readiness + 6.19 version ($($ready.version))" -ForegroundColor Green

$config = Api GET '/api/auth/config'
if ($config.auth_required -ne $false) { Fail 'Pilot kabul testinde AUTH_REQUIRED=false bekleniyor' }
if ($config.auth_provider -ne 'pilot') { Fail "Pilot auth provider bekleniyordu: $($config.auth_provider)" }
if ($config.entra.mode -ne 'single-tenant-v2-access-token') { Fail 'Entra v2 access-token modu raporlanmadi' }
$adminMe = Api GET '/api/auth/me'
if (-not (@($adminMe.role_names) -contains 'admin')) { Fail 'Varsayilan pilot admin kimligi aktif degil' }
Write-Host '[PASS] Pilot identity + Entra-ready auth config' -ForegroundColor Green

$periodBootstrap = @(Api POST '/api/academic-periods/bootstrap' @{})
$periods = @(Api GET '/api/academic-periods')
$pilotStatus = Api GET '/api/pilot/status'
if ($pilotStatus.version -notlike '*6.19*') { Fail 'Kurumsal pilot durum endpointi 6.19 raporlamiyor' }
$syncRuns = @(Api GET '/api/integrations/sync-runs')
Write-Host "[PASS] Academic periods + pilot status + integration history ($($periods.Count) dönem / $($syncRuns.Count) sync)" -ForegroundColor Green
$qualityDash = Api GET '/api/quality/dashboard'
if ($null -eq $qualityDash.summary -or $null -eq $qualityDash.programs) { Fail 'Yönetim & Kalite dashboard endpointi yanıt vermedi' }
Write-Host '[PASS] Yönetim & Kalite dashboard erişimi' -ForegroundColor Green

# Dedicated RBAC scope. Existing pilot data is untouched.
$programA = Api POST '/api/programs' @{ code="R617A-$stamp"; name="6.19 Yetki Program A $stamp"; faculty='Meslek Yuksekokulu'; department='Bilgisayar Teknolojileri' }
$programB = Api POST '/api/programs' @{ code="R617B-$stamp"; name="6.19 Yetki Program B $stamp"; faculty='Meslek Yuksekokulu'; department='Elektronik' }
if (-not $programA.id -or -not $programB.id) { Fail 'RBAC programlari olusmadi' }

$instMail = "verify613-inst-$stamp@local"
$headMail = "verify613-head-$stamp@local"
$qualityMail = "verify613-quality-$stamp@local"

$courseA = Api POST '/api/courses' @{ program_id=$programA.id; code="R617C1-$stamp"; name='6.19 Yetki Dersi A'; academic_year='2035-2036'; term='Guz'; instructor_email=$instMail; instructor_name='6.19 Yetkili Ogretim Elemani' }
$courseB = Api POST '/api/courses' @{ program_id=$programB.id; code="R617C2-$stamp"; name='6.19 Yetki Dersi B'; academic_year='2035-2036'; term='Guz'; instructor_email='other617@local'; instructor_name='Diger Ogretim Elemani' }
if (-not $courseA.id -or -not $courseB.id) { Fail 'RBAC dersleri olusmadi' }

$inst = Api POST '/api/users' @{ email=$instMail; display_name='6.19 Instructor Test'; auth_source='pilot'; is_active=$true }
$head = Api POST '/api/users' @{ email=$headMail; display_name='6.19 Program Head Test'; auth_source='pilot'; is_active=$true }
$quality = Api POST '/api/users' @{ email=$qualityMail; display_name='6.19 Quality Test'; auth_source='pilot'; is_active=$true }
if (-not $inst.id -or -not $head.id -or -not $quality.id) { Fail 'Test kullanicilari olusmadi' }

$instRole = Api POST "/api/users/$($inst.id)/roles" @{ role='instructor'; course_id=$courseA.id }
$headRole = Api POST "/api/users/$($head.id)/roles" @{ role='program_head'; program_id=$programA.id }
$qualityRole = Api POST "/api/users/$($quality.id)/roles" @{ role='quality' }
if (-not $instRole.id -or -not $headRole.id -or -not $qualityRole.id) { Fail 'Rol atamalari olusmadi' }
Write-Host '[PASS] User creation + scoped role assignments' -ForegroundColor Green

$hi = @{ 'X-DOU-Pilot-User' = $instMail }
$hh = @{ 'X-DOU-Pilot-User' = $headMail }
$hq = @{ 'X-DOU-Pilot-User' = $qualityMail }

$instMe = Api GET '/api/auth/me' $null $hi
if (-not (@($instMe.role_names) -contains 'instructor')) { Fail 'Instructor kimlik baglami olusmadi' }
$instCourses = @(Api GET '/api/courses' $null $hi)
$instCourseIds = @($instCourses | ForEach-Object { [int]$_.id })
if (-not ($instCourseIds -contains [int]$courseA.id)) { Fail 'Instructor kendi dersini goremiyor' }
if ($instCourseIds -contains [int]$courseB.id) { Fail 'Instructor yetkisiz dersi goruyor' }
ExpectHttp 403 PATCH "/api/courses/$($courseA.id)" @{ name='Yetkisiz akademik degisiklik' } $hi
ExpectHttp 403 GET '/api/users' $null $hi
Write-Host '[PASS] Instructor read scope + academic master protection' -ForegroundColor Green

$exam = Api POST '/api/exams' @{ course_id=$courseA.id; title="6.19 RBAC Sinavi $stamp"; exam_type='Quiz'; exam_date=(Get-Date).AddDays(20).ToString('yyyy-MM-dd'); duration_minutes=30; instructions=''; sync_students=$false } $hi
if (-not $exam.id) { Fail 'Instructor kendi dersinde sinav olusturamadi' }
ExpectHttp 403 POST '/api/exams' @{ course_id=$courseB.id; title='Yasak Sinav'; exam_type='Quiz'; exam_date=(Get-Date).AddDays(20).ToString('yyyy-MM-dd'); duration_minutes=30; instructions=''; sync_students=$false } $hi
Write-Host '[PASS] Instructor own-course exam write + cross-course deny' -ForegroundColor Green

$headPrograms = @(Api GET '/api/programs' $null $hh)
$headProgramIds = @($headPrograms | ForEach-Object { [int]$_.id })
if (-not ($headProgramIds -contains [int]$programA.id)) { Fail 'Program baskani kendi programini goremiyor' }
if ($headProgramIds -contains [int]$programB.id) { Fail 'Program baskani yetkisiz programi goruyor' }
$headPatch = Api PATCH "/api/courses/$($courseA.id)" @{ name='6.19 Yetki Dersi A - Baskan Onayli' } $hh
if ($headPatch.name -notlike '*Baskan Onayli') { Fail 'Program baskani kendi dersini yonetemedi' }
ExpectHttp 403 PATCH "/api/courses/$($courseB.id)" @{ name='Yasak Degisiklik' } $hh
Write-Host '[PASS] Program head scoped management' -ForegroundColor Green

$qualityCourses = @(Api GET '/api/courses' $null $hq)
if (@($qualityCourses).Count -lt 2) { Fail 'Kalite rolu global akademik gorunurluk alamadi' }
ExpectHttp 403 PATCH "/api/exams/$($exam.id)" @{ title='Kalite sinav icerigini degistirmemeli' } $hq
$profile = Api POST '/api/accreditation/profiles' @{ code="Q617-$stamp"; name='6.19 Kalite Profil Testi'; version='1'; required_general_evidence_kinds=@(); required_representative_evidence_kinds=@(); requires_representatives=$false; requires_improvement_for_gaps=$false } $hq
if (-not $profile.id) { Fail 'Kalite rolu akreditasyon profili olusturamadi' }
Write-Host '[PASS] Quality global read + accreditation write + exam-content deny' -ForegroundColor Green

$logs = @(Api GET '/api/audit-logs?limit=500' $null $hq)
$actorLog = $logs | Where-Object { $_.actor_email -eq $instMail -and $_.entity_type -eq 'exam' -and $_.action -eq 'create' } | Select-Object -First 1
if (-not $actorLog) { Fail 'Audit log instructor actor_email kaydi bulunamadi' }
if (-not (@($actorLog.actor_roles) -contains 'instructor')) { Fail 'Audit log actor_roles instructor icermiyor' }
Write-Host '[PASS] Audit actor identity + role snapshot' -ForegroundColor Green

$users = @(Api GET '/api/users')
$gotInst = $users | Where-Object { $_.email -eq $instMail } | Select-Object -First 1
if (-not $gotInst) { Fail 'Admin kullanici listesinden test instructor bulunamadi' }
Write-Host '[PASS] Admin user administration' -ForegroundColor Green

Write-Host 'API container restart ile identity/role kaliciligi kontrolu...' -ForegroundColor Yellow
docker compose --env-file .env restart api | Out-Null
if ($LASTEXITCODE -ne 0) { Fail 'API restart komutu basarisiz' }
$containerId = (& docker compose --env-file .env ps -q api).Trim()
if (-not $containerId) { Fail 'API container ID bulunamadi' }
$healthy = $false
for ($i=0; $i -lt 60; $i++) {
    Start-Sleep -Seconds 2
    $health = (& docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' $containerId 2>$null).Trim()
    if ($health -eq 'healthy') { $healthy = $true; break }
}
if (-not $healthy) {
    docker compose --env-file .env logs api --tail=160
    Fail 'API restart sonrasi Docker health=healthy olmadi'
}
$apiReady = $false
for ($i=0; $i -lt 20; $i++) {
    Start-Sleep -Seconds 1
    try {
        $rr = Invoke-RestMethod "$script:Base/api/ready" -TimeoutSec 3
        if ($rr.status -eq 'ready' -and $rr.version -like '*6.19*') { $apiReady=$true; break }
    } catch {}
}
if (-not $apiReady) { Fail 'API restart sonrasi /api/ready olmadi' }
$instAgain = Api GET '/api/auth/me' $null $hi
if ($instAgain.email -ne $instMail -or -not (@($instAgain.role_names) -contains 'instructor')) { Fail 'Restart sonrasi identity/role kaybi var' }
$examAgain = Api GET "/api/exams/$($exam.id)" $null $hi
if ($examAgain.id -ne $exam.id) { Fail 'Restart sonrasi instructor sinav erisimi kayboldu' }
Write-Host '[PASS] PostgreSQL identity/RBAC restart persistence' -ForegroundColor Green

Write-Host '6.19 güvenlik smoke testi...' -ForegroundColor Yellow
powershell -ExecutionPolicy Bypass -File .\Security-Smoke-6.19.ps1
if ($LASTEXITCODE -ne 0) { Fail 'Security-Smoke-6.19 başarısız' }

Write-Host ''
Write-Host 'TUM 6.19 PILOT KABUL TESTLERI BASARILI' -ForegroundColor Green
Write-Host 'Gercek PostgreSQL + Docker + scoped RBAC + audit actor + restart zinciri dogrulandi.' -ForegroundColor Green
Write-Host "Test exam id: $($exam.id)"
