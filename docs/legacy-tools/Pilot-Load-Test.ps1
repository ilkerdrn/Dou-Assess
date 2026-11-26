param(
  [int]$Requests = 500,
  [int]$Concurrency = 20,
  [double]$MaxP95Ms = 1500,
  [double]$MaxErrorPercent = 1.0,
  [string]$BaseUrl = '',
  [string]$AccessToken = ''
)
$ErrorActionPreference='Stop'
if($Requests -lt 20){throw 'Requests en az 20 olmalı.'}
if($Concurrency -lt 1 -or $Concurrency -gt 50){throw 'Concurrency 1-50 arasında olmalı.'}
if(-not $BaseUrl){
  $port=8080
  if(Test-Path '.\.env'){
    $line=Get-Content .env|Where-Object{$_ -match '^HTTP_PORT='}|Select-Object -First 1
    if($line){$v=($line -split '=',2)[1].Trim();if($v -match '^\d+$'){$port=[int]$v}}
  }
  $BaseUrl="http://localhost:$port"
}
$BaseUrl=$BaseUrl.TrimEnd('/')
$cfg=Invoke-RestMethod "$BaseUrl/api/auth/config" -TimeoutSec 10
$headers=@{}
if($cfg.auth_required){
  if([string]::IsNullOrWhiteSpace($AccessToken)){throw 'AUTH_REQUIRED=true. Production yük testi için -AccessToken <Entra access token> verin.'}
  $headers['Authorization']='Bearer '+$AccessToken.Trim()
}else{
  $users=@(Invoke-RestMethod "$BaseUrl/api/auth/pilot-users" -TimeoutSec 10)
  $admin=$users|Where-Object{ $_.role_names -contains 'admin' }|Select-Object -First 1
  if($admin){$headers['X-DOU-Pilot-User']=$admin.email}
}

Write-Host "DOU Assess 6.19 yük testi: $Requests istek / concurrency $Concurrency" -ForegroundColor Cyan
Write-Host "Hedef: $BaseUrl" -ForegroundColor DarkGray
$paths=@('/api/ready','/api/dashboard','/api/pilot/status','/api/pilot/readiness','/api/pilot/performance')

# Windows PowerShell 5.1 ile uyumlu gerçek async HttpClient kuyruğu.
# Start-Job veya Task.Run içindeki PowerShell scriptblock'larına bağlı değildir.
$handler=New-Object System.Net.Http.HttpClientHandler
$client=New-Object System.Net.Http.HttpClient($handler)
$client.Timeout=[TimeSpan]::FromSeconds(20)
foreach($kv in $headers.GetEnumerator()){$null=$client.DefaultRequestHeaders.TryAddWithoutValidation([string]$kv.Key,[string]$kv.Value)}
$null=$client.DefaultRequestHeaders.TryAddWithoutValidation('User-Agent','DOU-Assess-LoadTest/6.19')

$pending=New-Object System.Collections.ArrayList
$results=New-Object System.Collections.ArrayList
$freq=[double][System.Diagnostics.Stopwatch]::Frequency

function Complete-One([System.Collections.ArrayList]$Queue,[System.Collections.ArrayList]$Output,[System.Net.Http.HttpClient]$Http){
  if($Queue.Count -eq 0){return}
  $taskArray=@($Queue|ForEach-Object{$_.task})
  $done=[System.Threading.Tasks.Task]::WhenAny($taskArray).GetAwaiter().GetResult()
  $idx=-1
  for($j=0;$j -lt $Queue.Count;$j++){if([object]::ReferenceEquals($Queue[$j].task,$done)){$idx=$j;break}}
  if($idx -lt 0){throw 'Async yük testi task eşleşmesi bulunamadı.'}
  $item=$Queue[$idx];$Queue.RemoveAt($idx)
  $elapsed=(([System.Diagnostics.Stopwatch]::GetTimestamp()-[long]$item.started)/$freq)*1000.0
  $status=0;$ok=$false
  try{
    $resp=$done.GetAwaiter().GetResult()
    $status=[int]$resp.StatusCode
    $ok=($status -ge 200 -and $status -lt 400)
    $resp.Dispose()
  }catch{
    $status=0;$ok=$false
  }
  [void]$Output.Add([pscustomobject]@{ok=$ok;status=$status;ms=$elapsed;path=$item.path})
}

