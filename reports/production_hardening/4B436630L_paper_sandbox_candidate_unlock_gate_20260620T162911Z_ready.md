# 4B.4.3.6.6.30L Paper Sandbox Candidate Unlock Gate

This report consumes the 30K final go/no-go gate, verifies explicit paper candidate unlock, runs sandbox-only order enablement preflight, and keeps exchange submit and live-real blocked.

## Decision
- `decision`: `PAPER_SANDBOX_CANDIDATE_UNLOCK_GATE_READY_PAPER_CANDIDATE_UNLOCKED_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL`
- `read_only`: `True`
- `approved_for_paper_sandbox_candidate_unlock_gate`: `True`
- `approved_for_explicit_paper_candidate_unlock`: `True`
- `approved_for_sandbox_only_order_enablement_preflight`: `True`
- `approved_for_paper_sandbox_candidate`: `True`
- `approved_for_paper_sandbox_dry_run_execution`: `False`
- `approved_for_exchange_submit`: `False`
- `approved_for_paper_candidate`: `True`
- `approved_for_live_real`: `False`
- `paper_order_enablement_still_blocked`: `True`
- `trading_action_performed`: `False`
- `exchange_submit_performed`: `False`

## Gate checks
- `source_30k_go_no_go_verified`: `True`
- `explicit_candidate_unlock_verified`: `True`
- `sandbox_only_order_enablement_preflight_verified`: `True`
- `no_exchange_submit_yet_verified`: `True`
- `no_live_real_verified`: `True`
- `runtime_activation_blocked`: `True`
- `paper_live_order_blocked`: `True`
- `training_reload_blocked`: `True`

## Reason codes
- `SOURCE_30K_FINAL_GO_NO_GO_READY_VERIFIED`
- `EXPLICIT_PAPER_SANDBOX_CANDIDATE_UNLOCK_VERIFIED`
- `SANDBOX_ONLY_ORDER_ENABLEMENT_PREFLIGHT_VERIFIED_NO_SUBMIT`
- `NO_EXCHANGE_SUBMIT_YET_VERIFIED`
- `NO_LIVE_REAL_VERIFIED_CANDIDATE_UNLOCK_GATE`
- `NO_EXCHANGE_SUBMIT_YET`
- `NO_LIVE_REAL_VERIFIED`
- `ORDER_ENABLEMENT_STILL_BLOCKED_UNTIL_NEXT_EXECUTION_GATE`
