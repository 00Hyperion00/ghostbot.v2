# 4B.4.3.6.6.30Q First Paper Sandbox Canary Submit Gate

This report consumes the 30P-H3 submit-arm preflight, verifies explicit operator canary approval, builds one sandbox/demo order intent, and keeps the exchange submit path guarded with no live-real.

## Decision
- `decision`: `FIRST_PAPER_SANDBOX_CANARY_SUBMIT_GATE_OPERATOR_APPROVAL_REQUIRED_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL`
- `approved_for_first_paper_sandbox_canary_submit_gate`: `False`
- `approved_for_30p_submit_arm_consumption`: `True`
- `approved_for_operator_canary_approval`: `False`
- `approved_for_single_sandbox_order_intent`: `False`
- `approved_for_exchange_submit`: `False`
- `approved_for_live_real`: `False`
- `submit_still_blocked`: `True`
- `exchange_submit_performed`: `False`
- `trading_action_performed`: `False`

## Gate checks
- `api_mode_gate`: `True`
- `endpoint_gate`: `True`
- `min_notional_gate`: `True`
- `lot_size_gate`: `True`
- `risk_caps_gate`: `True`
- `kill_switch_gate`: `True`
- `exchange_submit_guard_gate`: `True`
- `no_live_real_gate`: `True`

## Reason codes
- `SOURCE_30P_SUBMIT_ARM_PREFLIGHT_VERIFIED`
- `CANARY_OPERATOR_ID_REQUIRED`
- `CANARY_OPERATOR_APPROVAL_NOT_ISSUED`
- `CANARY_OPERATOR_APPROVAL_TOKEN_MISMATCH`
- `SANDBOX_CANARY_SUBMIT_READINESS_VERIFIED`
- `SINGLE_SANDBOX_CANARY_ORDER_INTENT_BUILT_SUBMIT_GUARDED`
- `EXCHANGE_SUBMIT_PATH_GUARDED_CANARY_INTENT_ONLY`
- `NO_LIVE_REAL_VERIFIED_FIRST_CANARY_GATE`
- `SINGLE_SANDBOX_CANARY_ORDER_INTENT_ONLY`
- `EXCHANGE_SUBMIT_PATH_STILL_GUARDED`
- `NO_LIVE_REAL_VERIFIED`
