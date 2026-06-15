# 4B.4.3.6.6.28D-H1 ASCII-safe HYP-006-R1 scheduler registration script
$ErrorActionPreference = 'Stop'

$TaskName = 'TradeBot_HYP006_R1_Canonical_NoOrderShadowCollection'

# Script location: <project>\reports\hyp006_r1_canonical
$ReportsDir = $PSScriptRoot
$ProjectRoot = Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')
$ProjectRoot = $ProjectRoot.Path

Set-Location -LiteralPath $ProjectRoot

$Python = (Get-Command python -ErrorAction Stop).Source
if (-not (Test-Path -LiteralPath $Python)) {
  throw ('Python executable not found: ' + $Python)
}

$CandidateSpecDir = Join-Path $ProjectRoot 'reports\hyp006_r1_candidate_spec'
if (-not (Test-Path -LiteralPath $CandidateSpecDir)) {
  throw ('Candidate spec directory not found: ' + $CandidateSpecDir)
}

$ApprovalJsonItem = Get-ChildItem -LiteralPath $ReportsDir -Filter '4B436628D_hyp006_r1_shadow_collection_registration_approval_*.json' |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1

if (-not $ApprovalJsonItem) {
  throw 'Latest 28D approval-json not found.'
}

$RegistrationJsonItem = Get-ChildItem -LiteralPath $CandidateSpecDir -Filter '4B436628B_hyp006_r1_candidate_spec_registration_gate_*.json' |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1

if (-not $RegistrationJsonItem) {
  throw 'Latest 28B registration-json not found.'
}

$ApprovalJson = $ApprovalJsonItem.FullName
$RegistrationJson = $RegistrationJsonItem.FullName
$WrapperScript = Join-Path $ReportsDir 'run_hyp006_r1_canonical_shadow_scheduler.ps1'
$StdoutLog = Join-Path $ReportsDir 'hyp006_scheduler_stdout.log'
$StderrLog = Join-Path $ReportsDir 'hyp006_scheduler_stderr.log'

$WrapperContent = @"
`$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath '$ProjectRoot'
`$env:PYTHONPATH = 'src'

& '$Python' ``
  'tools/run_4B436628D_hyp006_canonical_shadow_cycle.py' ``
  --registration-approval-json '$ApprovalJson' ``
  --registration-json '$RegistrationJson' ``
  --symbols 'ADAUSDT,BNBUSDT,BTCUSDT,ETHUSDT,LINKUSDT,LTCUSDT,SOLUSDT,XRPUSDT' ``
  --interval '4h' ``
  --days 30 ``
  --out-dir 'reports\hyp006_r1_canonical' ``
  --review-ok ``
  1>> '$StdoutLog' ``
  2>> '$StderrLog'

exit `$LASTEXITCODE
"@

$Utf8Bom = New-Object System.Text.UTF8Encoding($true)
[System.IO.File]::WriteAllText($WrapperScript, $WrapperContent, $Utf8Bom)

$ActionArgs = '-NoProfile -ExecutionPolicy Bypass -File "' + $WrapperScript + '"'
$Action = New-ScheduledTaskAction `
  -Execute 'powershell.exe' `
  -Argument $ActionArgs `
  -WorkingDirectory $ProjectRoot

$Trigger = New-ScheduledTaskTrigger -Daily -At 00:05
$Settings = New-ScheduledTaskSettingsSet `
  -AllowStartIfOnBatteries `
  -DontStopIfGoingOnBatteries `
  -ExecutionTimeLimit (New-TimeSpan -Minutes 20)

Register-ScheduledTask `
  -TaskName $TaskName `
  -Action $Action `
  -Trigger $Trigger `
  -Settings $Settings `
  -Description 'HYP-006-R1 canonical no-order shadow collection. No paper/live/order actions.' `
  -Force

Write-Host 'Scheduler task registered.'
Write-Host ('ProjectRoot: ' + $ProjectRoot)
Write-Host ('WrapperScript: ' + $WrapperScript)
Write-Host ('Python: ' + $Python)
Write-Host ('ApprovalJson: ' + $ApprovalJson)
Write-Host ('RegistrationJson: ' + $RegistrationJson)