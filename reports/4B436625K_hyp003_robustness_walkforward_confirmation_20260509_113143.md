# 4B.4.3.6.6.25K HYP-003 Robustness / Walk-Forward Confirmation Gate

- contract_version: `4B.4.3.6.6.25K`
- decision: **HYP003_ROBUSTNESS_BLOCK**
- hypothesis_id: `HYP-003`
- selected: `ETHUSDT 4h range_mean_reversion range`
- signal_count: `66`
- mean_net_edge_bps: `-11.606522`
- median_net_edge_bps: `-24.400868`
- profit_factor: `0.74203`
- win_rate_pct: `37.878788`
- walk_forward_positive_rate_pct: `25.0`
- approved_for_research_candidate: `False`
- approved_for_training_candidate: `False`
- approved_for_paper_candidate: `False`
- approved_for_live_real: `False`
- reason_codes: `['ROBUST_MEAN_EDGE_LOW', 'ROBUST_MEDIAN_EDGE_LOW', 'ROBUST_OOS_EDGE_LOW', 'ROBUST_PROFIT_FACTOR_LOW', 'ROBUST_WALK_FORWARD_STABILITY_LOW', 'ROBUST_WIN_RATE_LOW']`
- recommendation: HYP-003 candidate failed robustness/walk-forward confirmation. Do not train, reload, paper trade, or enable live trading; refine or close this candidate.

## Walk-Forward Segments

| segment | decision | signals | mean_edge_bps | median_edge_bps | profit_factor | win_rate_pct | reasons |
|---|---|---:|---:|---:|---:|---:|---|
| wf_1 | BLOCK | 17 | 0.333307 | -35.690778 | 1.006764 | 47.058824 | `('SEGMENT_MEDIAN_EDGE_LOW', 'SEGMENT_PROFIT_FACTOR_LOW')` |
| wf_2 | BLOCK | 17 | -2.320304 | -10.956641 | 0.948059 | 35.294118 | `('SEGMENT_MEAN_EDGE_LOW', 'SEGMENT_MEDIAN_EDGE_LOW', 'SEGMENT_PROFIT_FACTOR_LOW')` |
| wf_3 | BLOCK | 16 | -29.295574 | -26.746929 | 0.351588 | 31.25 | `('SEGMENT_MEAN_EDGE_LOW', 'SEGMENT_MEDIAN_EDGE_LOW', 'SEGMENT_PROFIT_FACTOR_LOW')` |
| wf_4 | BLOCK | 16 | -16.470144 | -24.841013 | 0.594197 | 37.5 | `('SEGMENT_MEAN_EDGE_LOW', 'SEGMENT_MEDIAN_EDGE_LOW', 'SEGMENT_PROFIT_FACTOR_LOW')` |

## OOS Segment

- decision: `BLOCK`
- mean_net_edge_bps: `-21.839317`
- median_net_edge_bps: `-24.841013`

## Guardrails

- observation_only: `True`
- public_market_data_get_only: `True`
- post_requests_allowed: `False`
- config_mutation_performed: `False`
- order_actions_performed: `False`
- reload_performed: `False`
- live_real_allowed: `False`
- training_allowed: `False`
- paper_allowed: `False`

## Policy

This gate never trains models, reloads models, mutates config, starts paper trading, enables live trading, or sends orders. PASS is research-only.
