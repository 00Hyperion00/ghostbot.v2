4B.4.3.6.6.30J Paper Sandbox Dry-run Reconciliation + Audit Ledger Proof

Apply:
  cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
  Expand-Archive -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436630J_paper_sandbox_dry_run_reconciliation_audit_ledger_proof_patch.zip" -DestinationPath . -Force
  python tools/apply_4B436630J_paper_sandbox_dry_run_reconciliation_audit_ledger.py

Verify:
  $env:PYTHONPATH="src"
  python tools/check_4B436630J_paper_sandbox_dry_run_reconciliation_audit_ledger.py --once-json
  python tools/check_4B436630I_H4_internal_execution_harness_repo_hygiene_cleanup.py --once-json
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_paper_sandbox_dry_run_reconciliation_audit_ledger_4B436630J.py
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Run evidence:
  $env:PYTHONPATH="src"
  python tools/run_4B436630J_paper_sandbox_dry_run_reconciliation_audit_ledger.py --reports-dir .\reports\production_hardening

Expected decision:
  PAPER_SANDBOX_DRY_RUN_RECONCILIATION_AUDIT_LEDGER_PROOF_READY_MISMATCH_ZERO_NO_EXCHANGE_SUBMIT_PAPER_CANDIDATE_BLOCKED_LIVE_REAL_BLOCKED

Commit only if all checks pass:
  git status --short
  git add -A
  git commit -m "4B.4.3.6.6.30J paper sandbox dry-run reconciliation audit ledger proof"
  git tag -a 4B.4.3.6.6.30J -m "Accepted paper sandbox dry-run reconciliation audit ledger proof"
  git push origin main
  git push origin 4B.4.3.6.6.30J

Risk posture:
  - No exchange submit.
  - No real paper execution enablement.
  - No paper candidate approval.
  - No live-real approval.
  - No runtime overlay/training/reload/strategy mutation.
