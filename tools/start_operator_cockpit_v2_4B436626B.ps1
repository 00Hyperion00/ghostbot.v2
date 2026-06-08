$ErrorActionPreference = "Stop"
$ProjectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
Set-Location $ProjectRoot
python tools/run_operator_cockpit_v2_4B436626B.py --project-root $ProjectRoot --host 127.0.0.1 --port 8090 --open-browser
