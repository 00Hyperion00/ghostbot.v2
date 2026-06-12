4B.4.3.6.6.27G-H1
Repository Hygiene Cleanup / Runtime Report Artifact Ignore Policy / Patch Backup-Payload Exclusion / Accepted Baseline Preservation Hotfix

PowerShell uygulama adımları
===========================

1) Proje klasörüne geçin:

cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2

2) ZIP dosyasını açın:

Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436627G_H1_repository_hygiene_cleanup_runtime_report_artifact_ignore_policy_patch_backup_payload_exclusion_accepted_baseline_preservation_hotfix_patch.zip" `
  -DestinationPath . `
  -Force

3) Patch'i uygulayın:

python tools/apply_4B436627GH1_repository_hygiene_cleanup.py

4) Read-only checker:

python tools/check_4B436627GH1_repository_hygiene_cleanup.py --once-json

5) Hedefli test:

$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH="src"
python -m pytest -q tests/test_repository_hygiene_cleanup_4B436627GH1.py

6) Git durumunu kontrol edin:

git status --short

Beklenen davranış
=================

- .gitignore değiştirilir.
- reports/hyp005_r1_canonical altındaki runtime dosyaları Git indeksinden çıkarılır fakat yerel diskte kalır.
- tools/_patch_backup_* ve tools/_patch_payload_* klasörleri Git indeksinden çıkarılır fakat yerel diskte kalır.
- Silinen dosya listeleri git status üzerinde D olarak görünür; bu beklenen depo temizliği değişikliğidir.
- Config, scheduler, training, reload, paper/live ve order execution davranışı değiştirilmez.

Geri alma
=========

python tools/rollback_4B436627GH1_repository_hygiene_cleanup.py
