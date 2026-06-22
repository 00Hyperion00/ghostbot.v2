4B.4.3.6.6.30Z Post Live Micro-Canary Risk Review

Apply:
  Expand-Archive -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436630Z_post_live_micro_canary_risk_review_patch.zip" -DestinationPath . -Force
  python tools/apply_4B436630Z_post_live_micro_canary_risk_review.py

Check:
  $env:PYTHONPATH="src"
  python tools/check_4B436630Z_post_live_micro_canary_risk_review.py --once-json
  python tools/check_4B436630Y_H1_min_notional_quantity_adjustment.py --once-json

Test:
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_post_live_micro_canary_risk_review_4B436630Z.py
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Run evidence with real fill fee/PnL/slippage review values:
  python tools/run_4B436630Z_post_live_micro_canary_risk_review.py `
    --reports-dir .\reports\production_hardening `
    --fee-amount 0.0000029 `
    --fee-asset ETH `
    --review-mark-price 1713.36 `
    --reference-price 1713.36 `
    --emergency-stop-armed `
    --operator-notes "post live micro-canary risk review after 30Y-H1 reconciliation"

Expected READY decision:
  POST_LIVE_MICRO_CANARY_RISK_REVIEW_READY_PNL_FEE_SLIPPAGE_EMERGENCY_STOP_NO_ADDITIONAL_LIVE_ORDER

Commit only after checker, pytest, compileall and READY evidence pass:
  git status --short
  git add -A
  git commit -m "4B.4.3.6.6.30Z post live micro-canary risk review"
  git tag -a 4B.4.3.6.6.30Z -m "Accepted post live micro-canary risk review"
  git push origin main
  git push origin 4B.4.3.6.6.30Z

Risk: this phase reviews the already executed micro-canary. It does not place a new order, does not submit to Binance, and does not approve live-real continuation.
