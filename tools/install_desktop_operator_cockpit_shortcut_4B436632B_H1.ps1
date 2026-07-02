$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Desktop = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $Desktop "TradeBot V2 Operator Cockpit.lnk"
$TargetPath = Join-Path $ProjectRoot "start_tradebot_v2_operator_cockpit.bat"
$Shell = New-Object -ComObject WScript.Shell
$Shortcut = $Shell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $TargetPath
$Shortcut.WorkingDirectory = $ProjectRoot
$Shortcut.Description = "TradeBot V2 Operator Cockpit unified dashboard"
$Shortcut.Save()
Write-Host "Shortcut created: $ShortcutPath"
