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
- reason_codes: `['HYP005_SHADOW_LEDGER_ACCEPTANCE_NOT_MET', 'SHADOW_DAYS_OBSERVED_LOW', 'SHADOW_MEAN_FORWARD_EDGE_LOW', 'SHADOW_MEDIAN_FORWARD_EDGE_LOW', 'SHADOW_MISSING_FIELDS_HIGH', 'SHADOW_OOS_EDGE_LOW', 'SHADOW_PROFIT_FACTOR_LOW', 'SHADOW_SAMPLE_COUNT_LOW', 'SHADOW_WALK_FORWARD_STABILITY_LOW']`
- warnings: `['SHADOW_SAMPLE_COUNT_BELOW_ACCEPTANCE_TARGET']`
- recommendation: HYP-005 shadow observations did not meet paper-transition readiness. Keep collecting no-order shadow observations; do not train, reload, paper trade, or enable live trading.

## Shadow Acceptance Summary

- shadow_observation_count: `28`
- shadow_days_observed: `4`
- shadow_signal_capture_count: `28`
- shadow_mean_forward_edge_bps: `-96.079626`
- shadow_median_forward_edge_bps: `-65.217391`
- shadow_profit_factor: `0.127618`
- shadow_oos_edge_bps: `-132.382485`
- shadow_walk_forward_positive_rate_pct: `0.0`
- shadow_top_win_dependency_pct: `25.0`
- shadow_dominant_symbol_pct: `42.857143`
- shadow_wick_dependency_pct: `57.147043`
- shadow_slippage_proxy_bps: `8.416221`
- shadow_data_quality_pct: `100.0`
- shadow_missing_fields_pct: `3.174603`

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
