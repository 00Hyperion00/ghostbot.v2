# 4B.4.3.6.6.30M Paper Sandbox Execution Preflight

Purpose: consume the 30L-H2 accepted candidate-only unlock, require explicit paper sandbox dry-run authorization, build an internal order envelope, and keep exchange submit plus live-real blocked.

Scope:
- Consumes latest `4B436630L_paper_sandbox_candidate_unlock_gate_*_ready.json`.
- Requires explicit operator id, authorization token, and issued dry-run authorization.
- Builds an internal order envelope for paper sandbox preflight only.
- Does not perform paper sandbox dry-run execution.
- Does not submit to exchange.
- Does not enable live-real.

Ready decision:
`PAPER_SANDBOX_EXECUTION_PREFLIGHT_READY_ORDER_ENVELOPE_BUILT_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL`
