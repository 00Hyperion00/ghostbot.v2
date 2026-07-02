@echo off
setlocal
cd /d %~dp0
if exist .venv\Scripts\python.exe (
  .venv\Scripts\python.exe -m tradebot.cli cockpit --config config.local.yaml --host 127.0.0.1 --port 8787
) else (
  python -m tradebot.cli cockpit --config config.local.yaml --host 127.0.0.1 --port 8787
)
pause
