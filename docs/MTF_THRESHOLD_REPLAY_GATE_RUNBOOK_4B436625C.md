# 4B.4.3.6.6.25C — 15m Threshold/Calibration Replay Gate

Purpose: replay threshold/calibration profiles against 15m validation probabilities from a 25B candidate model.

This tool is observation-only. It never mutates config, reloads models, starts paper trading, or sends orders.

## Apply

```powershell
cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
Expand-Archive -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436625C_15m_threshold_replay_gate_patch.zip" -DestinationPath . -Force
python tools/apply_4B436625C_15m_threshold_replay_gate.py
```

## Test

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH="src"
python -m pytest -q tests/test_mtf_threshold_replay_gate_4B436625C.py
```

## Run against a 25B report

```powershell
python tools/run_15m_threshold_replay_gate_4B436625C.py `
  --input-json reports/4B436625B_15m_mtf_retrain_sweep_20260506_205356.json `
  --symbol ETHUSDT `
  --interval 15m `
  --days 180 `
  --base-url https://api.binance.com `
  --candidate-index 1 `
  --review-ok
```

Try candidate 2 if the selected 25B candidate was action-seek-light:

```powershell
python tools/run_15m_threshold_replay_gate_4B436625C.py `
  --input-json reports/4B436625B_15m_mtf_retrain_sweep_20260506_205356.json `
  --symbol ETHUSDT `
  --interval 15m `
  --days 180 `
  --base-url https://api.binance.com `
  --candidate-index 2 `
  --review-ok
```

## Interpretation

A PASS only identifies an offline threshold replay candidate. It is not a paper/live approval. Real live remains blocked.

A BLOCK means do not loosen thresholds, do not promote, and do not reload.
