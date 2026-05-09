# 4B.4.3.6.6.25V — HYP-005 Shadow Observation Logger / No-Order Runtime Probe Gate

This patch adds a no-order runtime probe for the HYP-005 `long_liquidity_sweep_reversal` candidate that passed 25S exploration and 25T robustness, then received a 25U no-order shadow plan.

## Purpose

- Read the 25U candidate spec JSON or 25U report.
- Validate that the spec is strictly `NO_ORDER_SHADOW_ONLY`.
- Scan deterministic CSV or public market data GET candles for liquidity sweep observations.
- Write a shadow observation ledger in JSON and JSONL form.
- Keep training, paper trading, live trading, model reload, config mutation, and order actions blocked.

## No-order runtime probe

The tool may read public OHLCV market data with GET requests only. It never sends POST requests, never touches exchange credentials, and never places orders.

## Example

```powershell
python tools/run_hyp005_shadow_observation_logger_4B436625V.py `
  --candidate-spec-json reports\4B436625U_hyp005_no_order_shadow_candidate_spec_20260509_175722.json `
  --symbols BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT `
  --interval 4h `
  --days 30 `
  --base-url https://api.binance.com `
  --out-dir reports `
  --review-ok
```

For deterministic replay:

```powershell
python tools/run_hyp005_shadow_observation_logger_4B436625V.py `
  --candidate-spec-json reports\4B436625U_hyp005_no_order_shadow_candidate_spec_20260509_175722.json `
  --input-csv data\shadow_replay.csv `
  --symbols BTCUSDT `
  --interval 4h `
  --out-dir reports `
  --review-ok
```

## Outputs

- `reports/4B436625V_hyp005_shadow_observation_logger_*.json`
- `reports/4B436625V_hyp005_shadow_observation_logger_*.md`
- `reports/4B436625V_hyp005_shadow_observation_ledger_*.json`
- `reports/4B436625V_hyp005_shadow_observation_ledger_*.jsonl`

## Guardrails

- No-order runtime probe.
- Candidate observations are not trading permission.
- Training remains blocked.
- Model reload remains blocked.
- Paper/live remain blocked.
- POST requests remain blocked.
- Manual review and a separate paper-transition gate remain required.
