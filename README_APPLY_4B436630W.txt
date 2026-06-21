4B.4.3.6.6.30W Live-Real Final Operator Approval

Apply:
  Expand-Archive -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436630W_live_real_final_operator_approval_patch.zip" -DestinationPath . -Force
  python tools/apply_4B436630W_live_real_final_operator_approval.py

Check:
  $env:PYTHONPATH="src"
  python tools/check_4B436630W_live_real_final_operator_approval.py --once-json
  python tools/check_4B436630V_live_real_preflight_gate.py --once-json

Test:
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_live_real_final_operator_approval_4B436630W.py
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Default evidence, approval required:
  python tools/run_4B436630W_live_real_final_operator_approval.py --reports-dir .\reports\production_hardening

Explicit final operator approval evidence:
  python tools/run_4B436630W_live_real_final_operator_approval.py `
    --reports-dir .\reports\production_hardening `
    --operator-id operator-30w `
    --approval-token APPROVE_LIVE_REAL_FINAL_OPERATOR_APPROVAL `
    --issue-final-approval

Expected READY decision:
  LIVE_REAL_FINAL_OPERATOR_APPROVAL_READY_FINAL_APPROVAL_CAPTURED_SUBMIT_BLOCKED_UNTIL_30X_NO_LIVE_REAL_ORDER

Commit only after checker, pytest, compileall and READY evidence pass:
  git status --short
  git add -A
  git commit -m "4B.4.3.6.6.30W live-real final operator approval"
  git tag -a 4B.4.3.6.6.30W -m "Accepted live-real final operator approval"
  git push origin main
  git push origin 4B.4.3.6.6.30W

Risk: no exchange submit, no network submit, no live-real order. 30X remains the first live-real micro canary gate.
