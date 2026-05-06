# 4B.4.3.6.6.25A Multi-Timeframe Alpha Discovery / Research Reset

- contract_version: `4B.4.3.6.6.25A`
- decision: **PASS**
- candidate_count: `7`
- approved_for_training_candidate: `True`
- approved_for_paper_candidate: `False`
- approved_for_live_real: `False`
- selected_policy: `mtf_15m_h16_cost20_edge40_atr3_0`
- selected_interval: `15m`
- selected_score: `182.434957`
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
| mtf_5m_h12_cost16_edge25_atr2_5 | 5m | PASS | 109.426877 | 51799 | 19.0255 | 80.9745 | BUY=4593, SELL=5262, HOLD=41944 | 53.3942 | 67.2636 | 78.3115 | 58.2243 | `[]` | `[]` |
| mtf_5m_h24_cost16_edge35_atr3_0 | 5m | PASS | 124.464641 | 51787 | 27.8757 | 72.1243 | BUY=6677, SELL=7759, HOLD=37351 | 53.7476 | 78.1554 | 93.5681 | 54.7382 | `[]` | `[]` |
| mtf_15m_h8_cost16_edge30_atr2_5 | 15m | PASS | 156.358019 | 17243 | 17.2128 | 82.7872 | BUY=1392, SELL=1576, HOLD=14275 | 53.0997 | 107.6473 | 109.2968 | 59.4340 | `[]` | `[]` |
| mtf_15m_h16_cost20_edge40_atr3_0 | 15m | PASS | 182.434957 | 17235 | 25.4308 | 74.5692 | BUY=2077, SELL=2306, HOLD=12852 | 52.6124 | 128.0488 | 138.3587 | 57.6546 | `[]` | `[]` |
| mtf_1h_h6_cost20_edge50_atr2_5 | 1h | BLOCK | 240.987299 | 4285 | 16.5461 | 83.4539 | BUY=348, SELL=361, HOLD=3576 | 50.9168 | 188.2280 | 194.6696 | 50.4937 | `['MTF_FEATURE_SEPARATION_LOW']` | `[]` |
| mtf_1h_h12_cost20_edge70_atr3_0 | 1h | BLOCK | 287.464579 | 4279 | 22.5520 | 77.4480 | BUY=483, SELL=482, HOLD=3314 | 50.0518 | 240.5526 | 241.2909 | 49.8446 | `['MTF_TREND_ALIGNMENT_LOW', 'MTF_FEATURE_SEPARATION_LOW']` | `[]` |

## Policy

This tool is observation-only. A PASS only identifies an offline research/training candidate. It never mutates config, reloads models, starts paper trading, or sends orders; real live trading remains blocked.
