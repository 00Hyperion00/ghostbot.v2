# 4B.4.3.6.6.30T Paper Soak / Evidence Window

Consumes 30S guarded runtime, runs multi-cycle paper soak evidence, verifies cap/kill-switch continuity, and keeps exchange submit/live-real blocked.

## Decision
- `decision`: `PAPER_SOAK_EVIDENCE_WINDOW_READY_MULTI_CYCLE_CAPS_KILL_SWITCH_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL`
- `approved_for_paper_soak_evidence_window`: `True`
- `source_30s_guardrail_verified`: `True`
- `multi_cycle_soak_verified`: `True`
- `cap_continuity_verified`: `True`
- `kill_switch_continuity_verified`: `True`
- `soak_cycle_count`: `5`
- `minimum_soak_cycles_required`: `3`
- `order_action_count`: `0`
- `exchange_submit_count`: `0`
- `network_submit_count`: `0`
- `approved_for_exchange_submit`: `False`
- `approved_for_live_real`: `False`

## Reason codes
- `PAPER_SOAK_EVIDENCE_WINDOW_READY`