try{
  for($i=0;$i -lt $Requests;$i++){
    while($pending.Count -ge $Concurrency){Complete-One $pending $results $client}
    $path=$paths[$i % $paths.Count]
    $task=$client.GetAsync($BaseUrl+$path)
    [void]$pending.Add([pscustomobject]@{task=$task;started=[System.Diagnostics.Stopwatch]::GetTimestamp();path=$path})
  }
  while($pending.Count -gt 0){Complete-One $pending $results $client}
}finally{
  $client.Dispose();$handler.Dispose()
}

$arr=@($results);$ok=@($arr|Where-Object ok);$fail=@($arr|Where-Object{-not $_.ok});$times=@($ok|ForEach-Object ms|Sort-Object)
function Percentile($Values,[double]$P){if(-not $Values.Count){return 0};$i=[math]::Min($Values.Count-1,[math]::Floor(($Values.Count-1)*$P));return [math]::Round($Values[$i],1)}
$avg=if($times.Count){[math]::Round(($times|Measure-Object -Average).Average,1)}else{0}
$p50=Percentile $times .50;$p95=Percentile $times .95;$p99=Percentile $times .99
$errorPct=[math]::Round(($fail.Count/[double]$Requests)*100,2)
$byPath=@()
foreach($p in $paths){
  $rows=@($arr|Where-Object path -eq $p);$good=@($rows|Where-Object ok);$ts=@($good|ForEach-Object ms|Sort-Object)
  $byPath += [pscustomobject]@{path=$p;requests=$rows.Count;errors=@($rows|Where-Object{-not $_.ok}).Count;p95_ms=(Percentile $ts .95)}
}
$statusCounts=@($arr|Group-Object status|Sort-Object Name|ForEach-Object{[pscustomobject]@{status=[int]$_.Name;count=$_.Count}})
$summary=[pscustomobject]@{
  version='6.19';base_url=$BaseUrl;requests=$Requests;concurrency=$Concurrency;success=$ok.Count;errors=$fail.Count;
  error_percent=$errorPct;avg_ms=$avg;p50_ms=$p50;p95_ms=$p95;p99_ms=$p99;
  threshold_p95_ms=$MaxP95Ms;threshold_error_percent=$MaxErrorPercent;status_counts=$statusCounts;by_path=$byPath;
  generated_at=(Get-Date).ToUniversalTime().ToString('o')
}
Write-Host "Başarılı: $($ok.Count)/$Requests | Hata: $($fail.Count) ($errorPct%) | Ort: ${avg}ms | P95: ${p95}ms | P99: ${p99}ms" -ForegroundColor $(if($fail.Count){'Yellow'}else{'Green'})
$dir='reports';New-Item -ItemType Directory -Force -Path $dir|Out-Null
$out=Join-Path $dir ("load-test-"+(Get-Date -Format 'yyyyMMdd-HHmmss')+'.json')
$summary|ConvertTo-Json -Depth 6|Set-Content $out -Encoding UTF8
Write-Host "Rapor: $out" -ForegroundColor DarkGray
if($errorPct -gt $MaxErrorPercent){throw "Hata oranı eşik üstünde: $errorPct% > $MaxErrorPercent%"}
if($p95 -gt $MaxP95Ms){throw "P95 eşik üstünde: ${p95}ms > ${MaxP95Ms}ms"}
Write-Host 'PERFORMANCE HARDENING PASS' -ForegroundColor Green
