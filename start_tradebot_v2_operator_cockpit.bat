@echo off
setlocal
cd /d "%~dp0"
title TradeBot V2 Operator Cockpit
set "PYTHONPATH=%CD%\src;%PYTHONPATH%"
echo Starting TradeBot V2 Operator Cockpit...
python "tools\run_operator_cockpit_unified.py"
if errorlevel 1 (
  echo.
  echo Operator Cockpit exited with an error.
  pause
)
