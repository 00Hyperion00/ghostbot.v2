# 4B.4.3.6.6.25S HYP-005 Liquidity Sweep Reversal Exploration Gate

- contract_version: `4B.4.3.6.6.25S`
- decision: **HYP005_EXPLORATION_PASS**
- hypothesis_id: `HYP-005`
- branch_name: `liquidity_sweep_reversal_vol_compression`
- source: `binance-spot:BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT:4h:90d`
- symbols: `BNBUSDT,BTCUSDT,ETHUSDT,SOLUSDT`
- candidate_count: `4`
- passed_candidate_count: `2`
- selected_strategy_family: `long_liquidity_sweep_reversal`
- selected_signal_count: `28`
- selected_mean_net_edge_bps: `140.089198`
- selected_median_net_edge_bps: `109.881101`
- selected_profit_factor: `4.197094`
- selected_oos_mean_net_edge_bps: `104.924999`
- selected_walk_forward_positive_rate_pct: `75.0`
- approved_for_research_candidate: `True`
- approved_for_training_candidate: `False`
- approved_for_paper_candidate: `False`
- approved_for_live_real: `False`
- reason_codes: `[]`
- recommendation: HYP-005 produced a research-only liquidity sweep reversal candidate. Do not train, reload, paper trade, or enable live trading; move to a dedicated robustness gate first.

## Candidates

| strategy | decision | score | signals | mean | median | PF | OOS | WF+ | reasons |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| long_liquidity_sweep_reversal | PASS | 307.40605 | 28 | 140.089198 | 109.881101 | 4.197094 | 104.924999 | 75.0 | `[]` |
| short_liquidity_sweep_reversal | PASS | 110.748249 | 28 | 32.700549 | 37.304538 | 1.508396 | 76.717471 | 75.0 | `[]` |
| compression_sweep_reversal | BLOCK | 182.00264 | 18 | 97.553038 | 111.349408 | 2.518628 | -30.738823 | 75.0 | `['HYP005_SIGNAL_COUNT_LOW', 'HYP005_OOS_EDGE_LOW', 'HYP005_TOP_WIN_DEPENDENCY_HIGH']` |
| compression_breakout_fakeout_probe | BLOCK | 45.929656 | 62 | 19.187385 | -12.634989 | 1.25104 | 48.317848 | 75.0 | `['DIAGNOSTIC_STRATEGY_NOT_APPROVABLE', 'HYP005_MEDIAN_EDGE_LOW']` |

## Guardrails

- observation_only: `True`
- public_market_data_get_only: `True`
- post_requests_allowed: `False`
- config_mutation_performed: `False`
- order_actions_performed: `False`
- reload_performed: `False`
- live_real_allowed: `False`
- Training remains blocked.
- Paper/live remain blocked.
