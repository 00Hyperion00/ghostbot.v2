# 4B.4.3.6.6.24L Edge-Aware Meta-Label / Regime Filter Recovery

## Purpose

24K showed that two-stage ACTION/SIDE candidates can produce staged actions, but the selected candidate stayed BLOCK because expected edge proxy was negative. 24L replays two-stage candidates and evaluates whether any regime/meta-label filter can isolate an edge-positive subset.

## Guardrails

- Observation only.
- GET/public market-data only.
- No config mutation.
- No order actions.
- No reload.
- No paper trading start.
- No real-live trading approval.
- `--promote` only copies PASS candidate files and requires an explicit flag.

## Inputs

Recommended input is a 24K JSON report:

```powershell
python tools/run_edge_meta_label_regime_recovery_4B436624L.py `
  --symbol ETHUSDT `
  --interval 1m `
  --days 90 `
  --base-url https://api.binance.com `
  --input-json reports/4B436624K_two_stage_action_side_recovery_YYYYMMDD_HHMMSS.json `
  --max-candidates 3 `
  --review-ok
```

For local OHLCV:

```powershell
python tools/run_edge_meta_label_regime_recovery_4B436624L.py `
  --input-json reports/4B436624K_two_stage_action_side_recovery_YYYYMMDD_HHMMSS.json `
  --input-csv data\ETHUSDT_1m.csv `
  --review-ok
```

For offline synthetic checks:

```powershell
python tools/run_edge_meta_label_regime_recovery_4B436624L.py `
  --candidate-json reports/synthetic_edge_samples.json `
  --review-ok
```

## Regime Filters

The tool evaluates filters including:

- `mtf_trend_aligned`
- `ema_trend_aligned`
- `trend_double_aligned`
- `volume_confirmed`
- `vwap_near`
- `mid_volatility`
- `trend_volume_confirmed`
- `trend_vwap_volume`
- `confidence_side_guarded`
- `trend_confidence_side_guarded`

`all_staged_actions` is diagnostic and not approvable.

## PASS Meaning

A PASS means an edge-positive subset was found for manual review. It does **not** authorize paper trading or live trading.

## BLOCK Meaning

A BLOCK means no safe edge-positive regime/meta-label subset passed the gate. Do not promote or reload. Revisit regime features, meta-label objective, timeframe, or market selection.
