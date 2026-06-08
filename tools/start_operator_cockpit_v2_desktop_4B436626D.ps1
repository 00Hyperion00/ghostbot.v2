$ErrorActionPreference = "Stop"
$ProjectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
Set-Location $ProjectRoot
python tools/run_operator_cockpit_v2_desktop_4B436626D.py --project-root $ProjectRoot
if ($LASTEXITCODE -ne 0) {
  Write-Host ""
  Write-Host "Operator Cockpit desktop shell could not start. Review the error above." -ForegroundColor Red
  Read-Host "Press Enter to close"
  exit $LASTEXITCODE
}
