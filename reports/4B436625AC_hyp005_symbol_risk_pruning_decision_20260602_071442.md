# HYP-005 Symbol Risk Pruning / Candidate Continuation Decision Gate

- contract_version: `4B.4.3.6.6.25AC`
- decision: `HYP005_BRANCH_REFINEMENT_REQUIRED`
- generated_at_utc: `2026-06-02T07:14:42Z`
- canonical_unique_observation_count: `31`
- baseline_mean_forward_edge_bps: `-15.642778`
- baseline_profit_factor: `0.783427`
- selected_scenario: `PRUNE_AVAXUSDT_DOGEUSDT`
- recommended_pruned_symbols: `AVAXUSDT,DOGEUSDT`
- recommended_symbols_arg: `ADAUSDT,BNBUSDT,BTCUSDT,ETHUSDT,LINKUSDT,LTCUSDT,SOLUSDT,XRPUSDT`

## Safety

This gate does not mutate scheduler config, train models, reload models, start paper trading, enable live trading, send POST requests, or send orders.

## Scenario Comparisons

- BASELINE_ALL_SYMBOLS: excluded=none, matured=25, mean_edge=-15.642778, median_edge=16.225838, pf=0.783427, win_rate=56.0, high_slip=2, tail_losses=7, passes=False
- PRUNE_AVAXUSDT: excluded=AVAXUSDT, matured=21, mean_edge=-10.226795, median_edge=52.576236, pf=0.86765, win_rate=61.904762, high_slip=1, tail_losses=6, passes=False
- PRUNE_DOGEUSDT: excluded=DOGEUSDT, matured=21, mean_edge=-9.175401, median_edge=16.225838, pf=0.851728, win_rate=57.142857, high_slip=1, tail_losses=6, passes=False
- PRUNE_AVAXUSDT_DOGEUSDT: excluded=AVAXUSDT,DOGEUSDT, matured=17, mean_edge=-0.963333, median_edge=52.576236, pf=0.985332, win_rate=64.705882, high_slip=0, tail_losses=5, passes=False

## Per-Symbol Risk

- ADAUSDT: count=2, matured=1, mean_edge=59.031877, pf=999.0, max_slip=8.684211, tail_losses=0, flags=none
- AVAXUSDT: count=4, matured=4, mean_edge=-44.076691, pf=0.03673, max_slip=12.717391, tail_losses=1, flags=SYMBOL_SLIPPAGE_PROXY_HIGH,SYMBOL_TAIL_LOSS_PRESENT,SYMBOL_MEAN_FORWARD_EDGE_NEGATIVE,SYMBOL_PROFIT_FACTOR_LOW
- BNBUSDT: count=2, matured=2, mean_edge=20.888489, pf=999.0, max_slip=3.988721, tail_losses=0, flags=none
- BTCUSDT: count=3, matured=1, mean_edge=158.648312, pf=999.0, max_slip=5.487664, tail_losses=0, flags=SYMBOL_TRUE_REQUIRED_FIELDS_MISSING_HIGH
- DOGEUSDT: count=4, matured=4, mean_edge=-49.596507, pf=0.608081, max_slip=15.634462, tail_losses=1, flags=SYMBOL_SLIPPAGE_PROXY_HIGH,SYMBOL_TAIL_LOSS_PRESENT,SYMBOL_MEAN_FORWARD_EDGE_NEGATIVE,SYMBOL_PROFIT_FACTOR_LOW
- ETHUSDT: count=3, matured=3, mean_edge=2.516069, pf=1.033118, max_slip=7.236468, tail_losses=1, flags=SYMBOL_TAIL_LOSS_PRESENT
- LINKUSDT: count=4, matured=3, mean_edge=-67.682101, pf=0.410343, max_slip=7.530573, tail_losses=1, flags=SYMBOL_TAIL_LOSS_PRESENT,SYMBOL_MEAN_FORWARD_EDGE_NEGATIVE,SYMBOL_PROFIT_FACTOR_LOW,SYMBOL_TRUE_REQUIRED_FIELDS_MISSING_HIGH
- LTCUSDT: count=1, matured=1, mean_edge=76.165707, pf=999.0, max_slip=4.012632, tail_losses=0, flags=none
- SOLUSDT: count=2, matured=1, mean_edge=83.682008, pf=999.0, max_slip=4.799409, tail_losses=0, flags=SYMBOL_TRUE_REQUIRED_FIELDS_MISSING_HIGH
- XRPUSDT: count=6, matured=5, mean_edge=-48.036691, pf=0.558676, max_slip=11.729452, tail_losses=3, flags=SYMBOL_TAIL_LOSS_PRESENT,SYMBOL_MEAN_FORWARD_EDGE_NEGATIVE,SYMBOL_PROFIT_FACTOR_LOW

## Reason Codes

- `CANDIDATE_REFINEMENT_REQUIRED_BEFORE_TRANSITION`
- `CANONICAL_DEDUPLICATION_REUSED_FROM_25AB_H2`
- `NO_AUTOMATIC_SYMBOL_CONFIG_MUTATION`
- `NO_SYMBOL_SCENARIO_PASSES_CONTINUATION_GATE`
- `NO_TRAINING_PAPER_LIVE_APPROVALS_DETECTED`
- `SYMBOL_PRUNING_SCENARIO_ANALYSIS_COMPLETED`

## Warnings

- `BASELINE_MEAN_FORWARD_EDGE_NEGATIVE`
- `BASELINE_PROFIT_FACTOR_LOW`
- `BASELINE_SHADOW_SLIPPAGE_PROXY_HIGH`

## Recommendation

HYP-005 requires branch refinement. No controlled symbol scenario currently passes the continuation gate. Continue no-order analysis only; do not train, reload, paper trade, live trade, mutate scheduler config, or send orders.
