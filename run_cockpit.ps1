$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot
$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
  $python = "python"
}
& $python -m tradebot.cli cockpit --config config.local.yaml --host 127.0.0.1 --port 8787
