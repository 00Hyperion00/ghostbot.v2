4B.4.3.6.6.38C — Paper Sandbox Dry-Run Runtime Harness

Apply:
  python tools/apply_4B436638C_paper_sandbox_dry_run_runtime_harness.py

Check:
  $env:PYTHONPATH="src"
  python tools/check_4B436638C_paper_sandbox_dry_run_runtime_harness.py --once-json

Test:
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_paper_sandbox_dry_run_runtime_harness_4B436638C.py
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Run evidence:
  $env:PYTHONPATH="src"
  python tools/run_4B436638C_paper_sandbox_dry_run_runtime_harness.py --reports-dir .\reports\recovery --once-json

Expected READY decision:
  PAPER_SANDBOX_DRY_RUN_RUNTIME_HARNESS_READY_LOCAL_DRY_RUN_NO_NETWORK_ORDER_NO_LIVE_NO_EXCHANGE_SUBMIT_LOCKED
