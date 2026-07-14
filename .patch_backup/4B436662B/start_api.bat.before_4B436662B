@echo off
setlocal
cd /d "%~dp0"
set "PYTHONPATH=%CD%\src"
title TradeBot API
python tools\desktop_launcher.py --config config.local.yaml --host 127.0.0.1 --port 8000 api
if errorlevel 1 pause
endlocal
