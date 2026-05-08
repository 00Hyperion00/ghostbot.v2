# Futures Candidate Refinement / Median Edge Recovery — 4B.4.3.6.6.25E

## Purpose

25D showed a futures research candidate with positive mean edge but negative median edge. This phase tests whether stricter funding/OI/taker/trend filters can recover a positive median edge without relying on a few outlier wins.

## Guardrails

- Observation only.
- Public futures market data only.
- No POST requests.
- No config mutation.
- No model training.
- No model reload.
- No order actions.
- Backtest PASS is not paper permission.
- Paper PASS is not live permission.

## Main command

```powershell
python tools/run_futures_candidate_refinement_median_edge_recovery_4B436625E.py `
  --input-json reports\4B436625D_futures_research_candidate_simulator_20260508_082617.json `
  --days 90 `
  --base-url https://fapi.binance.com `
  --out-dir reports `
  --review-ok
```

## Local CSV command

```powershell
python tools/run_futures_candidate_refinement_median_edge_recovery_4B436625E.py `
  --input-csv data\BTCUSDT_4h_futures_features.csv `
  --symbol BTCUSDT `
  --interval 4h `
  --out-dir reports `
  --review-ok
```

## PASS means

A PASS only identifies a refined research candidate. It does not permit training, paper trading, live trading, reload, or config mutation.

## BLOCK means

No median-edge recovery filter passed. The candidate should remain blocked unless a new pre-registered hypothesis is opened.
