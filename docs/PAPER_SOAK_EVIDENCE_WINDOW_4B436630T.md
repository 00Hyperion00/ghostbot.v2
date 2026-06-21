# 4B.4.3.6.6.30T Paper Soak / Evidence Window

Purpose: consume the accepted 30S guarded runtime evidence, run a deterministic multi-cycle paper soak window, prove cap/kill-switch continuity, and keep exchange submit/live-real disabled.

Scope:
- Consumes latest valid `4B436630S_paper_mode_runtime_guardrail_*_ready.json`.
- Builds multi-cycle soak observations with no trading action, no order action, no network submit, and no exchange submit.
- Enforces strict continuity: minimum cycle count, cycle cap, zero order actions, zero exchange submits, zero network submit attempts, zero notional, and kill-switch enabled for every cycle.
- Produces evidence only.
- Does not mutate strategy parameters.
- Does not activate exchange submit.
- Does not activate live-real.

Ready decision:
`PAPER_SOAK_EVIDENCE_WINDOW_READY_MULTI_CYCLE_CAPS_KILL_SWITCH_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL`
