4B.4.3.6.6.30Y Live-Real Micro Canary Reconciliation

Apply:
  Expand-Archive -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436630Y_live_real_micro_canary_reconciliation_patch.zip" -DestinationPath . -Force
  python tools/apply_4B436630Y_live_real_micro_canary_reconciliation.py

Check:
  $env:PYTHONPATH="src"
  python tools/check_4B436630Y_live_real_micro_canary_reconciliation.py --once-json
  python tools/check_4B436630X_live_real_micro_canary_gate.py --once-json

Test:
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_live_real_micro_canary_reconciliation_4B436630Y.py
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Default evidence, execution evidence required:
  python tools/run_4B436630Y_live_real_micro_canary_reconciliation.py --reports-dir .\reports\production_hardening

Ready evidence using operator-provided external execution fields:
  python tools/run_4B436630Y_live_real_micro_canary_reconciliation.py `
    --reports-dir .\reports\production_hardening `
    --operator-executed `
    --operator-id operator-30y `
    --exchange-order-id <REAL_EXCHANGE_ORDER_ID> `
    --filled-quantity 0.002 `
    --avg-fill-price 2500 `
    --account-position-delta-qty 0.002 `
    --ledger-event-id <REAL_LEDGER_EVENT_ID> `
    --ledger-filled-quantity 0.002 `
    --ledger-notional-usd 5.0 `
    --emergency-stop-armed

Alternative, use a real execution evidence JSON:
  python tools/run_4B436630Y_live_real_micro_canary_reconciliation.py `
    --reports-dir .\reports\production_hardening `
    --execution-evidence-json .\reports\production_hardening\your_real_execution_evidence.json

Expected READY decision:
  LIVE_REAL_MICRO_CANARY_RECONCILIATION_READY_MISMATCH_ZERO_EMERGENCY_STOP_ARMED

Commit only after checker, pytest, compileall and READY evidence pass:
  git status --short
  git add -A
  git commit -m "4B.4.3.6.6.30Y live-real micro canary reconciliation"
  git tag -a 4B.4.3.6.6.30Y -m "Accepted live-real micro canary reconciliation"
  git push origin main
  git push origin 4B.4.3.6.6.30Y

Risk: this phase verifies externally executed micro-canary evidence. It never submits orders by itself and it does not approve additional live-real submit.
