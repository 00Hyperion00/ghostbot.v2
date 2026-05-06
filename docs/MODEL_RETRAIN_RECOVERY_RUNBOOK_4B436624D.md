# 4B.4.3.6.6.24D Model Retrain Dataset Expansion + Candidate Quality Recovery

## Purpose

24D adds a controlled candidate-retraining workflow. It expands the candidate search over longer datasets, class-weight profiles, and threshold profiles, then blocks promotion unless the candidate has objective quality evidence.

## Hard rules

- The tool does not reload a model.
- The tool does not place orders.
- The tool does not change API credentials.
- Promotion is opt-in with `--promote` and only allowed when the best candidate is PASS.
- Real live trading remains disallowed by this phase.

## Smoke plan

```powershell
cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
$env:PYTHONPATH="src"
python tools/run_model_retrain_recovery_4B436624D.py --dry-run
```

## Candidate sweep

```powershell
python tools/run_model_retrain_recovery_4B436624D.py `
  --symbol ETHUSDT `
  --interval 1m `
  --base-url https://api.binance.com `
  --days 30,60,90 `
  --class-weight-profiles balanced,buy_sell_boost_light,buy_sell_boost_medium `
  --threshold-profiles balanced,action_seek_light `
  --max-candidates 6
```

## Output

The tool writes:

- `reports/4B436624D_model_retrain_recovery_*.json`
- `reports/4B436624D_model_retrain_recovery_*.md`

## PASS criteria

A candidate must pass both:

1. Training model-quality gate.
2. Dataset quality gate.

The dataset gate blocks synthetic class padding, missing/weak target action coverage, excessive HOLD target rate, and insufficient clean samples.

## After PASS

A PASS candidate may be copied with:

```powershell
python tools/run_model_retrain_recovery_4B436624D.py --promote --promote-to models/ETHUSDT_model_4b436624D.ubj
```

After promotion, use the normal `/ai/reload` path or dashboard reload flow. Do not bypass 24B/24C gate evidence.
