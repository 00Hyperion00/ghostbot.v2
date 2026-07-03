# 4B.4.3.6.6.33I-H1 — Source 33H Closure Gate Hotfix

## Apply

```powershell
python tools/apply_4B436633I_H1_source_33h_gate_hotfix.py
```

## Check

```powershell
$env:PYTHONPATH="src"
python tools/check_4B436633I_H1_source_33h_gate_hotfix.py --once-json
```

## Test

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH="src"
python -m pytest -q tests/test_recovery_closure_report_h1_4B436633I_H1.py
python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests
```

## Run

```powershell
$env:PYTHONPATH="src"
python tools/run_4B436633I_H1_source_33h_gate_hotfix.py --reports-dir .eportsecovery --once-json
```

## Re-check 33I

```powershell
$env:PYTHONPATH="src"
python tools/check_4B436633I_recovery_closure_report.py --once-json
python tools/run_4B436633I_recovery_closure_report.py --reports-dir .eportsecovery --once-json
```
