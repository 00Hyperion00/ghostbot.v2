# Apply 4B.4.3.6.6.33G-H1

```powershell
cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2

Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436633G_H1_source_33f_gate_hotfix_patch.zip" `
  -DestinationPath . `
  -Force

python tools/apply_4B436633G_H1_source_33f_gate_hotfix.py
```

Check:

```powershell
$env:PYTHONPATH="src"

python tools/check_4B436633G_H1_source_33f_gate_hotfix.py `
  --once-json

$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH="src"

python -m pytest -q `
  tests/test_archive_execution_preflight_h1_4B436633G_H1.py

python -m compileall -q `
  -x '(_patch_backup|_patch_payload|legacy_patches)' `
  src tools tests
```

Run:

```powershell
$env:PYTHONPATH="src"

python tools/run_4B436633G_H1_source_33f_gate_hotfix.py `
  --reports-dir .\reports\recovery `
  --once-json
```

Re-check 33G:

```powershell
$env:PYTHONPATH="src"

python tools/check_4B436633G_archive_execution_preflight.py `
  --once-json

python tools/run_4B436633G_archive_execution_preflight.py `
  --reports-dir .\reports\recovery `
  --once-json
```
