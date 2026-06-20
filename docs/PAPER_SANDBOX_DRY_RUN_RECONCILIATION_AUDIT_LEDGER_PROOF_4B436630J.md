# 4B.4.3.6.6.30J Paper Sandbox Dry-run Reconciliation + Audit Ledger Proof

Purpose: consume the 30I internal simulated fill ledger, reconcile order/fill/position/balance with mismatch=0, mirror the proof into SQLite audit storage, and keep exchange submit, real paper execution, paper candidate, and live-real blocked.

Scope:
- Consumes latest `4B436630I_paper_sandbox_dry_run_internal_execution_harness_*_ready.json`.
- Consumes `4B436630I_internal_simulated_fill_ledger.jsonl`.
- Reconciles order notional, fill notional, position quantity, quote balance delta, and base balance delta.
- Requires mismatch count to remain `0` within strict tolerance.
- Mirrors synthetic order/fill/position/balance/risk/operator audit rows into SQLite.
- Does not submit to exchange.
- Does not enable paper execution, paper candidate, runtime overlays, training/reload, strategy mutation, or live-real.

Expected ready decision:
`PAPER_SANDBOX_DRY_RUN_RECONCILIATION_AUDIT_LEDGER_PROOF_READY_MISMATCH_ZERO_NO_EXCHANGE_SUBMIT_PAPER_CANDIDATE_BLOCKED_LIVE_REAL_BLOCKED`
