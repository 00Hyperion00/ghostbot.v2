# 4B.4.3.6.6.25L-H1 Branch Closure CLI Hotfix

## Purpose

25L correctly produced `HYP003_BRANCH_CLOSURE_RECOMMENDED`, but the CLI crashed while printing `selected_next_candidate` because closure reports intentionally have no next candidate.

The failed path was:

```text
selected_next_candidate: None
AttributeError: 'NoneType' object has no attribute 'get'
```

## Fix

The CLI now uses `_candidate_key_text()` for both failed and selected candidates.

- Valid candidate keys are printed normally.
- Missing candidates are printed as `NONE`.
- Closure reports no longer crash after the report is generated.

## Guardrails

- No market data is fetched.
- No config is mutated.
- No model is trained or reloaded.
- No paper trading is started.
- No live trading is enabled.
- No orders are sent.

Paper/live remain blocked.

## Expected command

```powershell
python tools/run_hyp003_candidate_refinement_branch_decision_4B436625L.py `
  --input-json reports\4B436625J_hyp003_regime_strategy_exploration_20260509_110246.json `
  --input-json reports\4B436625K_hyp003_robustness_walkforward_confirmation_20260509_113143.json `
  --out-dir reports `
  --review-ok
```

Expected decision:

```text
HYP003_BRANCH_CLOSURE_RECOMMENDED
```
