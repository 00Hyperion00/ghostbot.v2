# 4B.4.3.6.6.30X First Live-Real Micro Canary

Consumes 30W final approval and builds one minimum-size live-real micro-canary submit request for manual runtime handoff.

## Decision
- `decision`: `FIRST_LIVE_REAL_MICRO_CANARY_GATE_OPERATOR_APPROVAL_REQUIRED_NO_NETWORK_SUBMIT`
- `approved_for_first_live_real_micro_canary_gate`: `False`
- `approved_for_exchange_submit`: `False`
- `approved_for_live_real`: `False`
- `source_30w_final_operator_approval_verified`: `True`
- `micro_canary_operator_approval_verified`: `False`
- `single_min_size_order_request_verified`: `True`
- `hard_caps_verified`: `True`
- `kill_switch_verified`: `True`
- `automated_network_submit_disabled_verified`: `True`
- `submit_request_built`: `False`
- `submit_request_path`: `None`
- `exchange_submit_performed`: `False`
- `network_submit_attempted`: `False`
- `live_real_order_performed`: `False`

## Operator approval
- `operator_id`: `None`
- `approval_token_matched`: `False`
- `captured_at_utc`: `None`

## Order request
- `symbol`: `ETHUSDT`
- `side`: `BUY`
- `quantity`: `0.002`
- `mark_price`: `2500.0`
- `notional_usd`: `5.0`
- `submit_handoff_mode`: `manual_runtime_only`

## Reason codes
- `MICRO_CANARY_OPERATOR_APPROVAL_NOT_ISSUED`
- `MICRO_CANARY_APPROVAL_TOKEN_MISMATCH`
- `MICRO_CANARY_OPERATOR_ID_REQUIRED`
