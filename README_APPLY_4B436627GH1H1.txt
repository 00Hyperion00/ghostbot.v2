4B.4.3.6.6.27G-H1-H1
Windows UTF-8 Git-Root Detection / Unicode-Safe Subprocess Contract Hotfix

PowerShell uygulama adımları
===========================

1) Proje klasörüne geçin:

cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2

2) ZIP dosyasını açın:

Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436627G_H1_H1_windows_utf8_git_root_detection_unicode_safe_subprocess_contract_hotfix_patch.zip" `
  -DestinationPath . `
  -Force

3) Unicode-safe hotfix'i uygulayın:

python tools/apply_4B436627GH1H1_windows_utf8_git_root_detection.py

4) Unicode-safe checker:

python tools/check_4B436627GH1H1_windows_utf8_git_root_detection.py --once-json

5) Asıl repository hygiene patch'ini yeniden çalıştırın:

python tools/apply_4B436627GH1_repository_hygiene_cleanup.py

6) Repository hygiene checker:

python tools/check_4B436627GH1_repository_hygiene_cleanup.py --once-json

7) Hedefli testler:

$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH="src"
python -m pytest -q `
  tests/test_repository_hygiene_cleanup_4B436627GH1.py `
  tests/test_repository_hygiene_windows_utf8_git_root_detection_4B436627GH1H1.py

8) Git durumu:

git status --short

Notlar
======

- Hotfix yalnızca locale-dependent Git subprocess decode hatasını düzeltir.
- Yerel raporları silmez.
- Config, scheduler, training, reload, order execution veya paper/live yetkilerini değiştirmez.
- Önceki başarısız GH1 apply işlemi değişiklik yapmadan durduğu için rollback gerekmez.

Geri alma
=========

python tools/rollback_4B436627GH1H1_windows_utf8_git_root_detection.py
