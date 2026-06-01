# 4B.4.3.6.6.25W HYP-005 Shadow Observation Acceptance / Paper-Transition Readiness Gate

- contract_version: `4B.4.3.6.6.25W`
- decision: **HYP005_SHADOW_PAPER_TRANSITION_BLOCK**
- hypothesis_id: `HYP-005`
- branch_name: `liquidity_sweep_reversal_vol_compression`
- selected_strategy_family: `long_liquidity_sweep_reversal`
- paper_transition_ready: `False`
- approved_for_paper_transition_candidate: `False`
- approved_for_paper_candidate: `False`
- approved_for_live_real: `False`
- reason_codes: `['HYP005_SHADOW_LEDGER_ACCEPTANCE_NOT_MET', 'SHADOW_DAYS_OBSERVED_LOW', 'SHADOW_MEAN_FORWARD_EDGE_LOW', 'SHADOW_MEDIAN_FORWARD_EDGE_LOW', 'SHADOW_OOS_EDGE_LOW', 'SHADOW_PROFIT_FACTOR_LOW', 'SHADOW_WALK_FORWARD_STABILITY_LOW']`
- warnings: `[]`
- recommendation: HYP-005 shadow observations did not meet paper-transition readiness. Keep collecting no-order shadow observations; do not train, reload, paper trade, or enable live trading.

## Shadow Acceptance Summary

- shadow_observation_count: `56`
- shadow_days_observed: `5`
- shadow_signal_capture_count: `56`
- shadow_mean_forward_edge_bps: `-39.400376`
- shadow_median_forward_edge_bps: `-21.030494`
- shadow_profit_factor: `0.495675`
- shadow_oos_edge_bps: `-41.608303`
- shadow_walk_forward_positive_rate_pct: `0.0`
- shadow_top_win_dependency_pct: `7.664608`
- shadow_dominant_symbol_pct: `21.428571`
- shadow_wick_dependency_pct: `57.479241`
- shadow_slippage_proxy_bps: `6.95993`
- shadow_data_quality_pct: `100.0`
- shadow_missing_fields_pct: `0.0`

## Guardrails

- no_order_shadow_only: `True`
- paper_transition_readiness_only: `True`
- orders_allowed: `False`
- paper_trading_allowed: `False`
- live_trading_allowed: `False`
- post_requests_allowed: `False`
- Paper-transition readiness is not paper-trading permission.
- Paper trading remains blocked until a separate gate explicitly enables it.
- Live trading remains blocked.
