4B.4.3.6.6.30F Paper Sandbox Dry-run Transition Plan

Apply:
  cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
  Expand-Archive -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436630F_paper_sandbox_dry_run_transition_plan_patch.zip" -DestinationPath . -Force
  python tools/apply_4B436630F_paper_sandbox_dry_run_transition_plan.py

Verify:
  $env:PYTHONPATH="src"
  python tools/check_4B436630F_paper_sandbox_dry_run_transition_plan.py --once-json
  python tools/check_4B436630E_paper_transition_review_rerun.py --once-json
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  python -m pytest -q tests/test_paper_sandbox_dry_run_transition_plan_4B436630F.py
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Run:
  $env:PYTHONPATH="src"
  python tools/run_4B436630F_paper_sandbox_dry_run_transition_plan.py --reports-dir .\reports\production_hardening

Expected if 30E ready evidence exists:
  PAPER_SANDBOX_DRY_RUN_TRANSITION_PLAN_READY_NO_ORDER_ENABLEMENT_LIVE_REAL_BLOCKED

This patch does not enable paper orders, paper dry-run execution, runtime overlays, training/reload, or live-real.
