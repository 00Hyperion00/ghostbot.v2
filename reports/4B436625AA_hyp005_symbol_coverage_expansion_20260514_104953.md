# HYP-005 Controlled Symbol Coverage Expansion Gate — 4B.4.3.6.6.25AA

- decision: `HYP005_SYMBOL_COVERAGE_EXPANSION_READY`
- ok: `True`
- hypothesis_id: `HYP-005`
- selected_strategy_family: `long_liquidity_sweep_reversal`
- symbol_count: `10`
- baseline_symbol_count: `4`
- expansion_symbol_count: `6`
- source_shadow_observation_count: `0`
- source_shadow_sample_target: `30`
- paper_transition_ready: `False`

## Approved Symbols

- `BTCUSDT`
- `ETHUSDT`
- `SOLUSDT`
- `BNBUSDT`
- `XRPUSDT`
- `DOGEUSDT`
- `ADAUSDT`
- `AVAXUSDT`
- `LINKUSDT`
- `LTCUSDT`

## Risk Permissions

- approved_for_shadow_collection: `True`
- approved_for_scheduler_regeneration: `True`
- approved_for_paper_candidate: `False`
- approved_for_live_real: `False`
- post_requests_allowed: `False`

## Reason Codes

- `HYP005_10_SYMBOL_COVERAGE_APPROVED_FOR_SHADOW_COLLECTION_ONLY`
- `NO_TRAINING_PAPER_LIVE_APPROVALS_DETECTED`

## Warnings

- `SHADOW_SAMPLE_COUNT_STILL_ZERO`

## Next Scheduler Symbols Arg

```text
BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,XRPUSDT,DOGEUSDT,ADAUSDT,AVAXUSDT,LINKUSDT,LTCUSDT
```

## Recommendation

HYP-005 controlled 10-symbol coverage expansion is ready for no-order shadow collection. Regenerate the 25Z scheduler pack with the emitted symbol list; do not train, reload, paper trade, live trade, or send orders.

Paper/live/order permissions remain closed.
