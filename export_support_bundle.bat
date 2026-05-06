@echo off
setlocal
cd /d "%~dp0"
python tools\export_support_bundle.py --config config.local.yaml --host 127.0.0.1 --port 8000
pause
