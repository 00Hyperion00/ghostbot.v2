$ErrorActionPreference = "Stop"
$CanonicalTaskName = "TradeBot_HYP005_R1_Canonical_NoOrderShadowCollection"
$Task = Get-ScheduledTask -TaskName $CanonicalTaskName -ErrorAction SilentlyContinue
if ($null -eq $Task) {
    Write-Host "Canonical task not found: $CanonicalTaskName"
    exit 0
}
Disable-ScheduledTask -TaskName $CanonicalTaskName | Out-Null
Write-Host "Canonical task disabled: $CanonicalTaskName"
Write-Host "Safety: no task deletion, no config mutation, no trading action."
