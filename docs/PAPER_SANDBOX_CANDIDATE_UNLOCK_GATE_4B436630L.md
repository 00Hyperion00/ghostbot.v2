# 4B.4.3.6.6.30L Paper Sandbox Candidate Unlock Gate

Purpose: consume the 30K final go/no-go ready report, require explicit paper candidate unlock, run sandbox-only order enablement preflight, and keep exchange submit plus live-real blocked.

Scope:
- Consumes latest `4B436630K_paper_sandbox_operator_final_go_no_go_gate_*_ready.json`.
- Requires explicit operator id, unlock token, and issued candidate unlock.
- Verifies sandbox-only settings, kill-switch, risk caps, and no live-real state.
- Approves paper sandbox candidate status only.
- Does not enable paper sandbox dry-run execution.
- Does not submit to exchange.
- Does not enable live-real.

Ready decision:
`PAPER_SANDBOX_CANDIDATE_UNLOCK_GATE_READY_PAPER_CANDIDATE_UNLOCKED_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL`
