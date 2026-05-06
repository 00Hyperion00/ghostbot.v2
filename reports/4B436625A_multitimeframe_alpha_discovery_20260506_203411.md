# 4B.4.3.6.6.25A Multi-Timeframe Alpha Discovery / Research Reset

- contract_version: `4B.4.3.6.6.25A`
- decision: **PASS**
- candidate_count: `7`
- approved_for_training_candidate: `True`
- approved_for_paper_candidate: `False`
- approved_for_live_real: `False`
- selected_policy: `mtf_15m_h16_cost20_edge40_atr3_0`
- selected_interval: `15m`
- selected_score: `182.433531`
- selected_action_pct: `25.4308`
- selected_min_expected_net_edge_bps: `128.0488`
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
| mtf_5m_h12_cost16_edge25_atr2_5 | 5m | BLOCK | -999.0 | 0 | 0.0000 | 0.0000 | BUY=0, SELL=0, HOLD=0 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | `['MTF_INTERVAL_DATA_MISSING']` | `[]` |
| mtf_5m_h24_cost16_edge35_atr3_0 | 5m | BLOCK | -999.0 | 0 | 0.0000 | 0.0000 | BUY=0, SELL=0, HOLD=0 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | `['MTF_INTERVAL_DATA_MISSING']` | `[]` |
| mtf_15m_h8_cost16_edge30_atr2_5 | 15m | PASS | 156.352635 | 17243 | 17.2128 | 82.7872 | BUY=1392, SELL=1576, HOLD=14275 | 53.0997 | 107.6473 | 109.2981 | 59.4340 | `[]` | `[]` |
| mtf_15m_h16_cost20_edge40_atr3_0 | 15m | PASS | 182.433531 | 17235 | 25.4308 | 74.5692 | BUY=2077, SELL=2306, HOLD=12852 | 52.6124 | 128.0488 | 138.3674 | 57.6546 | `[]` | `[]` |
| mtf_1h_h6_cost20_edge50_atr2_5 | 1h | BLOCK | -999.0 | 0 | 0.0000 | 0.0000 | BUY=0, SELL=0, HOLD=0 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | `['MTF_INTERVAL_DATA_MISSING']` | `[]` |
| mtf_1h_h12_cost20_edge70_atr3_0 | 1h | BLOCK | -999.0 | 0 | 0.0000 | 0.0000 | BUY=0, SELL=0, HOLD=0 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | `['MTF_INTERVAL_DATA_MISSING']` | `[]` |

## Policy

This tool is observation-only. A PASS only identifies an offline research/training candidate. It never mutates config, reloads models, starts paper trading, or sends orders; real live trading remains blocked.
