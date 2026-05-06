# 4B.4.3.6.6.24J Cost-Aware Retrain Sweep + Separation Gate

This phase uses the cost-aware label policies approved by 24I to train candidate XGBoost models, then gates each candidate with validation probability-separation and calibration metrics.

## Guardrails

- No config mutation.
- No model reload.
- No orders.
- No paper trading start.
- No real-live trading approval.
- Optional `--promote` only copies the best PASS model and sidecars when explicitly provided.

## Typical run

```powershell
python tools/run_cost_aware_retrain_sweep_4B436624J.py `
  --symbol ETHUSDT `
  --interval 1m `
  --days 90 `
  --base-url https://api.binance.com `
  --input-json reports/4B436624I_cost_aware_label_policy_recovery_YYYYMMDD_HHMMSS.json `
  --max-candidates 6 `
  --review-ok
```

## Promote copy only

```powershell
python tools/run_cost_aware_retrain_sweep_4B436624J.py `
  --symbol ETHUSDT `
  --interval 1m `
  --days 90 `
  --base-url https://api.binance.com `
  --input-json reports/4B436624I_cost_aware_label_policy_recovery_YYYYMMDD_HHMMSS.json `
  --max-candidates 6 `
  --promote `
  --promote-to models/ETHUSDT_model_4b436624J.ubj `
  --review-ok
```

Promotion does not reload the model. A later manual reload plus 24E/24F/24C verification is mandatory.

## Expected reports

- `reports/4B436624J_cost_aware_retrain_sweep_*.json`
- `reports/4B436624J_cost_aware_retrain_sweep_*.md`

## PASS meaning

A PASS means only: at least one trained cost-aware candidate model passed the separation gate and can be reviewed as a reload candidate. Paper/live trading remain blocked.
