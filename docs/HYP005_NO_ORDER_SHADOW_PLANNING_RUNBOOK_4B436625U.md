# 4B.4.3.6.6.25U HYP-005 No-Order Shadow Planning / Candidate Spec Gate

25U consumes the 25S exploration PASS report and the 25T robustness/walk-forward PASS report for HYP-005.
It creates a no-order shadow candidate specification for `long_liquidity_sweep_reversal`.

## Purpose

- Confirm that HYP-005 passed 25S and 25T as research-only.
- Create a no-order shadow observation plan.
- Define entry signal, invalidation conditions, hold horizon, required risk fields, and shadow acceptance metrics.
- Keep training, paper trading, live trading, model reload, config mutation, POST actions, and order actions blocked.

## Expected Decision

`HYP005_SHADOW_PLAN_READY`

## Outputs

- `reports/4B436625U_hyp005_no_order_shadow_planning_*.json`
- `reports/4B436625U_hyp005_no_order_shadow_planning_*.md`
- `reports/4B436625U_hyp005_no_order_shadow_candidate_spec_*.json`

## Run

```powershell
python tools/run_hyp005_no_order_shadow_planning_4B436625U.py `
  --input-json reports\4B436625S_hyp005_liquidity_sweep_reversal_exploration_20260509_172138.json `
  --input-json reports\4B436625T_hyp005_robustness_walkforward_confirmation_20260509_174924.json `
  --out-dir reports `
  --review-ok
```

Auto-discovery:

```powershell
python tools/run_hyp005_no_order_shadow_planning_4B436625U.py `
  --reports-dir reports `
  --include-all `
  --out-dir reports `
  --review-ok
```

## Guardrails

- No market data is fetched.
- No POST request is allowed.
- No config is mutated.
- No model is trained.
- No model is reloaded.
- No paper trading is started.
- No live trading is enabled.
- No order is sent.
- Candidate spec is not trading permission.
- Paper transition requires a separate future gate.
- Live transition requires a separate future gate.

## Required Shadow Acceptance Metrics

- `shadow_sample_count >= 30`
- `shadow_days_observed >= 30`
- `shadow_signal_capture_count >= 25`
- `shadow_mean_forward_edge_bps >= 50`
- `shadow_median_forward_edge_bps >= 30`
- `shadow_profit_factor >= 1.50`
- `shadow_oos_edge_bps >= 25`
- `shadow_walk_forward_positive_rate_pct >= 60`
- `shadow_top_win_dependency_pct <= 45`
- `shadow_dominant_symbol_pct <= 70`
- `shadow_wick_dependency_pct <= 85`
- `shadow_slippage_proxy_bps <= 12`
- `shadow_data_quality_pct >= 98`
- `shadow_missing_fields_pct <= 1`
- `manual_reviewers >= 1`

Training remains blocked. Paper/live remain blocked.
