# 4B.4.3.6.6.25N Research Backlog Advancement After HYP-003 Closure

This gate advances the research backlog after 25M confirms HYP-003 as `CLOSED_NO_GO`.

## Purpose

25M confirmed the HYP-003 branch closure. 25N marks HYP-003 as closed in a proposed registry snapshot and selects the next pre-registered hypothesis for research-only exploration.

## Guardrails

- Training remains blocked.
- Paper/live remain blocked.
- No model reload is performed.
- No config mutation is performed.
- No order action is performed.
- No market data is fetched.
- A selected next hypothesis is not permission to train, paper trade, or live trade.

## Run with explicit 25M closure report

```powershell
python tools/run_research_backlog_after_hyp003_closure_4B436625N.py `
  --input-json reports\4B436625M_hyp003_branch_closure_evidence_pack_20260509_152006.json `
  --out-dir reports `
  --review-ok
```

## Run with latest 25M closure report discovery

```powershell
python tools/run_research_backlog_after_hyp003_closure_4B436625N.py `
  --reports-dir reports `
  --out-dir reports `
  --review-ok
```

## Expected Decision

`NEXT_HYPOTHESIS_SELECTED`

The default next hypothesis is `HYP-004` unless a registry JSON provides a different selectable next hypothesis by priority.
