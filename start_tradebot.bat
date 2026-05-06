@echo off
setlocal
cd /d "%~dp0"
set "PYTHONPATH=%CD%\src"
title TradeBot Desktop Launcher
python tools\desktop_launcher.py --config config.local.yaml --host 127.0.0.1 --port 8000 one-click
if errorlevel 1 (
  echo.
  echo TradeBot launcher exited with error code %errorlevel%.
  pause
)
endlocal
