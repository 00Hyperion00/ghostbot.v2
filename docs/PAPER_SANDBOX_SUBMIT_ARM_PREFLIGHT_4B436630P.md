# 4B.4.3.6.6.30P Paper Sandbox Submit-Arm Preflight

Purpose: consume the 30O-H6 reconciliation proof and verify sandbox submit readiness before the first sandbox canary submit phase.

Scope:
- Consumes latest `4B436630O_paper_sandbox_execution_reconciliation_gate_*_ready.json`.
- Verifies API mode and sandbox/testnet endpoint.
- Verifies minNotional, lot-size step, risk caps, and kill-switch.
- Builds an order request skeleton for audit only.
- Keeps exchange submit blocked.
- Keeps paper sandbox canary submit blocked until 30Q.
- Keeps live-real blocked.

Ready decision:
`PAPER_SANDBOX_SUBMIT_ARM_PREFLIGHT_READY_SUBMIT_STILL_BLOCKED_NO_LIVE_REAL`
