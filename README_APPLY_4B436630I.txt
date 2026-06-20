4B.4.3.6.6.30I Paper Sandbox Dry-run Internal Execution Harness

Apply:
  cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
  Expand-Archive -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436630I_paper_sandbox_dry_run_internal_execution_harness_patch.zip" -DestinationPath . -Force
  python tools/apply_4B436630I_paper_sandbox_dry_run_internal_execution_harness.py

Verify:
  $env:PYTHONPATH="src"
  python tools/check_4B436630I_paper_sandbox_dry_run_internal_execution_harness.py --once-json
  python tools/check_4B436630H_paper_sandbox_dry_run_execution_readiness_lock.py --once-json
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  python -m pytest -q tests/test_paper_sandbox_dry_run_internal_execution_harness_4B436630I.py
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Run:
  $env:PYTHONPATH="src"
  python tools/run_4B436630I_paper_sandbox_dry_run_internal_execution_harness.py --reports-dir .\reports\production_hardening

Expected if 30H ready evidence exists:
  PAPER_SANDBOX_DRY_RUN_INTERNAL_EXECUTION_HARNESS_READY_SIMULATED_FILL_LEDGER_APPENDED_NO_EXCHANGE_SUBMIT_PAPER_CANDIDATE_BLOCKED_LIVE_REAL_BLOCKED

This patch appends only an internal simulated fill ledger artifact. It does not enable paper sandbox dry-run execution, exchange submit, paper candidate, runtime overlays, training/reload, or live-real.
