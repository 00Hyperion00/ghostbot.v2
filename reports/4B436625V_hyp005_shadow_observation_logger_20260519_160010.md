# 4B.4.3.6.6.25V HYP-005 Shadow Observation Logger / No-Order Runtime Probe Gate

- contract_version: `4B.4.3.6.6.25V`
- decision: **HYP005_SHADOW_OBSERVATION_LOGGER_BLOCK**
- hypothesis_id: `HYP-005`
- branch_name: `liquidity_sweep_reversal_vol_compression`
- selected_strategy_family: `long_liquidity_sweep_reversal`
- timeframe: `4h`
- shadow_observation_count: `12`
- shadow_sample_target: `30`
- shadow_sample_target_met: `False`
- approved_for_shadow_candidate: `False`
- approved_for_training_candidate: `False`
- approved_for_paper_candidate: `False`
- approved_for_live_real: `False`
- reason_codes: `['NO_ORDER_SHADOW_LEDGER_NOT_READY', 'SHADOW_MISSING_FIELDS_HIGH']`
- warnings: `['SHADOW_SAMPLE_COUNT_BELOW_ACCEPTANCE_TARGET', 'SHADOW_SLIPPAGE_PROXY_HIGH']`
- recommendation: HYP-005 shadow observation logger is blocked. Fix candidate spec/data quality before collecting shadow observations; do not train, reload, paper trade, or enable live trading.

## Shadow Summary

- shadow_mean_forward_edge_bps: `-50.440123`
- shadow_median_forward_edge_bps: `22.292402`
- shadow_profit_factor: `0.360753`
- shadow_data_quality_pct: `100.0`
- shadow_missing_fields_pct: `1.388889`
- shadow_slippage_proxy_bps: `15.634462`

## Guardrails

- no_order_shadow_only: `True`
- runtime_probe_only: `True`
- orders_allowed: `False`
- training_allowed: `False`
- paper_trading_allowed: `False`
- live_trading_allowed: `False`
- post_requests_allowed: `False`
- Candidate observations are not trading permission.
- Training remains blocked.
- Paper/live remain blocked.
