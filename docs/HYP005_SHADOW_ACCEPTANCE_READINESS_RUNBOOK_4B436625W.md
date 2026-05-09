# 4B.4.3.6.6.25W — HYP-005 Shadow Observation Acceptance / Paper-Transition Readiness Gate

This patch evaluates HYP-005 no-order shadow observation ledgers produced by 25V.

## Purpose

- Read 25V shadow observation ledger JSON / JSONL files.
- Measure shadow sample count, forward edge, profit factor, OOS edge, walk-forward stability, data quality, slippage proxy, top-win dependency, symbol dependency, and wick dependency.
- Emit `HYP005_SHADOW_PAPER_TRANSITION_READY` only when the shadow ledger meets the readiness gate.
- Emit `HYP005_SHADOW_PAPER_TRANSITION_BLOCK` when samples or metrics are insufficient.

## Safety Policy

Paper-transition readiness is not paper permission.

25W does not:

- send orders
- start paper trading
- enable live trading
- train models
- reload/promote models
- mutate config
- perform POST requests

A READY decision only says the shadow ledger can be considered by a later dedicated paper-enablement gate.

## Expected Command

```powershell
python tools/run_hyp005_shadow_acceptance_readiness_4B436625W.py `
  --ledger-json reports\4B436625V_hyp005_shadow_observation_ledger_YYYYMMDD_HHMMSS.json `
  --out-dir reports `
  --review-ok
```

Or discover the latest 25V logger/ledger automatically:

```powershell
python tools/run_hyp005_shadow_acceptance_readiness_4B436625W.py `
  --reports-dir reports `
  --include-all `
  --out-dir reports `
  --review-ok
```

## Acceptance Metrics

- `shadow_observation_count >= 30`
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

## Output Files

- `reports/4B436625W_hyp005_shadow_observation_acceptance_*.json`
- `reports/4B436625W_hyp005_shadow_observation_acceptance_*.md`
- `reports/4B436625W_hyp005_shadow_acceptance_summary_*.json`

## Guardrail

Paper/live remain blocked. Training remains blocked. Reload remains blocked.
