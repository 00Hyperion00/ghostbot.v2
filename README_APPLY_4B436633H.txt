
# Apply 4B.4.3.6.6.33H

```powershell
cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
python tools/apply_4B436633H_archive_execution_approval_ledger.py
$env:PYTHONPATH="src"
python tools/check_4B436633H_archive_execution_approval_ledger.py --once-json
python -m pytest -q tests/test_archive_execution_approval_ledger_4B436633H.py
python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests
python tools/run_4B436633H_archive_execution_approval_ledger.py --reports-dir .\reports\recovery --once-json
```

Expected decision:

`ARCHIVE_EXECUTION_APPROVAL_LEDGER_READY_FINAL_NO_EXECUTION_GATE_LOCKED`
