4B.4.3.6.6.30O-H5 Reconciliation Checker Full Probe Rebuild

Problem fixed:
  30O-H4 still called stale target checker probe paths.
  Existing target checker called build_paper_sandbox_execution_reconciliation_snapshot with an incompatible signature in the local repo.

Scope:
  - Replaces target 30O checker with adaptive signature probing.
  - Replaces H1/H2/H3/H4 wrapper checkers so they delegate to the rebuilt target checker.
  - Does not modify runtime reconciliation module.
  - Does not enable exchange submit or live-real.

Apply:
  cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
  Expand-Archive -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436630O_H5_reconciliation_checker_full_probe_rebuild_patch.zip" -DestinationPath . -Force
  python tools/apply_4B436630O_H5_reconciliation_checker_full_probe_rebuild.py

Verify:
  $env:PYTHONPATH="src"
  python tools/check_4B436630O_H5_reconciliation_checker_full_probe_rebuild.py --once-json
  python tools/check_4B436630O_paper_sandbox_execution_reconciliation_gate.py --once-json
  python tools/check_4B436630O_H1_reconciliation_checker_baseline_compat.py --once-json
  python tools/check_4B436630O_H2_reconciliation_checker_probe_signature_hotfix.py --once-json
  python tools/check_4B436630O_H3_reconciliation_checker_ledger_event_signature_hotfix.py --once-json
  python tools/check_4B436630O_H4_reconciliation_sqlite_mirror_finalize.py --once-json
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_paper_sandbox_execution_reconciliation_gate_4B436630O_H5.py
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Evidence:
  python tools/run_4B436630O_paper_sandbox_execution_reconciliation_gate.py --reports-dir .\reports\production_hardening

Commit only if all checks pass:
  git status --short
  git add -A
  git commit -m "4B.4.3.6.6.30O-H5 reconciliation checker full probe rebuild"
  git tag -a 4B.4.3.6.6.30O-H5 -m "Accepted reconciliation checker full probe rebuild"
  git push origin main
  git push origin 4B.4.3.6.6.30O-H5
