# 4B.4.3.6.6.25F Futures Hypothesis Branch Review / Candidate Closure Decision

This patch reviews the HYP-002 `funding_trend_exhaustion` futures branch after 25B/25C/25D/25E.

It does not fetch market data and it does not create new signals. It reads prior evidence reports and decides whether the branch is:

- `BRANCH_REVIEW_PENDING_COMPANION_AUDIT`
- `BRANCH_CLOSED_NO_GO`
- `BRANCH_RESEARCH_CONTINUE`
- `BRANCH_REVIEW_INCONCLUSIVE`

## Safety Policy

Training remains blocked.
Paper/live remain blocked.
Model reload remains blocked.
Order actions remain blocked.
Config mutation remains blocked.

A continuation decision is research-only and is not paper permission.

## Recommended Run

```powershell
python tools/run_futures_hypothesis_branch_review_4B436625F.py `
  --input-json reports\4B436625B_futures_funding_open_interest_edge_exploration_20260508_094539.json `
  --input-json reports\4B436625C_futures_candidate_robustness_audit_20260508_103728.json `
  --input-json reports\4B436625D_futures_research_candidate_simulator_20260508_082617.json `
  --input-json reports\4B436625E_futures_candidate_refinement_median_edge_recovery_20260508_135957.json `
  --out-dir reports `
  --review-ok
```

Alternative:

```powershell
python tools/run_futures_hypothesis_branch_review_4B436625F.py `
  --reports-dir reports `
  --include-all `
  --out-dir reports `
  --review-ok
```

## Interpretation

If BTC is too sparse or outlier-dependent but ETH has only 25B exploration evidence, the correct decision is pending companion audit, not training.

If BTC and ETH both fail terminal dry-run/refinement checks, close this branch and require a materially different pre-registered futures hypothesis.
