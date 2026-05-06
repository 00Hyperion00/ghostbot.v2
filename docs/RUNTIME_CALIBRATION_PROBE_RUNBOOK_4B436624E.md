# 4B.4.3.6.6.24E Runtime Calibration Probe + Threshold Sweep

Purpose: determine whether runtime HOLD dominance is caused by raw model collapse or by calibration/threshold suppression.

## Guardrails

- GET-only against `/status`.
- No order submission.
- No model reload.
- No config mutation.
- No live-real arming.
- No gate bypass.

## One-shot probe

```powershell
cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
$env:PYTHONPATH="src"

python tools/run_runtime_calibration_probe_4B436624E.py `
  --base-url http://127.0.0.1:8000 `
  --once `
  --review-ok `
  --timeout-sec 15
```

## Runtime window probe

```powershell
python tools/run_runtime_calibration_probe_4B436624E.py `
  --base-url http://127.0.0.1:8000 `
  --duration-min 40 `
  --interval-sec 60 `
  --min-samples 30 `
  --review-ok `
  --timeout-sec 15
```

## Offline input

```powershell
python tools/run_runtime_calibration_probe_4B436624E.py --input-json status_samples.json --min-samples 30
```

## Interpret conclusions

- `RAW_MODEL_COLLAPSE`: raw top class is also HOLD. Do not relax thresholds; investigate labels/features/objective/class mapping.
- `CALIBRATION_SUPPRESSION`: raw BUY/SELL exists but current calibration suppresses it. Consider a separate paper-only threshold patch after review.
- `MODEL_ACTION_PROBABILITY_TOO_LOW`: raw actions appear but are too weak even under diagnostic profiles.
- `ACTIONABLE_UNDER_CURRENT_CALIBRATION`: current calibration produces actions; continue controlled validation.
- `PENDING_INSUFFICIENT_SAMPLES`: collect more runtime samples.

Real live trading remains blocked until later paper/live-demo evidence exists.
