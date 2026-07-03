# 4B436637B install contract: requirements.txt is generated from pyproject.toml
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if (-not (Test-Path .venv)) { py -3.11 -m venv .venv }
. .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
pip install -e .
if (-not (Test-Path config.local.yaml)) { Copy-Item examples\config.demo.yaml config.local.yaml }
tradebot dashboard --config config.local.yaml
