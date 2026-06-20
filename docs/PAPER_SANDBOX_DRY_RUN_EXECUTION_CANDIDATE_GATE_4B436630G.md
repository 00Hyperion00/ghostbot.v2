# 4B.4.3.6.6.30G Paper Sandbox Dry-run Execution Candidate Gate

This phase consumes the latest 30F ready transition-plan evidence and verifies a dry-run-only execution candidate gate.

Fail-closed guarantees:

- It verifies the 30F transition plan before creating any candidate state.
- It verifies a dry-run-only runtime envelope.
- It builds exactly one simulated paper intent.
- It never submits to the exchange.
- It never marks `approved_for_paper_sandbox_dry_run_execution=True`.
- It never marks `approved_for_exchange_submit=True`.
- It never marks `approved_for_paper_transition_candidate=True`.
- It never marks `approved_for_paper_candidate=True`.
- It never marks `approved_for_live_real=True`.
- It performs no order, runtime overlay, training, reload, scheduler mutation, or strategy parameter mutation.
