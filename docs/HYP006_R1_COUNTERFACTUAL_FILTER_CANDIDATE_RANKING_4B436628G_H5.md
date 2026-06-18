# 4B.4.3.6.6.28G-H5 HYP-006 Counterfactual Filter Candidate Ranking

No-order Gate-Combo Review Pack for HYP-006-R1.

This patch consumes the latest `4B436628G_H4_hyp006_r1_near_miss_outcome_attribution_*.json` report and ranks counterfactual candidates across:

- gate-combo outcome summaries,
- symbol outcome summaries,
- risk-bucket outcome summaries.

It produces:

- `accepted_review_candidates`,
- `gate_combo_specific_candidates`,
- `symbol_specific_candidates`,
- `risk_bucket_specific_candidates`,
- `watchlist_low_sample_candidates`,
- `rejected_counterfactual_candidates`,
- `tail_risk_flags`,
- `do_not_relax_gate_combos`.

## Guardrails

Accepted review candidates require:

- `matured_count >= 10`,
- `win_rate_pct >= 60`,
- `profit_factor >= 1.5`,
- `mean_return_bps > 0`,
- `worst_return_bps > -500`,
- `worst_mae_bps > -500`.

Watchlist candidates require the same quality constraints but `3 <= matured_count < 10`.

## Fail-closed behavior

This report is research-only. It never modifies strategy parameters, config, scheduler, training, reload, paper/live trading, or order state.

The following remain false by construction:

- `approved_for_parameter_relaxation_candidate`,
- `approved_for_paper_candidate`,
- `approved_for_live_real`,
- `training_performed`,
- `reload_performed`,
- `trading_action_performed`,
- `order_actions_performed`.
