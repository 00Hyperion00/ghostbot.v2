@echo off
setlocal
cd /d "%~dp0"
set "PY_CMD="
if exist ".venv\Scripts\python.exe" set "PY_CMD=.venv\Scripts\python.exe"
if not defined PY_CMD where py >nul 2>&1 && set "PY_CMD=py -3"
if not defined PY_CMD where python >nul 2>&1 && set "PY_CMD=python"
if not defined PY_CMD (
  echo [HATA] Python bulunamadi.
  pause
  exit /b 1
)
echo [1/3] v3.0 bagimliliklari kuruluyor...
%PY_CMD% -m pip install --disable-pip-version-check --only-binary=:all: -r requirements_v3.txt
if errorlevel 1 (
  echo [HATA] Paket kurulumu tamamlanamadi.
  pause
  exit /b 1
)
echo [2/3] Uygulama ve veritabani yukseltilecek...
%PY_CMD% install_v3.py
if errorlevel 1 (
  echo [HATA] v3.0 yukseltmesi tamamlanamadi.
  pause
  exit /b 1
)
echo [3/3] Sistem testi calistiriliyor...
%PY_CMD% -m pytest -q test_v3.py
if errorlevel 1 (
  echo [UYARI] Testlerden biri basarisiz. test_v3.log ve konsol ciktisini inceleyin.
  pause
  exit /b 1
)
echo.
echo v3.0 Kurumsal Surekli Denetim yukseltmesi tamamlandi.
pause
