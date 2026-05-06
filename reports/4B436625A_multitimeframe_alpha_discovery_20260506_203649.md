# 4B.4.3.6.6.25A Multi-Timeframe Alpha Discovery / Research Reset

- contract_version: `4B.4.3.6.6.25A`
- decision: **BLOCK**
- candidate_count: `None`
- approved_for_training_candidate: `False`
- approved_for_paper_candidate: `False`
- approved_for_live_real: `False`
- selected_policy: `None`
- selected_interval: `None`
- selected_score: `None`
- selected_action_pct: `0.0000`
- selected_min_expected_net_edge_bps: `0.0000`
- recommendation: Tool failed before producing a valid research report: [Errno 2] No such file or directory: 'data\\ETHUSDT_15m.csv'

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

## Policy

This tool is observation-only. A PASS only identifies an offline research/training candidate. It never mutates config, reloads models, starts paper trading, or sends orders; real live trading remains blocked.
