# 4B.4.3.6.6.25B — 15m Multi-Timeframe Retrain Sweep + Gate

This runbook covers the 25B research-only retrain sweep. The tool uses 25A multi-timeframe alpha discovery policy candidates, trains 15m candidate models, evaluates probability separation and expected-edge metrics, and writes reports.

## Guardrails

- Observation/research only.
- No POST requests to the local bot API.
- No order placement.
- No config mutation.
- No automatic model reload.
- No paper trading start.
- No live-real approval.
- `--promote` only copies a PASS candidate model and sidecars; it does not reload the runtime model.

## Apply

```powershell
cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
Expand-Archive -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436625B_15m_mtf_retrain_sweep_patch.zip" -DestinationPath . -Force
python tools/apply_4B436625B_multitimeframe_retrain_sweep.py
```

## Tests

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH="src"
python -m pytest -q tests/test_multitimeframe_retrain_sweep_4B436625B.py
```

## Run from 25A report

```powershell
python tools/run_multitimeframe_retrain_sweep_4B436625B.py `
  --symbol ETHUSDT `
  --interval 15m `
  --days 180 `
  --base-url https://api.binance.com `
  --input-json reports/4B436625A_multitimeframe_alpha_discovery_20260506_202950.json `
  --class-weight-profiles balanced,buy_sell_boost_light,buy_sell_boost_medium `
  --threshold-profiles balanced,action_seek_light,paper_guarded `
  --max-candidates 6 `
  --review-ok
```

## PASS semantics

A PASS only means a 15m research candidate is suitable for manual review and later controlled reload/probe checks. It does not approve paper or live trading.
