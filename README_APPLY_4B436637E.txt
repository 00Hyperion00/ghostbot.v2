# 4B.4.3.6.6.37E API Auth Destructive Endpoint Guard

No-submit P0-4 hardening patch.

## Apply

```powershell
python tools/apply_4B436637E_api_auth_destructive_endpoint_guard.py
```

## Check

```powershell
$env:PYTHONPATH="src"
python tools/check_4B436637E_api_auth_destructive_endpoint_guard.py --once-json
```

## Test

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH="src"
python -m pytest -q tests/test_api_auth_destructive_endpoint_guard_4B436637E.py
python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests
```

## Run evidence

```powershell
$env:PYTHONPATH="src"
python tools/run_4B436637E_api_auth_destructive_endpoint_guard.py --reports-dir .eportsecovery --once-json
```

This patch does not bind existing API routes, does not generate/write token secrets, and does not enable paper/live/submit/runtime overlay.
