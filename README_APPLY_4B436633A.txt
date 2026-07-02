# 4B.4.3.6.6.33A Project Recovery Baseline

This is a no-order, no-training, no-reload recovery inventory patch.

## Apply

```powershell
cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2

Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436633A_project_recovery_baseline_patch.zip" `
  -DestinationPath . `
  -Force

python tools/apply_4B436633A_project_recovery_baseline.py
```

## Check and test

```powershell
$env:PYTHONPATH="src"

python tools/check_4B436633A_project_recovery_baseline.py `
  --once-json

$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH="src"

python -m pytest -q `
  tests/test_project_recovery_baseline_4B436633A.py

python -m compileall -q `
  -x '(_patch_backup|_patch_payload|legacy_patches)' `
  src tools tests
```

## Run recovery baseline report

```powershell
$env:PYTHONPATH="src"

python tools/run_4B436633A_project_recovery_baseline.py `
  --reports-dir .\reports\recovery `
  --once-json
```

## Expected safety state

```text
approved_for_live_real=False
approved_for_paper_transition=False
approved_for_exchange_submit=False
approved_for_runtime_overlay=False
trading_action_performed=False
training_performed=False
reload_performed=False
```

## Commit

```powershell
git status --short

git add -A

git commit -m "4B.4.3.6.6.33A project recovery baseline"

git tag -a 4B.4.3.6.6.33A `
  -m "Accepted project recovery baseline"

git push origin main
git push origin 4B.4.3.6.6.33A
```
