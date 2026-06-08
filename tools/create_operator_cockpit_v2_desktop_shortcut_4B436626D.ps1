$ErrorActionPreference = "Stop"
$ProjectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$Desktop = [Environment]::GetFolderPath("Desktop")
$Target = Join-Path $ProjectRoot "tools\start_operator_cockpit_v2_desktop_4B436626D.cmd"
$ShortcutPath = Join-Path $Desktop "TradeBot V2 Operator Cockpit.lnk"
$Shell = New-Object -ComObject WScript.Shell
$Shortcut = $Shell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $Target
$Shortcut.WorkingDirectory = $ProjectRoot
$Shortcut.Description = "TradeBot V2 local read-only Operator Cockpit"
$Shortcut.Save()
Write-Host "Desktop shortcut created: $ShortcutPath" -ForegroundColor Green
