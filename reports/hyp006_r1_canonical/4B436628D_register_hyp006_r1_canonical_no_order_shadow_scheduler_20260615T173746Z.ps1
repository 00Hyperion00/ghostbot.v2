# 4B.4.3.6.6.28D HYP-006-R1 canonical no-order shadow scheduler registration script
# This script is emitted for operator review. The 28D Python patch does not execute it automatically.
$ErrorActionPreference = 'Stop'
$ProjectRoot = "C:\\Users\\muhas\\OneDrive\\Masa\u00fcst\u00fc\\trade_botV2"
$ApprovalJson = "reports\\hyp006_r1_canonical\\4B436628D_hyp006_r1_shadow_collection_registration_approval_20260615T173746Z.json"
$ReportsDir = "reports\\hyp006_r1_canonical"
$TaskName = "TradeBot_HYP006_R1_Canonical_NoOrderShadowCollection"
Set-Location $ProjectRoot
$Python = 'python'
$ActionArgs = @("tools/run_4B436628D_hyp006_canonical_shadow_cycle.py",
  "--registration-approval-json", $ApprovalJson,
  "--symbols", "ADAUSDT,BNBUSDT,BTCUSDT,ETHUSDT,LINKUSDT,LTCUSDT,SOLUSDT,XRPUSDT",
  "--interval", "4h",
  "--days", 30,
  "--out-dir", $ReportsDir,
  "--review-ok") -join ' '
$Action = New-ScheduledTaskAction -Execute $Python -Argument $ActionArgs -WorkingDirectory $ProjectRoot
$Trigger = New-ScheduledTaskTrigger -Daily -At 00:05
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 20)
# Operator action: uncomment the next line only after reviewing the 28D approval report.
# Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Description 'HYP-006-R1 canonical no-order shadow collection. No paper/live/order actions.' -Force
Write-Host 'Registration script generated. Scheduler task not created until Register-ScheduledTask line is explicitly enabled by operator.'
