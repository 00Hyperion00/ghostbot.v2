# Apply 4B.4.3.6.6.33E — Status Conflict Resolver

PowerShell:

```powershell
cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2

Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436633E_status_conflict_resolver_patch.zip" `
  -DestinationPath . `
  -Force

python tools/apply_4B436633E_status_conflict_resolver.py
```

Check/test:

```powershell
$env:PYTHONPATH="src"
python tools/check_4B436633E_status_conflict_resolver.py --once-json

$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH="src"
python -m pytest -q tests/test_status_conflict_resolver_4B436633E.py
python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests
```

Run:

```powershell
$env:PYTHONPATH="src"
python tools/run_4B436633E_status_conflict_resolver.py --reports-dir .\reports\recovery --once-json
```
