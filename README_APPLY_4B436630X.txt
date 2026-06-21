4B.4.3.6.6.30X First Live-Real Micro Canary

Apply:
  Expand-Archive -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436630X_first_live_real_micro_canary_gate_patch.zip" -DestinationPath . -Force
  python tools/apply_4B436630X_live_real_micro_canary_gate.py

Check:
  $env:PYTHONPATH="src"
  python tools/check_4B436630X_live_real_micro_canary_gate.py --once-json
  python tools/check_4B436630W_live_real_final_operator_approval.py --once-json

Test:
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_live_real_micro_canary_gate_4B436630X.py
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Default evidence, approval required:
  python tools/run_4B436630X_live_real_micro_canary_gate.py --reports-dir .\reports\production_hardening

Explicit micro-canary approval and submit request build:
  python tools/run_4B436630X_live_real_micro_canary_gate.py `
    --reports-dir .\reports\production_hardening `
    --operator-id operator-30x `
    --approval-token APPROVE_FIRST_LIVE_REAL_MICRO_CANARY `
    --issue-micro-canary-approval `
    --symbol ETHUSDT `
    --side BUY `
    --quantity 0.002 `
    --mark-price 2500 `
    --write-submit-request

Expected READY decision:
  FIRST_LIVE_REAL_MICRO_CANARY_GATE_READY_SINGLE_MIN_SIZE_SUBMIT_REQUEST_BUILT_NO_AUTOMATED_NETWORK_SUBMIT

Commit only after checker, pytest, compileall and READY evidence pass:
  git status --short
  git add -A
  git commit -m "4B.4.3.6.6.30X first live-real micro canary gate"
  git tag -a 4B.4.3.6.6.30X -m "Accepted first live-real micro canary gate"
  git push origin main
  git push origin 4B.4.3.6.6.30X

Risk: this patch builds a single minimum-size live-real micro-canary submit request and approval evidence. It does not perform automated network submit. Verify live exchange/account state immediately before any external runtime handoff.
