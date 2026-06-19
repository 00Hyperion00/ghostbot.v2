# 4B.4.3.6.6.30A Paper Candidate Preflight

## Apply

```powershell
cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2

Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436630A_paper_candidate_preflight_no_order_to_paper_sandbox_cap_killswitch_operator_approval_patch.zip" `
  -DestinationPath . `
  -Force

python tools/apply_4B436630A_paper_candidate_preflight.py
```

## Verify

```powershell
$env:PYTHONPATH="src"

python tools/check_4B436630A_paper_candidate_preflight.py `
  --once-json

$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH="src"

python -m pytest -q `
  tests/test_paper_candidate_preflight_4B436630A.py

python -m compileall -q `
  -x '(_patch_backup|_patch_payload|legacy_patches)' `
  src tools tests
```

## Report

```powershell
$env:PYTHONPATH="src"

python tools/run_4B436630A_paper_candidate_preflight.py `
  --reports-dir .\reports\production_hardening
```
