4B.4.3.6.6.30H Paper Sandbox Dry-run Execution Readiness Lock

Apply:
  cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
  Expand-Archive -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436630H_paper_sandbox_dry_run_execution_readiness_lock_patch.zip" -DestinationPath . -Force
  python tools/apply_4B436630H_paper_sandbox_dry_run_execution_readiness_lock.py

Verify:
  $env:PYTHONPATH="src"
  python tools/check_4B436630H_paper_sandbox_dry_run_execution_readiness_lock.py --once-json
  python tools/check_4B436630G_paper_sandbox_dry_run_execution_candidate_gate.py --once-json
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  python -m pytest -q tests/test_paper_sandbox_dry_run_execution_readiness_lock_4B436630H.py
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Default blocked report:
  $env:PYTHONPATH="src"
  python tools/run_4B436630H_paper_sandbox_dry_run_execution_readiness_lock.py --reports-dir .\reports\production_hardening

Explicit readiness-lock report:
  $env:PYTHONPATH="src"
  python tools/run_4B436630H_paper_sandbox_dry_run_execution_readiness_lock.py --reports-dir .\reports\production_hardening --operator-id operator-30h --lock-token LOCK_PAPER_SANDBOX_DRY_RUN_READINESS --issue-dry-run-lock

Expected explicit decision:
  PAPER_SANDBOX_DRY_RUN_EXECUTION_READINESS_LOCK_READY_PAPER_EXECUTION_DISABLED_LIVE_REAL_BLOCKED

This patch does not enable paper sandbox dry-run execution, exchange submit, paper candidate, runtime overlays, training/reload, or live-real.
