# 4B.4.3.6.6.30V Live-Real Preflight Gate

Consumes 30U promotion review, audits API/env/account capability in redacted preflight mode, and keeps hard live submit blocked.

## Decision
- `decision`: `LIVE_REAL_PREFLIGHT_GATE_READY_API_ENV_ACCOUNT_AUDIT_HARD_SUBMIT_BLOCKED_NO_LIVE_REAL_ORDER`
- `approved_for_live_real_preflight_gate`: `True`
- `approved_for_live_real_readiness_candidate`: `True`
- `source_30u_promotion_review_verified`: `True`
- `api_env_capability_audit_verified`: `True`
- `account_capability_audit_verified`: `True`
- `hard_live_submit_block_verified`: `True`
- `order_action_count`: `0`
- `exchange_submit_count`: `0`
- `network_submit_count`: `0`
- `approved_for_exchange_submit`: `False`
- `approved_for_live_real`: `False`
- `live_real_order_performed`: `False`

## Capability audit
- `api_key_redacted`: `absent`
- `api_secret_redacted`: `absent`
- `account_capability_mode`: `offline_redacted_audit`

## Reason codes
- `LIVE_REAL_PREFLIGHT_GATE_READY`
