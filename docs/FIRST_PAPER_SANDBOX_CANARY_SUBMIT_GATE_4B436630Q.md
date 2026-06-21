# 4B.4.3.6.6.30Q First Paper Sandbox Canary Submit Gate

Purpose: consume the accepted 30P-H3 submit-arm preflight, require explicit operator canary approval, build one sandbox/demo order intent, and keep the exchange submit path guarded with no live-real.

Scope:
- Consumes latest valid `4B436630P_paper_sandbox_submit_arm_preflight_*_ready.json`.
- Requires explicit operator id and approval token.
- Verifies API mode, sandbox endpoint, minNotional, lot-size, risk caps, and kill-switch.
- Builds `4B436630Q_single_canary_order_intent.json` only when explicitly approved.
- Does not submit to exchange.
- Does not enable live-real.

Ready decision:
`FIRST_PAPER_SANDBOX_CANARY_SUBMIT_GATE_READY_ORDER_INTENT_BUILT_SUBMIT_GUARDED_NO_LIVE_REAL`
