# 4B.4.3.6.6.25C Futures Candidate Robustness / Data Coverage Audit

## Purpose

25C audits 25B futures funding/open-interest research candidates before any further modeling work. It checks whether the apparent edge is supported by enough signals, acceptable drawdown, positive OOS edge, profit factor, cross-symbol confirmation, and available data coverage fields.

## Guardrails

- Observation only.
- Public research reports only.
- No POST requests.
- No config mutation.
- No model training.
- No model reload.
- No paper trading.
- No live trading.

Backtest PASS is not paper permission.
Paper PASS is not live permission.

## Example

```powershell
python tools/run_futures_candidate_robustness_audit_4B436625C.py `
  --input-json reports/4B436625B_futures_funding_open_interest_edge_exploration_20260508_092725.json `
  --input-json reports/4B436625B_futures_funding_open_interest_edge_exploration_20260508_094539.json `
  --out-dir reports `
  --review-ok
```

Or auto-discover recent 25B reports:

```powershell
python tools/run_futures_candidate_robustness_audit_4B436625C.py `
  --reports-dir reports `
  --include-all `
  --out-dir reports `
  --review-ok
```

## Result interpretation

PASS means a futures research candidate survived robustness review and may move to the next controlled research phase.

PASS does not allow training, reload, paper trading, or live trading.

BLOCK means the futures candidate is not robust enough for the next phase.
