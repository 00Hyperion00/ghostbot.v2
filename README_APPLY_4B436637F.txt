# 4B.4.3.6.6.37F Typed Confirmation Destructive Actions

No-submit P0-5 hardening patch.

## Apply

```powershell
python tools/apply_4B436637F_typed_confirmation_destructive_actions.py
```

## Check

```powershell
$env:PYTHONPATH="src"
python tools/check_4B436637F_typed_confirmation_destructive_actions.py --once-json
```

## Test

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH="src"
python -m pytest -q tests/test_typed_confirmation_destructive_actions_4B436637F.py
python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests
```

## Run evidence

```powershell
$env:PYTHONPATH="src"
python tools/run_4B436637F_typed_confirmation_destructive_actions.py --reports-dir .eportsecovery --once-json
```

This patch does not bind existing API routes, does not execute destructive actions, and does not enable paper/live/submit/runtime overlay.
