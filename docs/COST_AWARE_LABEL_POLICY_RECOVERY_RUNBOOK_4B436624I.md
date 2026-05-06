# 4B.4.3.6.6.24I Cost-Aware Label Policy Recovery Runbook

## Purpose

24I investigates whether target labels become safer when round-trip cost, slippage, and minimum edge are included in the label policy. It is a diagnostic gate for future retrain sweeps.

## Guardrails

This tool is observation-only. It never changes config, never trains a model, never reloads a model, never submits orders, and never approves real-live trading.

## Apply

```powershell
cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
Expand-Archive -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436624I_cost_aware_label_policy_recovery_patch.zip" -DestinationPath . -Force
python tools/apply_4B436624I_cost_aware_label_policy_recovery.py
```

## Test

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH="src"
python -m pytest -q tests/test_cost_aware_label_policy_recovery_4B436624I.py
```

Suggested regression:

```powershell
python -m pytest -q `
tests/test_cost_aware_label_policy_recovery_4B436624I.py `
tests/test_label_horizon_recovery_4B436624H.py `
tests/test_probability_separation_gate_4B436624G.py `
tests/test_calibration_policy_gate_4B436624F.py `
tests/test_runtime_calibration_probe_4B436624E.py
```

## Run with public Binance data

```powershell
python tools/run_cost_aware_label_policy_recovery_4B436624I.py `
  --symbol ETHUSDT `
  --interval 1m `
  --days 90 `
  --base-url https://api.binance.com `
  --review-ok
```

Shorter first pass:

```powershell
python tools/run_cost_aware_label_policy_recovery_4B436624I.py `
  --symbol ETHUSDT `
  --interval 1m `
  --days 30 `
  --base-url https://api.binance.com `
  --review-ok
```

## Output

The tool writes:

```text
reports/4B436624I_cost_aware_label_policy_recovery_*.json
reports/4B436624I_cost_aware_label_policy_recovery_*.md
```

## Interpretation

PASS means a cost-aware label policy is eligible for a controlled retrain sweep only. It does not approve paper trading or real-live trading.

BLOCK means do not retrain with the tested policies yet. Review the reason codes, especially:

- TARGET_ACTION_COVERAGE_HIGH
- TARGET_ACTION_COVERAGE_LOW
- TARGET_HOLD_COVERAGE_LOW
- TARGET_ACTION_SIDE_IMBALANCE_HIGH
- EXPECTED_NET_EDGE_LOW
- EFFECTIVE_MIN_PROFIT_BELOW_COST_FLOOR
- FORWARD_RETURN_SEPARATION_LOW

## Policy

Real live trading remains blocked. Paper trading remains blocked until a later phase explicitly approves it based on model, calibration, and soak evidence.
