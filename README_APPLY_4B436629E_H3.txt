# 4B.4.3.6.6.29E-H3 Apply Guide

## Apply

```powershell
cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2

Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436629E_H3_production_readiness_legacy_test_compat_cleanup_hotfix_patch.zip" `
  -DestinationPath . `
  -Force

python tools/apply_4B436629E_H3_production_readiness_legacy_test_compat.py
```

## Verify

```powershell
$env:PYTHONPATH="src"

python tools/check_4B436629E_H3_production_readiness_legacy_test_compat.py `
  --once-json

python tools/check_4B436629E_H2_production_readiness_evidence_selector_compat.py `
  --once-json

python tools/check_4B436629E_H1_production_readiness_evidence_refresh.py `
  --once-json

python tools/check_4B436629E_production_readiness_consolidation_gate.py `
  --once-json

$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH="src"

python -m pytest -q `
  tests/test_production_readiness_evidence_selector_compat_4B436629E_H2.py `
  tests/test_production_readiness_evidence_refresh_4B436629E_H1.py `
  tests/test_production_readiness_consolidation_gate_4B436629E.py `
  tests/test_production_readiness_legacy_test_compat_4B436629E_H3.py

python -m compileall -q `
  -x '(_patch_backup|_patch_payload|legacy_patches)' `
  src tools tests
```

## Run Reports

```powershell
$env:PYTHONPATH="src"

python tools/run_4B436629E_H3_production_readiness_legacy_test_compat.py `
  --reports-dir .\reports\production_hardening

python tools/run_4B436629E_production_readiness_consolidation_gate.py `
  --reports-dir .\reports\production_hardening
```

## Commit

```powershell
git status --short

git add -A

git commit -m "4B.4.3.6.6.29E-H3 production readiness legacy test compatibility"

git tag -a 4B.4.3.6.6.29E-H3 `
  -m "Accepted production readiness legacy test compatibility hotfix"

git push
git push origin 4B.4.3.6.6.29E-H3
```
