# 4B.4.3.6.6.25I Research Backlog Advancement / Next Hypothesis Selection Gate

- contract_version: `4B.4.3.6.6.25I`
- decision: **NEXT_HYPOTHESIS_SELECTED**
- source_reports: `15`
- registry_source: `config\research_hypotheses_4B436624O.json`
- closed_hypothesis_id: `HYP-002`
- closed_branch_name: `futures_funding_trend_exhaustion`
- selected_next_hypothesis_id: `HYP-003`
- selected_next_hypothesis_title: `Regime-specific strategy family`
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
- title: `Regime-specific strategy family`
- family: `research`
- priority: `3`
- status: `BACKLOG`
- training_allowed_if_pass: `False`
- paper_allowed_if_pass: `False`
- live_allowed_if_pass: `False`
- acceptance_metrics: `{'min_net_edge_bps': 3.0, 'min_profit_factor': 1.15, 'min_trade_count': 100, 'max_drawdown_pct': 8.0, 'oos_required': True, 'walk_forward_required': True, 'fee_slippage_included': True, 'lookahead_leakage_tolerance': 'zero'}`

## Backlog Snapshot

| hypothesis_id | status | priority | family | title |
|---|---|---:|---|---|
| HYP-001 | PROPOSED | 1 | research | Higher timeframe trend following |
| HYP-002 | CLOSED_NO_GO | 2 | research | Futures funding and open-interest edge |
| HYP-003 | BACKLOG | 3 | research | Regime-specific strategy family |
| HYP-004 | BACKLOG | 4 | research | Portfolio relative-strength rotation |
| HYP-005 | BACKLOG | 5 | research | Order-flow and volume imbalance research |

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
