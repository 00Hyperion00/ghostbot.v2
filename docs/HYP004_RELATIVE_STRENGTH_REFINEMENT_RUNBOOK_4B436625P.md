# 4B.4.3.6.6.25P HYP-004 Relative Strength Candidate Refinement / Approvable Strategy Gate

## Purpose

25O found positive-looking relative-strength metrics, but the candidate did not pass the exploration gate. 25P takes the near-miss `laggard_reversion` family and tests non-diagnostic, guarded variants with stricter stability requirements.

## What it checks

- non-diagnostic laggard-reversion variants
- spread threshold sensitivity
- lookback / holding horizon sensitivity
- signal count
- mean and median edge
- OOS edge
- walk-forward stability
- dominant-symbol dependency
- top-win dependency
- traded-symbol coverage

## Guardrails

- Training remains blocked.
- Paper/live remain blocked.
- No model reload.
- No config mutation.
- No order actions.
- Public market data GET only when not using `--input-csv`.

A PASS is research-only and must go to a later robustness gate before any paper/live discussion.

## Apply

```powershell
cd C:\Users\user\OneDrive\Masaüstü\trade_botV2

Expand-Archive -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436625P_hyp004_relative_strength_refinement_patch.zip" -DestinationPath . -Force

python tools/apply_4B436625P_hyp004_relative_strength_refinement.py
```

## Test

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH="src"

python -m pytest -q tests/test_hyp004_relative_strength_refinement_4B436625P.py
```

Expected:

```text
5 passed
```

## Run

```powershell
python tools/run_hyp004_relative_strength_refinement_4B436625P.py `
  --input-json reports\4B436625O_hyp004_cross_symbol_relative_strength_exploration_20260509_153232.json `
  --symbols BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT `
  --interval 4h `
  --days 90 `
  --base-url https://api.binance.com `
  --out-dir reports `
  --review-ok
```

## Output

```text
reports\4B436625P_hyp004_relative_strength_refinement_*.json
reports\4B436625P_hyp004_relative_strength_refinement_*.md
```

If a refined candidate passes, the tool also writes:

```text
reports\4B436625P_hyp004_next_candidate_for_25Q_*.json
```

## Policy

25P never trains, reloads, starts paper trading, enables live trading, mutates config, or sends orders.
