4B.4.3.6.6.30I-H1 Internal Execution Harness Acceptance Chain Hotfix

Apply:
  cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
  Expand-Archive -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436630I_H1_internal_execution_harness_acceptance_chain_hotfix_patch.zip" -DestinationPath . -Force
  python tools/apply_4B436630I_H1_internal_execution_harness_acceptance_chain_hotfix.py

Verify:
  $env:PYTHONPATH="src"
  python tools/check_4B436630I_H1_internal_execution_harness_acceptance_chain_hotfix.py --once-json
  python tools/check_4B436630I_paper_sandbox_dry_run_internal_execution_harness.py --once-json
  python tools/check_4B436630H_paper_sandbox_dry_run_execution_readiness_lock.py --once-json
  python tools/check_4B436630D_operator_approval_evidence_capture.py --once-json
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  python -m pytest -q tests/test_paper_sandbox_dry_run_internal_execution_harness_4B436630I.py tests/test_paper_sandbox_dry_run_internal_execution_harness_4B436630I_H1.py
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Run 30I evidence again:
  $env:PYTHONPATH="src"
  python tools/run_4B436630I_paper_sandbox_dry_run_internal_execution_harness.py --reports-dir .\reports\production_hardening

Expected 30I decision:
  PAPER_SANDBOX_DRY_RUN_INTERNAL_EXECUTION_HARNESS_READY_SIMULATED_FILL_LEDGER_APPENDED_NO_EXCHANGE_SUBMIT_PAPER_CANDIDATE_BLOCKED_LIVE_REAL_BLOCKED

Commit:
  git status --short
  git add -A
  git commit -m "4B.4.3.6.6.30I-H1 internal execution harness acceptance chain hotfix"
  git tag -a 4B.4.3.6.6.30I-H1 -m "Accepted internal execution harness acceptance chain hotfix"
  git push origin main
  git push origin 4B.4.3.6.6.30I-H1

This hotfix only repairs checker/runner compatibility. It does not enable exchange submit, paper sandbox execution, paper candidate, runtime overlays, training/reload, or live-real.
