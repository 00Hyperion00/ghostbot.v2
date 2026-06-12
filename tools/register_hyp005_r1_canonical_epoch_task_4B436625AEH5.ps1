# Manual operator action: register the canonical HYP-005-R1 no-order shadow scheduler.
# This script never enables paper/live trading and never sends orders.

$ErrorActionPreference = "Stop"
$CanonicalTaskName = "TradeBot_HYP005_R1_Canonical_NoOrderShadowCollection"
$LegacyR1TaskName = "TradeBot_HYP005_R1_NoOrderShadowCollection"
$BaselineTaskName = "TradeBot_HYP005_NoOrderShadowCollection"
$CycleScript = Join-Path $PSScriptRoot "run_hyp005_r1_canonical_epoch_cycle_4B436625AEH5.ps1"

$LegacyR1Task = Get-ScheduledTask -TaskName $LegacyR1TaskName -ErrorAction Stop
if ($LegacyR1Task.State -ne "Disabled") {
    throw "Legacy R1 task '$LegacyR1TaskName' must remain Disabled. Current state: $($LegacyR1Task.State)"
}

$BaselineTask = Get-ScheduledTask -TaskName $BaselineTaskName -ErrorAction SilentlyContinue
if ($null -ne $BaselineTask -and $BaselineTask.State -ne "Disabled") {
    throw "Baseline task '$BaselineTaskName' must remain Disabled. Current state: $($BaselineTask.State)"
}

$ExistingCanonicalTask = Get-ScheduledTask -TaskName $CanonicalTaskName -ErrorAction SilentlyContinue
if ($null -ne $ExistingCanonicalTask -and $ExistingCanonicalTask.State -ne "Disabled") {
    throw "Existing canonical task '$CanonicalTaskName' must be Disabled before replacement. Current state: $($ExistingCanonicalTask.State)"
}

$Action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$CycleScript`""
$Now = Get-Date
$NextBoundary = $Now.Date.AddHours(([math]::Floor($Now.Hour / 4) + 1) * 4)
if ($NextBoundary -le $Now) { $NextBoundary = $NextBoundary.AddHours(4) }
$Trigger = New-ScheduledTaskTrigger -Once -At $NextBoundary -RepetitionInterval (New-TimeSpan -Hours 4) -RepetitionDuration (New-TimeSpan -Days 3650)
$Settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable
$SettingPropertyNames = @($Settings.PSObject.Properties.Name)
if ($SettingPropertyNames -contains "DisallowStartIfOnBatteries") { $Settings.DisallowStartIfOnBatteries = $true }
if ($SettingPropertyNames -contains "StopIfGoingOnBatteries") { $Settings.StopIfGoingOnBatteries = $true }
if ($SettingPropertyNames -contains "AllowStartIfOnBatteries") { $Settings.AllowStartIfOnBatteries = $false }

Register-ScheduledTask `
    -TaskName $CanonicalTaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "HYP-005-R1 canonical epoch no-order shadow collection. 25V→25X→25W→25Y→chain checks. No paper/live/order actions." `
    -Force | Out-Null

Write-Host "Registered canonical task: $CanonicalTaskName"
Write-Host "Legacy R1 task remains Disabled: $LegacyR1TaskName"
Write-Host "Canonical reports dir: reports\hyp005_r1_canonical"
Write-Host "Safety: no config mutation, no paper/live enablement, no order action."
