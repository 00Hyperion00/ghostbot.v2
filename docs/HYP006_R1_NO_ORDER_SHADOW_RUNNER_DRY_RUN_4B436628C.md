# 4B.4.3.6.6.28C HYP-006-R1 No-Order Shadow Runner Dry-Run

This patch adds a research-only dry-run runner for `HYP-006-R1`.

## Guarantees

- No order placement.
- No paper/live enablement.
- No training or model reload.
- No scheduler task creation or mutation.
- No strategy parameter mutation.
- Public market-data GET only when the runner is explicitly executed without `--input-csv`.
- Checker/tests are offline and read-only.

## Purpose

The patch verifies that the `28B` HYP-006 candidate spec can be consumed by a no-order dry-run runner and produces a dry-run ledger using short-side forward return probes.

## Gate state

`28C` can mark the runner and canonical scheduler registration preflight as ready for operator review, but it keeps actual shadow collection disabled. The next gate is:

`28D_CANONICAL_NO_ORDER_SHADOW_COLLECTION_SCHEDULER_REGISTRATION_OPERATOR_APPROVAL`
