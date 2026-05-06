@echo off
setlocal
cd /d "%~dp0"
if not exist .venv (
  py -3.11 -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
if not exist config.local.yaml (
  copy examples\config.demo.yaml config.local.yaml >nul
)
tradebot dashboard --config config.local.yaml
endlocal
