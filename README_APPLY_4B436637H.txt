4B.4.3.6.6.37H — Runtime Process Lock

Purpose:
- Close P0-7 Runtime Process Lock hardening gap.
- Add a no-submit runtime process lock baseline, stale-lock detection contract, and guard probes.
- Keep paper/live/exchange submit/runtime start locked.

Apply:
  python tools/apply_4B436637H_runtime_process_lock.py

Check:
  $env:PYTHONPATH="src"
  python tools/check_4B436637H_runtime_process_lock.py --once-json

Test:
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_runtime_process_lock_4B436637H.py
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Run/report:
  $env:PYTHONPATH="src"
  python tools/run_4B436637H_runtime_process_lock.py --reports-dir .eportsecovery --once-json

Safety:
- No lock file is created/deleted.
- No process is started/killed.
- No runtime health probe is performed.
- No runtime overlay is activated.
- No paper/live/exchange submit/network request is enabled.
- No next phase is unlocked.
