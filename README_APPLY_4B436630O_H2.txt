4B.4.3.6.6.30O-H2 Reconciliation Checker Probe Signature Hotfix

Problem:
  30O runtime/reconciliation path was healthy, but the 30O checker module probe called
  build_paper_sandbox_execution_reconciliation_snapshot(..., reports_dir=...) against a repository copy whose function signature did not accept reports_dir.
  This produced TypeError and made 30O-H1 target_30o_checker_ok=false.

Apply:
  cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
  Expand-Archive -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436630O_H2_reconciliation_checker_probe_signature_hotfix_patch.zip" -DestinationPath . -Force
  python tools/apply_4B436630O_H2_reconciliation_checker_probe_signature_hotfix.py

Verify:
  $env:PYTHONPATH="src"
  python tools/check_4B436630O_H2_reconciliation_checker_probe_signature_hotfix.py --once-json
  python tools/check_4B436630O_H1_reconciliation_checker_baseline_compat.py --once-json
  python tools/check_4B436630O_paper_sandbox_execution_reconciliation_gate.py --once-json
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_paper_sandbox_execution_reconciliation_gate_4B436630O.py tests/test_paper_sandbox_execution_reconciliation_gate_4B436630O_H1.py tests/test_paper_sandbox_execution_reconciliation_gate_4B436630O_H2.py
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Run evidence:
  $env:PYTHONPATH="src"
  python tools/run_4B436630O_paper_sandbox_execution_reconciliation_gate.py --reports-dir .\reports\production_hardening

Expected decision:
  PAPER_SANDBOX_EXECUTION_RECONCILIATION_GATE_READY_MISMATCH_ZERO_SQLITE_MIRRORED_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL

Commit only if all checks pass:
  git status --short
  git add -A
  git commit -m "4B.4.3.6.6.30O-H2 reconciliation checker probe signature hotfix"
  git tag -a 4B.4.3.6.6.30O-H2 -m "Accepted reconciliation checker probe signature hotfix"
  git push origin main
  git push origin 4B.4.3.6.6.30O-H2

Risk posture:
  - Checker-only compatibility fix.
  - No exchange submit.
  - No live-real.
  - No runtime overlay/training/reload/strategy mutation.
