# 4B.4.3.6.6.33I — Recovery Closure Report

## Apply

```powershell
python tools/apply_4B436633I_recovery_closure_report.py
```

## Check

```powershell
$env:PYTHONPATH="src"
python tools/check_4B436633I_recovery_closure_report.py --once-json
```

## Test

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH="src"
python -m pytest -q tests/test_recovery_closure_report_4B436633I.py
python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests
```

## Run

```powershell
$env:PYTHONPATH="src"
python tools/run_4B436633I_recovery_closure_report.py --reports-dir .eportsecovery --once-json
```

## Safety

No trading, no exchange submit, no archive execution, no file delete, no runtime overlay, no training, no reload.
