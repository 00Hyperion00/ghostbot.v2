# 4B.4.3.6.6.25A Multi-Timeframe Alpha Discovery / Research Reset

- contract_version: `4B.4.3.6.6.25A`
- decision: **PASS**
- candidate_count: `7`
- approved_for_training_candidate: `True`
- approved_for_paper_candidate: `False`
- approved_for_live_real: `False`
- selected_policy: `mtf_15m_h8_cost16_edge30_atr2_5`
- selected_interval: `15m`
- selected_score: `141.343892`
- selected_action_pct: `17.6683`
- selected_min_expected_net_edge_bps: `95.0002`
- recommendation: A multi-timeframe alpha candidate passed the research gate. Use it only for controlled offline retrain research; paper/live remain blocked.

## Guardrails

- observation_only: `True`
- get_only_public_market_data: `True`
- post_requests_allowed: `False`
- config_mutation_performed: `False`
- order_actions_performed: `False`
- reload_performed: `False`
- live_real_allowed: `False`

## Candidates

| candidate | interval | decision | score | samples | action_pct | hold_pct | buy/sell/hold | side_pct | min_edge_bps | fwd_gap_bps | trend_align_pct | reasons | warnings |
|---|---|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---|---|
| diagnostic_1m_cost16_edge30_atr3_0 | 1m | BLOCK | -999.0 | 0 | 0.0000 | 0.0000 | BUY=0, SELL=0, HOLD=0 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | `['MTF_INTERVAL_DATA_MISSING']` | `[]` |
| mtf_5m_h12_cost16_edge25_atr2_5 | 5m | PASS | 100.664526 | 25879 | 19.1661 | 80.8339 | BUY=2500, SELL=2460, HOLD=20919 | 50.4032 | 60.6042 | 75.5800 | 60.5645 | `[]` | `[]` |
| mtf_5m_h24_cost16_edge35_atr3_0 | 5m | PASS | 113.946229 | 25867 | 28.3295 | 71.6705 | BUY=3773, SELL=3555, HOLD=18539 | 51.4874 | 69.2252 | 88.9100 | 55.1992 | `[]` | `[]` |
| mtf_15m_h8_cost16_edge30_atr2_5 | 15m | PASS | 141.343892 | 8603 | 17.6683 | 82.3317 | BUY=786, SELL=734, HOLD=7083 | 51.7105 | 95.0002 | 103.4622 | 55.4605 | `[]` | `[]` |
| mtf_15m_h16_cost20_edge40_atr3_0 | 15m | BLOCK | 163.211135 | 8595 | 25.6312 | 74.3688 | BUY=1158, SELL=1045, HOLD=6392 | 52.5647 | 126.0066 | 134.5514 | 52.8370 | `['MTF_FEATURE_SEPARATION_LOW']` | `[]` |
| mtf_1h_h6_cost20_edge50_atr2_5 | 1h | BLOCK | 225.564304 | 2125 | 16.8000 | 83.2000 | BUY=197, SELL=160, HOLD=1768 | 55.1821 | 191.7525 | 185.3568 | 49.5798 | `['MTF_TREND_ALIGNMENT_LOW', 'MTF_FEATURE_SEPARATION_LOW']` | `[]` |
| mtf_1h_h12_cost20_edge70_atr3_0 | 1h | BLOCK | 267.925748 | 2119 | 22.0387 | 77.9613 | BUY=268, SELL=199, HOLD=1652 | 57.3876 | 224.1520 | 236.8779 | 44.3255 | `['MTF_TREND_ALIGNMENT_LOW', 'MTF_FEATURE_SEPARATION_LOW']` | `[]` |

## Policy

This tool is observation-only. A PASS only identifies an offline research/training candidate. It never mutates config, reloads models, starts paper trading, or sends orders; real live trading remains blocked.
