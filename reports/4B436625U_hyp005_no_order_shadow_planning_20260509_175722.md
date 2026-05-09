# 4B.4.3.6.6.25U HYP-005 No-Order Shadow Planning / Candidate Spec Gate

- contract_version: `4B.4.3.6.6.25U`
- decision: **HYP005_SHADOW_PLAN_READY**
- hypothesis_id: `HYP-005`
- branch_name: `liquidity_sweep_reversal_vol_compression`
- selected_strategy_family: `long_liquidity_sweep_reversal`
- shadow_plan_ready: `True`
- no_order_shadow_only: `True`
- shadow_min_samples: `30`
- signal_count: `28`
- penalized_mean_net_edge_bps: `122.089198`
- median_net_edge_bps: `109.881101`
- profit_factor: `4.197094`
- oos_mean_net_edge_bps: `104.924999`
- approved_for_research_candidate: `True`
- approved_for_training_candidate: `False`
- approved_for_paper_candidate: `False`
- approved_for_live_real: `False`
- reason_codes: `['HYP005_EXPLORATION_PASS_CONFIRMED', 'HYP005_ROBUSTNESS_PASS_CONFIRMED', 'NO_ORDER_SHADOW_PLAN_READY', 'NO_TRAINING_PAPER_LIVE_APPROVALS_DETECTED']`
- warnings: `['SHADOW_SMALL_SAMPLE_CAUTION_REQUIRED']`
- recommendation: HYP-005 no-order shadow plan is ready. Do not train, reload, paper trade, or enable live trading; collect shadow observations and require a separate paper-transition gate.

## Candidate Spec Summary

- status: `NO_ORDER_SHADOW_PLAN_READY`
- execution_mode: `NO_ORDER_SHADOW_ONLY`
- paper_transition_requires_new_gate: `True`
- live_transition_requires_separate_gate: `True`

## Required Shadow Acceptance Metrics

| metric | operator | threshold | required |
|---|---:|---:|---:|
| `shadow_sample_count` | `>=` | `30` | `True` |
| `shadow_days_observed` | `>=` | `30` | `True` |
| `shadow_signal_capture_count` | `>=` | `25` | `True` |
| `shadow_mean_forward_edge_bps` | `>=` | `50.0` | `True` |
| `shadow_median_forward_edge_bps` | `>=` | `30.0` | `True` |
| `shadow_profit_factor` | `>=` | `1.5` | `True` |
| `shadow_oos_edge_bps` | `>=` | `25.0` | `True` |
| `shadow_walk_forward_positive_rate_pct` | `>=` | `60.0` | `True` |
| `shadow_top_win_dependency_pct` | `<=` | `45.0` | `True` |
| `shadow_dominant_symbol_pct` | `<=` | `70.0` | `True` |
| `shadow_wick_dependency_pct` | `<=` | `85.0` | `True` |
| `shadow_slippage_proxy_bps` | `<=` | `12.0` | `True` |
| `shadow_data_quality_pct` | `>=` | `98.0` | `True` |
| `shadow_missing_fields_pct` | `<=` | `1.0` | `True` |
| `manual_reviewers` | `>=` | `1` | `True` |

## Guardrails

- observation_only: `True`
- no_order_shadow_only: `True`
- orders_allowed: `False`
- training_allowed: `False`
- paper_trading_allowed: `False`
- live_trading_allowed: `False`
- model_reload_allowed: `False`
- config_mutation_allowed: `False`
- post_requests_allowed: `False`
- Training remains blocked.
- Paper/live remain blocked.
