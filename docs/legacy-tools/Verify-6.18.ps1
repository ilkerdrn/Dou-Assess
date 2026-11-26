$ErrorActionPreference='Stop'
[Console]::OutputEncoding=[System.Text.Encoding]::UTF8
$OutputEncoding=[System.Text.Encoding]::UTF8
function Fail($msg){throw "6.19 KABUL TESTİ BAŞARISIZ: $msg"}
if(-not(Test-Path '.\.env')){Fail '.env bulunamadı. Önce Start-Pilot.ps1 çalıştırın.'}
$port=8080;$line=Get-Content .env|Where-Object{$_ -match '^HTTP_PORT='}|Select-Object -First 1
if($line){$v=($line -split '=',2)[1].Trim();if($v -match '^\d+$'){$port=[int]$v}}
$base="http://localhost:$port"
Write-Host 'DOU Assess 6.19 final ürün hızlı kabul testi' -ForegroundColor Cyan
$ready=Invoke-RestMethod "$base/api/ready" -TimeoutSec 12
if($ready.status -ne 'ready'){Fail '/api/ready hazır değil'}
if($ready.database_dialect -ne 'postgresql'){Fail "PostgreSQL bekleniyordu: $($ready.database_dialect)"}
if($ready.version -notlike '*6.19*'){Fail "6.19 sürümü bekleniyordu: $($ready.version)"}
if($ready.schema_revision -ne '0018_classic_assessment_standard'){Fail "0018 schema bekleniyordu: $($ready.schema_revision)"}
Write-Host "[PASS] API + PostgreSQL + schema 0018 + sürüm: $($ready.version)" -ForegroundColor Green

$cfg=Invoke-RestMethod "$base/api/auth/config" -TimeoutSec 10
if($cfg.auth_required -ne $false){Fail 'Pilot pakette AUTH_REQUIRED=false bekleniyordu'}
Write-Host '[PASS] Pilot kimlik modu hazır' -ForegroundColor Green

$web=Invoke-WebRequest -UseBasicParsing -Uri "$base/api/health" -TimeoutSec 10
foreach($h in @('X-Content-Type-Options','X-Frame-Options','Referrer-Policy','Permissions-Policy','Cross-Origin-Opener-Policy','Cross-Origin-Resource-Policy')){if(-not $web.Headers[$h]){Fail "Güvenlik başlığı eksik: $h"}}
$html=(Invoke-WebRequest -UseBasicParsing -Uri "$base/" -TimeoutSec 10).Content
foreach($token in @(
 'id="loginGate"','id="bankFilterProgram"','Akademik Ölçme Merkezi · 6.19','Akademik Yapı','Sınav Yönetimi','Analiz & Akreditasyon','ÖÇ / PÇ Merkezi','Sınav Merkezi','Optik & Kontrol','Puanlama',
 'id="commandPalette"','id="outcomeCenterKpis"','id="examCenterKpis"','id="examWorkspaceSummary"','id="examDraftForm"','id="draftBookletCount"','id="duplicateExam"',
 'id="courseCreateForm"','id="studentCreateForm"','id="programCreateForm"','id="bankOutcomePicker"','id="qOutcomePicker"','id="analyticsStudentDrawer"','id="academicWorkbookFile"','id="academicTemplateDownload"','SINAV ANALİZ MERKEZİ','EXCEL İLE TOPLU KURULUM'
)){if($html -notmatch [regex]::Escape($token)){Fail "UI kontratı eksik: $token"}}
if($html -match 'onclick=' -or $html -match 'onsubmit='){Fail 'CSP ile uyumsuz inline event handler bulundu'}
$css=(Invoke-WebRequest -UseBasicParsing -Uri "$base/styles.css?v=6.19-final" -TimeoutSec 10).Content
foreach($token in @('.final-nav','.exam-center-hero','.exam-center-layout','.exam-detail-strip','.workspace-metrics','.outcome-center-hero','.outcome-center-kpis','.command-overlay','.academic-data-layout','.scan-review-workbench','.analytics-sticky-tabs','.distribution-chart','.analytics-drawer','.academic-bulk-import','.question-analysis-grid')){if($css -notmatch [regex]::Escape($token)){Fail "CSS kontratı eksik: $token"}}
$js=(Invoke-WebRequest -UseBasicParsing -Uri "$base/app.js?v=6.19-final" -TimeoutSec 10).Content
foreach($token in @('workspace-summary','goExamNextAction','openCommandPalette','learning_outcome_codes','questionOutcomeCodes','/duplicate','draftBookletCount','renderExamWorkspaceSummary','DELEGATED_ACTIONS','data-action-call=','score_distribution','renderAnalyticsStudents','academic-workbook','openAnalyticsStudent')){if($js -notmatch [regex]::Escape($token)){Fail "JS kontratı eksik: $token"}}
if($js -match 'onclick=' -or $js -match 'onsubmit='){Fail 'JS içinde CSP uyumsuz inline event handler bulundu'}
Write-Host '[PASS] Final UI/UX + CSP güvenli etkileşim kontratı' -ForegroundColor Green

$openapi=(Invoke-WebRequest -UseBasicParsing -Uri "$base/openapi.json" -TimeoutSec 10).Content
foreach($token in @('/api/question-bank','/api/import/academic-workbook/template','/api/import/academic-workbook/validate','/api/import/academic-workbook','/api/exams/{exam_id}/students/{exam_student_id}/analytics','/api/pilot/readiness','/api/pilot/uat/run','/api/quality/dashboard.xlsx','/representatives/freeze-all','/api/scan-items/{item_id}/review-preview','preview_url','raw_preview_url','/report.xlsx','/api/exams/{exam_id}/workspace-summary','/api/exams/{exam_id}/duplicate','/api/courses/{course_id}/outcome-summary','/api/learning-outcomes/{outcome_id}','/api/program-outcomes/{outcome_id}','/api/exams/{exam_id}/scans-batch','/api/exams/{exam_id}/students/{student_id}/classic-scans','/api/scan-items/{item_id}/classic-crop/{question_id}','/api/quality/dashboard','/api/accreditation/periods/{period_id}/report.xlsx')){if($openapi -notmatch [regex]::Escape($token)){Fail "API kontratı eksik: $token"}}
Write-Host '[PASS] Final backend API kontratı' -ForegroundColor Green

$pilotUsers=@(Invoke-RestMethod "$base/api/auth/pilot-users" -TimeoutSec 10)
$admin=$pilotUsers|Where-Object{$_.role_names -contains 'admin'}|Select-Object -First 1
if(-not $admin){Fail 'Pilot admin kullanıcı bulunamadı'}
$headers=@{'X-DOU-Pilot-User'=$admin.email}
$diag=Invoke-RestMethod "$base/api/system/diagnostics" -Headers $headers -TimeoutSec 10
if($diag.security.expected_schema_revision -ne '0018_classic_assessment_standard'){Fail 'Diagnostics beklenen schema 0018 değil'}
if([int]$diag.security.db_statement_timeout_ms -le 0){Fail 'DB statement timeout kapalı'}
Write-Host '[PASS] Security diagnostics + schema contract' -ForegroundColor Green

Write-Host ''
Write-Host 'TÜM 6.19 HIZLI KABUL TESTLERİ BAŞARILI' -ForegroundColor Green
Write-Host 'Sonraki: .\Security-Smoke-6.19.ps1 ve .\Verify-Pilot.ps1' -ForegroundColor Cyan
