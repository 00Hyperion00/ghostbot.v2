4B.4.3.6.6.29B API / Operator Security Hardening

Apply:
  python tools/apply_4B436629B_api_operator_security_hardening.py

Check:
  $env:PYTHONPATH="src"
  python tools/check_4B436629B_api_operator_security_hardening.py --once-json

Test:
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_api_operator_security_hardening_4B436629B.py
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Run report:
  python tools/run_4B436629B_api_operator_security_hardening.py --reports-dir .eports\production_hardening

Safety:
  - Does not enable live-real.
  - Does not enable paper/live.
  - Does not perform runtime overlay activation.
  - Does not mutate HYP-006 strategy thresholds.
  - Does not perform training/reload or order actions.
