$ErrorActionPreference = "Stop"
python -m pip install pywebview
if ($LASTEXITCODE -ne 0) {
  throw "pywebview installation failed"
}
Write-Host "pywebview desktop dependency installed." -ForegroundColor Green
