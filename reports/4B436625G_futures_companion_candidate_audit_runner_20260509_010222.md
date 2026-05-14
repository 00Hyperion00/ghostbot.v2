# 4B.4.3.6.6.25G Futures Companion Candidate Audit Runner

- contract_version: `4B.4.3.6.6.25G`
- decision: **COMPANION_AUDIT_READY**
- source_reports: `9`
- approved_for_research_candidate: `False`
- approved_for_training_candidate: `False`
- approved_for_paper_candidate: `False`
- approved_for_live_real: `False`
- combined_signals: `64`
- downstream_confirmed_count: `0`
- reason_codes: `['COMPANION_DRY_RUN_REFINEMENT_AUDIT_REQUIRED', 'COMPANION_SPEC_READY']`
- recommendation: Companion exploration candidate is ready for 25D/25E audit. Run the generated commands; paper/live remain blocked.

## Primary

- symbol: `BTCUSDT`
- interval: `4h`
- strategy: `funding_trend_exhaustion`
- signal_count: `33`
- mean_net_edge_bps: `53.704409`
- profit_factor: `2.154669`

## Companion

- symbol: `ETHUSDT`
- interval: `4h`
- strategy: `funding_trend_exhaustion`
- signal_count: `31`
- mean_net_edge_bps: `44.125478`
- profit_factor: `1.584716`
- companion_spec_path: `reports\4B436625G_companion_spec_ETHUSDT_4h_funding_trend_exhaustion.json`

## Next Commands

### 25D — Run companion dry-run signal simulator without orders.

```powershell
python tools/run_futures_research_candidate_simulator_4B436625D.py `
  --spec-json reports\4B436625G_companion_spec_ETHUSDT_4h_funding_trend_exhaustion.json `
  --days 90 `
  --base-url https://fapi.binance.com `
  --out-dir reports `
  --review-ok
```

### 25E — Run companion median-edge refinement without orders.

```powershell
python tools/run_futures_candidate_refinement_median_edge_recovery_4B436625E.py `
  --spec-json reports\4B436625G_companion_spec_ETHUSDT_4h_funding_trend_exhaustion.json `
  --days 90 `
  --base-url https://fapi.binance.com `
  --out-dir reports `
  --review-ok
```

## Guardrails

- observation_only: `True`
- market_data_requests_performed: `False`
- post_requests_allowed: `False`
- config_mutation_performed: `False`
- order_actions_performed: `False`
- reload_performed: `False`
- live_real_allowed: `False`
- Training remains blocked.
- Paper/live remain blocked.

## Policy

This runner only prepares companion audit specs and downstream no-order commands. It never fetches market data, trains models, reloads models, mutates config, starts paper trading, or sends orders.
