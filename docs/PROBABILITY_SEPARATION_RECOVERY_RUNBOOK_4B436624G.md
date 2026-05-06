# 4B.4.3.6.6.24G Probability Separation / Label Calibration Recovery Runbook

## Purpose

24E proved `CALIBRATION_SUPPRESSION` and 24F proved no safe calibration policy candidate passed the gate. 24G checks whether the model has enough BUY/SELL probability separation and whether label calibration evidence is strong enough before another retrain/promote cycle.

## Guardrails

- Observation-only.
- GET-only when collecting runtime samples.
- No POST requests.
- No model reload.
- No config mutation.
- No order submission.
- Real live trading remains blocked.

## Apply

```powershell
cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
Expand-Archive -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436624G_probability_separation_recovery_patch.zip" -DestinationPath . -Force
python tools/apply_4B436624G_probability_separation_recovery.py
```

## Tests

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH="src"
python -m pytest -q `
tests/test_probability_separation_gate_4B436624G.py `
tests/test_calibration_policy_gate_4B436624F.py `
tests/test_runtime_calibration_probe_4B436624E.py `
tests/test_model_retrain_recovery_4B436624D.py `
tests/test_model_quality_gate_4B436624B.py `
tests/test_extended_demo_soak_4B436624C.py `
tests/test_api_persistence_hotfix.py `
tests/test_release_cleanup_4B436624A.py `
tests/test_config_loading.py `
tests/test_config_profile_safety.py
```

## Run from the latest 24E report

```powershell
python tools/run_probability_separation_recovery_4B436624G.py `
  --input-json reports/4B436624E_runtime_calibration_probe_20260505_200857.json `
  --review-ok
```

## Run from live runtime samples

```powershell
python tools/run_probability_separation_recovery_4B436624G.py `
  --base-url http://127.0.0.1:8000 `
  --duration-min 40 `
  --interval-sec 60 `
  --min-samples 30 `
  --review-ok `
  --timeout-sec 15
```

## Interpretation

- `BUY_SELL_SEPARATION_MEAN_LOW` / `BUY_SELL_SEPARATION_MEDIAN_LOW`: model action side probabilities are too close; threshold relaxation is unsafe.
- `RAW_ACTION_COVERAGE_TOO_HIGH`: raw model is over-triggering action and needs label/objective recovery.
- `LOW_MARGIN_REJECTION_HIGH`: current calibration is rejecting too many low-margin action calls.
- `LABEL_SIDE_IMBALANCE_ELEVATED`: target labels may be biased toward one action side.

A PASS result is only paper/demo evidence. It does not authorize real live trading.
