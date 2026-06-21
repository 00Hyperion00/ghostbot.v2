# 4B.4.3.6.6.30Y-H1 Live-Real Micro Canary Reconciliation

Consumes 30X submit request and reconciles externally executed live-real micro-canary evidence.

## Decision
- `decision`: `LIVE_REAL_MICRO_CANARY_RECONCILIATION_READY_MISMATCH_ZERO_EMERGENCY_STOP_ARMED`
- `approved_for_live_real_micro_canary_reconciliation`: `True`
- `approved_for_post_canary_review`: `True`
- `approved_for_additional_exchange_submit`: `False`
- `approved_for_live_real_continuation`: `False`
- `source_30x_submit_request_verified`: `True`
- `execution_evidence_verified`: `True`
- `mismatch_count`: `0`
- `emergency_stop_armed_verified`: `True`
- `patch_network_submit_attempted`: `False`
- `external_exchange_submit_performed`: `True`

## Execution evidence
- `operator_id`: `operator-30y`
- `exchange_order_id`: `8114595899`
- `client_order_id`: `tbv2-30x-20260621T205011Z-ethusdt`
- `symbol`: `ETHUSDT`
- `side`: `BUY`
- `status`: `FILLED`
- `filled_quantity`: `0.0029`
- `avg_fill_price`: `1713.36`
- `fill_notional_usd`: `4.968743999999999`

## Reconciliation
- `request_execution_match`: `True`
- `manual_min_notional_quantity_adjustment_requested`: `True`
- `manual_min_notional_quantity_adjustment_accepted`: `True`
- `manual_min_notional_quantity_adjustment_reason`: `manual Binance minimum notional quantity adjustment from 30X request`
- `account_reconciliation_match`: `True`
- `ledger_reconciliation_match`: `True`
- `ledger_event_id`: `MANUAL_30Y_ETHUSDT_8114595899_20260622T002601`

## Emergency stop
- `emergency_stop_armed`: `True`
- `kill_switch_armed`: `True`

## Reason codes
- `LIVE_REAL_MICRO_CANARY_RECONCILIATION_READY`
