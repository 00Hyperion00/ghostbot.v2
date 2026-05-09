# 4B.4.3.6.6.25I Research Backlog Advancement / Next Hypothesis Selection Gate

## Purpose

25H closed HYP-002 `futures_funding_trend_exhaustion` as `FUTURES_BRANCH_CLOSURE_CONFIRMED`. 25I advances the research backlog only after that closure evidence is present. It marks HYP-002 as `CLOSED_NO_GO` in a proposed registry snapshot and selects the next safe registered hypothesis.

## Safety Policy

Training remains blocked.
Paper/live remain blocked.
Model reload remains blocked.
Order actions remain blocked.
Config mutation remains blocked.

A selected next hypothesis is research-only. It is not permission to train, reload, paper trade, or live trade.

## Main Command

```powershell
python tools/run_research_backlog_advancement_4B436625I.py `
  --reports-dir reports `
  --include-all `
  --registry-json config\research_hypotheses_4B436624O.json `
  --out-dir reports `
  --review-ok
```

If the registry file is missing, the tool falls back to a built-in conservative backlog.

## Explicit Closure Report Command

```powershell
python tools/run_research_backlog_advancement_4B436625I.py `
  --input-json reports\4B436625H_futures_branch_closure_evidence_pack_20260509_014428.json `
  --out-dir reports `
  --review-ok
```

## Expected Result

```text
NEXT_HYPOTHESIS_SELECTED
```

Expected default next hypothesis when no custom registry overrides it:

```text
HYP-003 — Regime-filtered volatility expansion breakout
```

## Outputs

- `reports/4B436625I_research_backlog_advancement_*.json`
- `reports/4B436625I_research_backlog_advancement_*.md`
- `reports/4B436625I_proposed_research_registry_snapshot_*.json`

## Policy

25I only advances the backlog. The next hypothesis must pass its own future exploration, robustness, dry-run, and evidence gates before any model training or paper/live discussion.
