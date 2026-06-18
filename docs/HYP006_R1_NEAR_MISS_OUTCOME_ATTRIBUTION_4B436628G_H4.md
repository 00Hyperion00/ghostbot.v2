# 4B.4.3.6.6.28G-H4 HYP-006 Near-Miss Outcome Attribution

Read-only, no-order research report for HYP-006-R1 near-miss events emitted by the 28G-H3 runtime candidate scan hook.

## Scope

- Loads the latest 28G-H3 runtime candidate scan artifact.
- Attributes sampled near-miss events to forward short-probe returns using public market data or an operator-supplied OHLCV CSV.
- Aggregates outcome by failed gate combo, symbol, and risk bucket.
- Compares near-miss outcomes with existing canonical trigger ledger rows when available.

## Non-scope

- No parameter mutation.
- No threshold relaxation.
- No scheduler mutation.
- No config mutation.
- No training or reload.
- No paper/live/order enablement.

## Required interpretation

Any positive gate-combo outcome is only a counterfactual research signal. It does not authorize paper, live, model training, model reload, strategy parameter mutation, or order placement.
