4B.4.3.6.6.30R Paper Sandbox Canary Reconciliation

Apply:
  cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
  Expand-Archive -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436630R_paper_sandbox_canary_reconciliation_patch.zip" -DestinationPath . -Force
  python tools/apply_4B436630R_paper_sandbox_canary_reconciliation.py

Verify:
  $env:PYTHONPATH="src"
  python tools/check_4B436630R_paper_sandbox_canary_reconciliation.py --once-json
  python tools/check_4B436630P_H3_submit_arm_real_30o_evidence_selection_hotfix.py --once-json
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_paper_sandbox_canary_reconciliation_4B436630R.py
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Evidence:
  $env:PYTHONPATH="src"
  python tools/run_4B436630R_paper_sandbox_canary_reconciliation.py --reports-dir .\reports\production_hardening

Expected ready decision:
  PAPER_SANDBOX_CANARY_RECONCILIATION_READY_MISMATCH_ZERO_SUBMIT_GUARDED_NO_LIVE_REAL

Commit only if all checks pass:
  git status --short
  git add -A
  git commit -m "4B.4.3.6.6.30R paper sandbox canary reconciliation"
  git tag -a 4B.4.3.6.6.30R -m "Accepted paper sandbox canary reconciliation"
  git push origin main
  git push origin 4B.4.3.6.6.30R

Risk posture:
  - Consumes 30Q order intent only.
  - Submit remained guarded.
  - mismatch_count=0 proof.
  - No exchange submit.
  - No live-real.
