# 4B.4.3.6.6.24K Two-Stage Action/Side Model Recovery

## Purpose

24J showed that the cost-aware label policy improved labels, but a single 3-class XGBoost model still failed the action-vs-hold separation gate. 24K introduces a diagnostic training workflow that separates the decision into two models:

1. **ACTION model:** HOLD vs ACTION.
2. **SIDE model:** BUY vs SELL, trained only on action-labelled samples.

The goal is to determine whether a two-stage architecture improves action precision, action coverage, side balance, and action-vs-hold probability separation.

## Guardrails

This patch never:

- mutates config,
- reloads models,
- starts paper trading,
- sends orders,
- enables real-live trading.

A PASS only identifies a two-stage training candidate for manual review. Paper/live remain blocked.

## Apply

```powershell
cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
Expand-Archive -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436624K_two_stage_action_side_recovery_patch.zip" -DestinationPath . -Force
python tools/apply_4B436624K_two_stage_action_side_recovery.py
```

## Tests

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH="src"
python -m pytest -q tests/test_two_stage_action_side_recovery_4B436624K.py
```

Regression:

```powershell
python -m pytest -q `
tests/test_two_stage_action_side_recovery_4B436624K.py `
tests/test_cost_aware_retrain_sweep_4B436624J.py `
tests/test_cost_aware_label_policy_recovery_4B436624I.py `
tests/test_label_horizon_recovery_4B436624H.py `
tests/test_probability_separation_gate_4B436624G.py
```

## Run from 24I report

```powershell
python tools/run_two_stage_action_side_recovery_4B436624K.py `
  --symbol ETHUSDT `
  --interval 1m `
  --days 90 `
  --base-url https://api.binance.com `
  --input-json reports/4B436624I_cost_aware_label_policy_recovery_20260506_121817.json `
  --max-candidates 6 `
  --review-ok
```

## Wider sweep

```powershell
python tools/run_two_stage_action_side_recovery_4B436624K.py `
  --symbol ETHUSDT `
  --interval 1m `
  --days 90 `
  --base-url https://api.binance.com `
  --input-json reports/4B436624I_cost_aware_label_policy_recovery_20260506_121817.json `
  --action-profiles balanced,action_precision_guarded,action_recall_light `
  --side-profiles balanced,side_balance_guarded `
  --action-threshold-profiles conservative,balanced,recall_light `
  --side-margin-profiles strict,guarded,balanced `
  --max-candidates 9 `
  --review-ok
```

## Output

- `reports/4B436624K_two_stage_action_side_recovery_*.json`
- `reports/4B436624K_two_stage_action_side_recovery_*.md`
- `models/4B436624K_candidates/*_action.ubj`
- `models/4B436624K_candidates/*_side.ubj`

## Promote

Only after a PASS and manual review:

```powershell
python tools/run_two_stage_action_side_recovery_4B436624K.py `
  --symbol ETHUSDT `
  --interval 1m `
  --days 90 `
  --base-url https://api.binance.com `
  --input-json reports/4B436624I_cost_aware_label_policy_recovery_20260506_121817.json `
  --max-candidates 6 `
  --promote `
  --promote-prefix models/ETHUSDT_two_stage_4b436624K `
  --review-ok
```

Promotion copies files only. It does not reload anything. Real live trading remains blocked.
