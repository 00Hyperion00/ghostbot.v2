# 4B.4.3.6.6.30Y Live-Real Micro Canary Reconciliation

Consumes 30X submit request and reconciles externally executed live-real micro-canary evidence.

## Decision
- `decision`: `LIVE_REAL_MICRO_CANARY_RECONCILIATION_EXECUTION_EVIDENCE_REQUIRED_NO_PATCH_NETWORK_SUBMIT`
- `approved_for_live_real_micro_canary_reconciliation`: `False`
- `approved_for_post_canary_review`: `False`
- `approved_for_additional_exchange_submit`: `False`
- `approved_for_live_real_continuation`: `False`
- `source_30x_submit_request_verified`: `True`
- `execution_evidence_verified`: `False`
- `mismatch_count`: `5`
- `emergency_stop_armed_verified`: `True`
- `patch_network_submit_attempted`: `False`
- `external_exchange_submit_performed`: `False`

## Execution evidence
- `operator_id`: `None`
- `exchange_order_id`: `None`
- `client_order_id`: `None`
- `symbol`: `None`
- `side`: `None`
- `status`: `None`
- `filled_quantity`: `0.0`
- `avg_fill_price`: `0.0`
- `fill_notional_usd`: `0.0`

## Reconciliation
- `request_execution_match`: `False`
- `account_reconciliation_match`: `True`
- `ledger_reconciliation_match`: `False`
- `ledger_event_id`: `None`

## Emergency stop
- `emergency_stop_armed`: `True`
- `kill_switch_armed`: `True`

## Reason codes
- `EXECUTION_EVIDENCE_REQUIRED`
- `SYMBOL_MISMATCH`
- `SIDE_MISMATCH`
- `QUANTITY_MISMATCH`
- `NOTIONAL_MISMATCH`
- `LEDGER_RECONCILIATION_MISMATCH`
