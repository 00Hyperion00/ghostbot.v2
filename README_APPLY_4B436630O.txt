4B.4.3.6.6.30O Paper Sandbox Execution Reconciliation Gate

Apply:
  cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
  Expand-Archive -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436630O_paper_sandbox_execution_reconciliation_gate_patch.zip" -DestinationPath . -Force
  python tools/apply_4B436630O_paper_sandbox_execution_reconciliation_gate.py

Verify:
  $env:PYTHONPATH="src"
  python tools/check_4B436630O_paper_sandbox_execution_reconciliation_gate.py --once-json
  python tools/check_4B436630N_paper_sandbox_dry_run_execution_gate.py --once-json
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_paper_sandbox_execution_reconciliation_gate_4B436630O.py
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Default blocked report:
  $env:PYTHONPATH="src"
  python tools/run_4B436630O_paper_sandbox_execution_reconciliation_gate.py --reports-dir .\reports\production_hardening

Expected default decision:
  PAPER_SANDBOX_EXECUTION_RECONCILIATION_GATE_SQLITE_MIRROR_REQUIRED_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL

Ready reconciliation + SQLite mirror:
  $env:PYTHONPATH="src"
  python tools/run_4B436630O_paper_sandbox_execution_reconciliation_gate.py --reports-dir .\reports\production_hardening --write-sqlite-mirror

Expected ready decision:
  PAPER_SANDBOX_EXECUTION_RECONCILIATION_GATE_READY_MISMATCH_ZERO_SQLITE_MIRRORED_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL

Commit only if all checks pass:
  git status --short
  git add -A
  git commit -m "4B.4.3.6.6.30O paper sandbox execution reconciliation gate"
  git tag -a 4B.4.3.6.6.30O -m "Accepted paper sandbox execution reconciliation gate"
  git push origin main
  git push origin 4B.4.3.6.6.30O

Risk posture:
  - Reconciliation proof only.
  - SQLite audit mirror only.
  - No exchange submit.
  - No live-real.
  - No runtime overlay/training/reload/strategy mutation.
