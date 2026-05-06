# 4B.4.3.6.6.24L Regime-Aware Edge Filter Recovery

- contract_version: `4B.4.3.6.6.24L`
- decision: **BLOCK**
- candidate_count: `1`
- candidate_run_count: `1`
- approved_for_training_candidate: `False`
- approved_for_paper_candidate: `False`
- approved_for_live_real: `False`
- selected_filter: `aggregate_24k_diagnostic`
- selected_score: `-100`
- selected_filtered_action_pct: `None`
- selected_action_precision: `None`
- selected_side_accuracy: `None`
- selected_expected_edge_proxy_bps: `None`
- recommendation: 24K aggregate report is insufficient for regime filtering. Run 24L with market data so per-sample regime features can be evaluated.

## Guardrails

- observation_only: `True`
- no_post_actions: `True`
- post_requests_allowed: `False`
- config_mutation_performed: `False`
- order_actions_performed: `False`
- reload_performed: `False`
- live_real_allowed: `False`
- promotion_requires_explicit_flag: `True`

## Baseline

- validation_staged_action_pct: `32.865136`
- validation_action_precision: `0.165422`
- validation_action_recall: `None`
- validation_side_accuracy: `0.61497`
- expected_edge_proxy_bps: `-13.959141`

## Selected Filter Metrics

- reason_codes: `['REGIME_SAMPLE_FEATURES_MISSING', 'AGGREGATE_REPORT_NOT_APPROVABLE']`
- filtered_action_count: `None`
- filtered_action_pct: `None`
- action_precision: `None`
- action_precision_lift: `None`
- action_recall: `None`
- filtered_side_accuracy: `None`
- filtered_action_side_pct: `None`
- expected_edge_proxy_bps: `None`

## Filter Candidates

| # | decision | score | filter | family | action_pct | precision | precision_lift | side_accuracy | edge_proxy_bps | reasons | warnings |
|---:|---|---:|---|---|---:|---:|---:|---:|---:|---|---|
| 1 | BLOCK | -100 | aggregate_24k_diagnostic | diagnostic | None | None | None | None | None | `['REGIME_SAMPLE_FEATURES_MISSING', 'AGGREGATE_REPORT_NOT_APPROVABLE']` | `[]` |

## Policy

This tool may train temporary two-stage candidates for validation and regime analysis, but it never reloads models, mutates config, starts paper trading, or sends orders. A PASS only identifies a training-candidate regime filter for manual review; real live trading remains blocked.
