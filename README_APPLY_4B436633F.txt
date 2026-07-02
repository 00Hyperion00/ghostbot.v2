# Apply 4B.4.3.6.6.33F

```powershell
cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2

Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436633F_evidence_retention_archive_policy_patch.zip" `
  -DestinationPath . `
  -Force

python tools/apply_4B436633F_evidence_retention_archive_policy.py
```

Check:

```powershell
$env:PYTHONPATH="src"

python tools/check_4B436633F_evidence_retention_archive_policy.py `
  --once-json

$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH="src"

python -m pytest -q `
  tests/test_evidence_retention_archive_policy_4B436633F.py

python -m compileall -q `
  -x '(_patch_backup|_patch_payload|legacy_patches)' `
  src tools tests
```

Run:

```powershell
$env:PYTHONPATH="src"

python tools/run_4B436633F_evidence_retention_archive_policy.py `
  --reports-dir .\reports\recovery `
  --once-json
```
