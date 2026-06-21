4B.4.3.6.6.30Y-H1 — Live-Real Micro Canary Reconciliation / Manual Min-Notional Quantity Adjustment Hotfix

Purpose
- Keeps 30Y reconciliation fail-closed by default.
- Accepts a bounded, explicit operator-approved quantity adjustment only when real Binance fill notional is still inside the 30X micro-canary cap and near the 30X intended notional.
- Does not perform exchange submit, network submit, or additional live-real orders.

Apply
cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
Expand-Archive -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436630Y_H1_min_notional_quantity_adjustment_hotfix_patch.zip" -DestinationPath . -Force
python tools/apply_4B436630Y_H1_min_notional_quantity_adjustment.py

Check
$env:PYTHONPATH="src"
python tools/check_4B436630Y_H1_min_notional_quantity_adjustment.py --once-json
python tools/check_4B436630Y_live_real_micro_canary_reconciliation.py --once-json

Test
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH="src"
python -m pytest -q tests/test_live_real_micro_canary_reconciliation_4B436630Y.py tests/test_live_real_micro_canary_reconciliation_4B436630Y_H1.py
python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Run with real observed Binance fill
$env:PYTHONPATH="src"
$exchangeOrderId = "8114595899"
$ledgerEventId = "MANUAL_30Y_ETHUSDT_8114595899_20260622T002601"
python tools/run_4B436630Y_live_real_micro_canary_reconciliation.py `
  --reports-dir .\reports\production_hardening `
  --operator-executed `
  --operator-id operator-30y `
  --exchange-order-id $exchangeOrderId `
  --filled-quantity 0.0029 `
  --avg-fill-price 1713.36 `
  --account-position-delta-qty 0.0029 `
  --ledger-event-id $ledgerEventId `
  --ledger-filled-quantity 0.0029 `
  --ledger-notional-usd 4.968744 `
  --emergency-stop-armed `
  --allow-min-notional-quantity-adjustment `
  --quantity-adjustment-reason "manual Binance minimum notional quantity adjustment from 30X request"

Expected decision
LIVE_REAL_MICRO_CANARY_RECONCILIATION_READY_MISMATCH_ZERO_EMERGENCY_STOP_ARMED

Commit only after READY

git status --short
git add -A
git commit -m "4B.4.3.6.6.30Y-H1 min-notional quantity adjustment hotfix"
git tag -a 4B.4.3.6.6.30Y-H1 -m "Accepted 30Y min-notional quantity adjustment hotfix"
git push origin main
git push origin 4B.4.3.6.6.30Y-H1
