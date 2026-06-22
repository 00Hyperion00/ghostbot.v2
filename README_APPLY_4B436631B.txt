# 4B.4.3.6.6.31B Release Hygiene & Bad Evidence Ledger Cleanup

Bu patch canlı emir göndermez. Amaç: 31A / 31A-H1 / 31A-H2 NOT_READY geçmişini açıklamak, kalan bad evidence dosyalarını quarantine manifest altında taşımak ve 31A-H3 sonrası final audit snapshot üretmek.

## Uygulama

```powershell
cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2

Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436631B_release_hygiene_bad_evidence_ledger_cleanup_patch.zip" `
  -DestinationPath . `
  -Force

python tools/apply_4B436631B_release_hygiene_bad_evidence_ledger_cleanup.py
```

## Kontrol ve test

```powershell
$env:PYTHONPATH="src"

python tools/check_4B436631B_release_hygiene_bad_evidence_ledger_cleanup.py `
  --once-json

$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH="src"

python -m pytest -q `
  tests/test_release_hygiene_bad_evidence_cleanup_4B436631B.py

python -m compileall -q `
  -x '(_patch_backup|_patch_payload|legacy_patches)' `
  src tools tests
```

## 31A-H3 source path al

```powershell
$source31aH3 = (
  Get-ChildItem .\reports\production_hardening\4B436631A_live_micro_canary_freeze_audit_closure_*_ready.json |
    Where-Object { $_.Name -notlike "*_not_ready.json" } |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
).FullName

$source31aH3
```

Boş dönmemeli ve en son accepted 31A-H3 READY JSON olmalı.

## READY evidence üret

```powershell
$env:PYTHONPATH="src"

python tools/run_4B436631B_release_hygiene_bad_evidence_ledger_cleanup.py `
  --reports-dir .\reports\production_hardening `
  --source-31a-h3-report $source31aH3 `
  --operator-id operator-31b `
  --finalization-token FINALIZE_31B_RELEASE_HYGIENE_AUDIT `
  --quarantine-manifest-id BAD_31A_NOT_READY_SUPERSEDED_BY_31A_H3 `
  --audit-comment "31B: quarantine superseded 31A/31A-H1/31A-H2 not_ready evidence; finalize audit snapshot; no further live order approved." `
  --move-bad-evidence-to-quarantine
```

Beklenen karar:

```text
RELEASE_HYGIENE_BAD_EVIDENCE_LEDGER_CLEANUP_READY_FINAL_AUDIT_SNAPSHOT_NO_FURTHER_LIVE_ORDER
```

## Commit

```powershell
git status --short

git add -A

git commit -m "4B.4.3.6.6.31B release hygiene bad evidence cleanup"

git tag -a 4B.4.3.6.6.31B `
  -m "Accepted release hygiene bad evidence ledger cleanup"

git push origin main
git push origin 4B.4.3.6.6.31B
```
