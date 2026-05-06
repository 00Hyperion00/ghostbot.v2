# 4B.4.3.6.6.24F Calibration Policy Candidate Gate

Evaluates guarded calibration profiles using runtime probability samples. It does not mutate config, reload models, submit orders, or arm live trading.

## Apply

```powershell
python tools/apply_4B436624F_calibration_policy_gate.py
```

## Test

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH="src"
python -m pytest -q tests/test_calibration_policy_gate_4B436624F.py tests/test_runtime_calibration_probe_4B436624E.py tests/test_model_retrain_recovery_4B436624D.py tests/test_model_quality_gate_4B436624B.py tests/test_extended_demo_soak_4B436624C.py tests/test_config_profile_safety.py
```

## Run from a 24E report

```powershell
python tools/run_calibration_policy_gate_4B436624F.py --input-json reports/4B436624E_runtime_calibration_probe_YYYYMMDD_HHMMSS.json --review-ok
```

## Run live observation

```powershell
python tools/run_calibration_policy_gate_4B436624F.py --base-url http://127.0.0.1:8000 --duration-min 40 --interval-sec 60 --min-samples 30 --review-ok --timeout-sec 15
```

`no_margin_probe` is diagnostic only and is never approvable. `approved_for_live_real` always remains false.
