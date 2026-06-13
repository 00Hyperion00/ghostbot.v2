4B.4.3.6.6.27G-H2
Canonical Shadow Evidence Path UTF-8 Normalization / Windows Unicode Serialization Parity / Fail-Closed Evidence Path Resolution Hotfix

PowerShell uygulama adımları
===========================

1) Proje klasörüne geçin:

cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2

2) ZIP dosyasını açın:

Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436627G_H2_canonical_shadow_evidence_path_utf8_normalization_windows_unicode_serialization_parity_fail_closed_resolution_hotfix_patch.zip" `
  -DestinationPath . `
  -Force

3) Patch'i uygulayın:

python tools/apply_4B436627GH2_shadow_evidence_path_utf8_normalization.py

4) Read-only checker:

$env:PYTHONPATH="src"
python tools/check_4B436627GH2_shadow_evidence_path_utf8_normalization.py --once-json

5) Hedefli test:

$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH="src"
python -m pytest -q tests/test_shadow_evidence_path_utf8_normalization_4B436627GH2.py

6) Derleme kontrolü:

python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

7) Scheduler aynı cadence ile çalışmaya devam eder. Sonraki canonical epoch sonrasında JSON'u PowerShell 5.1 üzerinde şu şekilde okuyun:

Get-Content $latest.FullName -Raw -Encoding UTF8

Geri alma
=========

python tools/rollback_4B436627GH2_shadow_evidence_path_utf8_normalization.py
