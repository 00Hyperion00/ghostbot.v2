# 4B.4.3.6.6.25AC — HYP-005 Symbol Risk Pruning / Candidate Continuation Decision Gate

## Purpose

This patch evaluates HYP-005 after canonical-deduped no-order shadow collection reaches the evidence target. It compares the full 10-symbol baseline against controlled symbol-risk pruning scenarios, including AVAXUSDT, DOGEUSDT, and the combined AVAXUSDT+DOGEUSDT removal case.

## Safety contract

- Observation-only decision gate.
- Reuses 25AB-H2 canonical deduplication.
- Does not mutate scheduler configuration.
- Does not regenerate the scheduler pack.
- Does not train or reload a model.
- Does not start paper trading.
- Does not enable live trading.
- Does not send POST requests or orders.
- Paper/live remain blocked.

Any recommended symbol-set change requires a separate operator-reviewed patch.

## Decisions

- `HYP005_CONTINUE_WITH_BASELINE_SYMBOLS`
- `HYP005_CONTINUE_WITH_PRUNED_SYMBOL_SET`
- `HYP005_BRANCH_REFINEMENT_REQUIRED`
- `HYP005_BRANCH_CLOSURE_RECOMMENDED`

## Scenario audit

The gate emits:

- baseline metrics,
- individual risk-symbol removal scenarios,
- combined high-slippage-symbol removal scenario,
- per-symbol edge, PF, slippage, tail-loss, and missing-field summaries,
- a recommended no-order symbol-set candidate,
- a recommendation that requires a separate operator patch before scheduler mutation.
