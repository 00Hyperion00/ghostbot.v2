# 4B.4.3.6.6.30M Paper Sandbox Execution Preflight

This report consumes the 30L-H2 accepted candidate-only unlock, verifies dry-run authorization, builds an internal order envelope, and keeps exchange submit and live-real blocked.

## Decision
- `decision`: `PAPER_SANDBOX_EXECUTION_PREFLIGHT_AUTHORIZATION_REQUIRED_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL`
- `read_only`: `True`
- `approved_for_paper_sandbox_execution_preflight`: `False`
- `approved_for_30l_candidate_unlock_consumption`: `True`
- `approved_for_paper_sandbox_dry_run_authorization`: `False`
- `approved_for_order_envelope_build`: `False`
- `approved_for_paper_sandbox_dry_run_execution`: `False`
- `approved_for_exchange_submit`: `False`
- `approved_for_paper_candidate`: `True`
- `approved_for_live_real`: `False`
- `paper_order_enablement_still_blocked`: `True`
- `trading_action_performed`: `False`
- `exchange_submit_performed`: `False`

## Gate checks
- `source_30l_candidate_unlock_verified`: `True`
- `dry_run_authorization_verified`: `False`
- `order_envelope_built`: `False`
- `order_envelope_written`: `False`
- `no_exchange_submit_verified`: `True`
- `no_live_real_verified`: `True`
- `runtime_activation_blocked`: `True`
- `paper_live_order_blocked`: `True`
- `training_reload_blocked`: `True`

## Reason codes
- `SOURCE_30L_CANDIDATE_ONLY_UNLOCK_VERIFIED`
- `DRY_RUN_AUTHORIZATION_OPERATOR_ID_REQUIRED`
- `DRY_RUN_AUTHORIZATION_NOT_ISSUED`
- `DRY_RUN_AUTHORIZATION_TOKEN_MISMATCH`
- `ORDER_ENVELOPE_BUILT_INTERNAL_ONLY_NO_SUBMIT`
- `NO_EXCHANGE_SUBMIT_VERIFIED_EXECUTION_PREFLIGHT`
- `NO_LIVE_REAL_VERIFIED_EXECUTION_PREFLIGHT`
- `ORDER_ENVELOPE_BUILD_NO_EXCHANGE_SUBMIT`
- `NO_EXCHANGE_SUBMIT_VERIFIED`
- `NO_LIVE_REAL_VERIFIED`
- `PAPER_EXECUTION_STILL_BLOCKED_UNTIL_NEXT_GATE`
