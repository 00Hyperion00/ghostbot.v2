# 4B.4.3.6.6.30W Live-Real Final Operator Approval

Consumes 30V live-real preflight, captures explicit final operator approval, and keeps live-real submit blocked until 30X.

## Decision
- `decision`: `LIVE_REAL_FINAL_OPERATOR_APPROVAL_OPERATOR_APPROVAL_REQUIRED_SUBMIT_BLOCKED_NO_LIVE_REAL_ORDER`
- `approved_for_live_real_final_operator_approval`: `False`
- `approved_for_30x_live_real_micro_canary_candidate`: `False`
- `source_30v_live_real_preflight_verified`: `True`
- `final_operator_approval_verified`: `False`
- `hard_live_submit_block_verified`: `True`
- `live_real_submit_blocked_until_30x`: `True`
- `order_action_count`: `0`
- `exchange_submit_count`: `0`
- `network_submit_count`: `0`
- `approved_for_exchange_submit`: `False`
- `approved_for_live_real`: `False`
- `live_real_order_performed`: `False`

## Operator approval
- `operator_id`: `None`
- `approval_token_matched`: `False`
- `captured_at_utc`: `None`

## Reason codes
- `LIVE_REAL_FINAL_OPERATOR_APPROVAL_FLAG_REQUIRED`
- `LIVE_REAL_FINAL_OPERATOR_APPROVAL_TOKEN_MISMATCH`
- `LIVE_REAL_FINAL_OPERATOR_ID_REQUIRED`
