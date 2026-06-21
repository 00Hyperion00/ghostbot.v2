4B.4.3.6.6.30O-H1 Reconciliation Checker Baseline Compatibility

Apply:
  cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
  Expand-Archive -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436630O_H1_reconciliation_checker_baseline_compat_patch.zip" -DestinationPath . -Force
  python tools/apply_4B436630O_H1_reconciliation_checker_baseline_compat.py

Verify:
  $env:PYTHONPATH="src"
  python tools/check_4B436630O_H1_reconciliation_checker_baseline_compat.py --once-json
  python tools/check_4B436630O_paper_sandbox_execution_reconciliation_gate.py --once-json
  python tools/check_4B436630N_paper_sandbox_dry_run_execution_gate.py --once-json
  python tools/check_4B436630L_H2_candidate_unlock_hotfix_checker_compat.py --once-json
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_paper_sandbox_execution_reconciliation_gate_4B436630O.py tests/test_paper_sandbox_execution_reconciliation_gate_4B436630O_H1.py
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Reconciliation evidence:
  $env:PYTHONPATH="src"
  python tools/run_4B436630O_paper_sandbox_execution_reconciliation_gate.py --reports-dir .\reports\production_hardening

Expected ready decision:
  PAPER_SANDBOX_EXECUTION_RECONCILIATION_GATE_READY_MISMATCH_ZERO_SQLITE_MIRRORED_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL

Commit only if all checks pass:
  git status --short
  git add -A
  git commit -m "4B.4.3.6.6.30O-H1 reconciliation checker baseline compatibility"
  git tag -a 4B.4.3.6.6.30O-H1 -m "Accepted reconciliation checker baseline compatibility"
  git push origin main
  git push origin 4B.4.3.6.6.30O-H1

Risk posture:
  - Reconciliation checker compatibility only.
  - No exchange submit.
  - No live-real.
  - No runtime overlay/training/reload/strategy mutation.
