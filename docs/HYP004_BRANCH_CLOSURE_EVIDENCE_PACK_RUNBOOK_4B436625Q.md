# 4B.4.3.6.6.25Q HYP-004 Branch Closure Evidence Pack

This patch converts HYP-004 `cross_symbol_relative_strength_rotation` into a formal `CLOSED_NO_GO` evidence pack when 25O exploration and 25P refinement both fail to produce an approvable candidate.

## Required Evidence

- 25O `HYP004_EXPLORATION_BLOCK`
- 25P `HYP004_REFINEMENT_BLOCK`
- No passed exploration candidates
- No passed refined candidates
- No training, paper, live, reload, config mutation, or order approvals

Expected confirmed decision:

```text
HYP004_BRANCH_CLOSURE_CONFIRMED
```

## Guardrails

- Training remains blocked.
- Paper/live remain blocked.
- No market data is fetched.
- No POST requests are made.
- No config is mutated.
- No model is trained or reloaded.
- No orders are sent.

## Run

```powershell
python tools/run_hyp004_branch_closure_evidence_pack_4B436625Q.py `
  --input-json reports\4B436625O_hyp004_cross_symbol_relative_strength_exploration_20260509_153232.json `
  --input-json reports\4B436625P_hyp004_relative_strength_refinement_20260509_154507.json `
  --out-dir reports `
  --review-ok
```

Automatic scan:

```powershell
python tools/run_hyp004_branch_closure_evidence_pack_4B436625Q.py `
  --reports-dir reports `
  --include-all `
  --out-dir reports `
  --review-ok
```

## Outputs

- `reports/4B436625Q_hyp004_branch_closure_evidence_pack_*.json`
- `reports/4B436625Q_hyp004_branch_closure_evidence_pack_*.md`
- `reports/4B436625Q_hyp004_branch_closure_registry_snapshot_*.json`

This closure pack prepares the backlog for the next pre-registered hypothesis only. It is not paper or live trading permission.
