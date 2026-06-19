# 4B.4.3.6.6.29C Apply Guide

```powershell
cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2

Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436629C_sqlite_audit_ledger_upgrade_orders_fills_positions_risk_model_balance_operator_schema_migration_patch.zip" `
  -DestinationPath . `
  -Force

python tools/apply_4B436629C_sqlite_audit_ledger_upgrade.py
```

Kontrol ve test:

```powershell
$env:PYTHONPATH="src"
python tools/check_4B436629C_sqlite_audit_ledger_upgrade.py --once-json

$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH="src"
python -m pytest -q tests/test_sqlite_audit_ledger_upgrade_4B436629C.py
python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests
```

Rapor:

```powershell
$env:PYTHONPATH="src"
python tools/run_4B436629C_sqlite_audit_ledger_upgrade.py --reports-dir .\reports\production_hardening
```

Beklenen karar:

```text
SQLITE_AUDIT_LEDGER_UPGRADE_READY_LIVE_REAL_STILL_BLOCKED
```

Commit:

```powershell
git status --short
git add -A
git commit -m "4B.4.3.6.6.29C SQLite audit ledger upgrade"
git tag -a 4B.4.3.6.6.29C -m "Accepted SQLite audit ledger upgrade baseline"
git push
git push origin 4B.4.3.6.6.29C
```
