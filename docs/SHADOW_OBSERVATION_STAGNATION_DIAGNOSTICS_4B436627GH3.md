# 4B.4.3.6.6.27G-H3 — Shadow Observation Stagnation Diagnostics

This patch adds a read-only diagnostic layer for HYP-005-R1 canonical shadow observation stagnation.

It does not mutate scheduler registration, runtime config, model state, paper trading, live trading, or order execution.

## What it reports

- latest ledger sample count and latest observation timestamp,
- exact candidate count from current OHLCV scan,
- duplicate candidate count versus the existing merged ledger,
- new unique candidate count,
- near-miss candidate count,
- per-filter rejection counts,
- top bottleneck filter,
- no-order research recommendation.

## Safety contract

- `read_only = true`
- `no_order_research_diagnostics_only = true`
- `approved_for_paper_candidate = false`
- `approved_for_live_real = false`
- `order_actions_performed = false`
- `trading_action_performed = false`

The report may perform public market-data GET requests only when no CSV is supplied and `--offline` is not set. It never sends POST requests and never sends orders.
