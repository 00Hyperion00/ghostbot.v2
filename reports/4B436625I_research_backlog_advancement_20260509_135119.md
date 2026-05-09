# 4B.4.3.6.6.25I Research Backlog Advancement / Next Hypothesis Selection Gate

- contract_version: `4B.4.3.6.6.25I`
- decision: **NEXT_HYPOTHESIS_SELECTED**
- source_reports: `15`
- registry_source: `builtin_default`
- closed_hypothesis_id: `HYP-002`
- closed_branch_name: `futures_funding_trend_exhaustion`
- selected_next_hypothesis_id: `HYP-003`
- selected_next_hypothesis_title: `Regime-filtered volatility expansion breakout`
- approved_for_research_candidate: `True`
- approved_for_training_candidate: `False`
- approved_for_paper_candidate: `False`
- approved_for_live_real: `False`
- reason_codes: `['HYPOTHESIS_CLOSURE_EVIDENCE_CONFIRMED', 'NEXT_HYPOTHESIS_SELECTED']`
- recommendation: Advance to HYP-003 as research-only. Do not train, reload, start paper trading, or enable live trading; run its dedicated exploration gate first.

## Closure Evidence

- source_report: `reports\4B436625H_futures_branch_closure_evidence_pack_20260509_014428.json`
- decision: `FUTURES_BRANCH_CLOSURE_CONFIRMED`
- final_25f_decision: `BRANCH_CLOSED_NO_GO`
- primary_terminal_block_count: `5`
- companion_terminal_block_count: `2`
- approvals_detected: `False`

## Next Hypothesis

- hypothesis_id: `HYP-003`
- title: `Regime-filtered volatility expansion breakout`
- family: `volatility_breakout`
- priority: `30`
- status: `REGISTERED`
- training_allowed_if_pass: `False`
- paper_allowed_if_pass: `False`
- live_allowed_if_pass: `False`
- acceptance_metrics: `{'min_sample_count': 250, 'min_signal_count': 35, 'min_mean_net_edge_bps': 0.0, 'min_median_net_edge_bps': 0.0, 'min_profit_factor': 1.2, 'min_walk_forward_positive_rate_pct': 60.0, 'max_top_win_dependency_pct': 35.0, 'max_drawdown_pct': 25.0}`

## Backlog Snapshot

| hypothesis_id | status | priority | family | title |
|---|---|---:|---|---|
| HYP-001 | BLOCKED | 10 | spot_or_futures_trend | Higher timeframe trend following |
| HYP-002 | CLOSED_NO_GO | 20 | futures_funding | Futures funding/open-interest trend exhaustion |
| HYP-003 | REGISTERED | 30 | volatility_breakout | Regime-filtered volatility expansion breakout |
| HYP-004 | REGISTERED | 40 | vwap_reversion | Session-aware VWAP reversion with volatility guard |
| HYP-005 | REGISTERED | 50 | cross_symbol_relative_strength | Cross-symbol liquidity rotation edge |

## Guardrails

- observation_only: `True`
- no_post_actions: `True`
- post_requests_allowed: `False`
- config_mutation_performed: `False`
- order_actions_performed: `False`
- reload_performed: `False`
- training_allowed: `False`
- paper_allowed: `False`
- live_real_allowed: `False`
- new_hypothesis_requires_future_acceptance_gate: `True`

## Policy

This gate only advances the research backlog. It never trains models, reloads models, mutates config, starts paper trading, enables live trading, or sends orders. A selected next hypothesis must still pass a future dedicated exploration gate.
