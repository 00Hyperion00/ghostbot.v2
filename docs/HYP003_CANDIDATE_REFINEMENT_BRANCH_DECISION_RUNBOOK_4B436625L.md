# 4B.4.3.6.6.25L HYP-003 Candidate Refinement / Branch Decision Gate

25L reviews the HYP-003 research chain after a 25J exploration PASS and a 25K robustness BLOCK.

## Purpose

- Mark the selected 25J candidate as terminal-failed when 25K BLOCKs it.
- Inspect remaining 25J PASS candidates.
- Select the next candidate for a dedicated 25K robustness run when one exists.
- Recommend HYP-003 branch closure when no alternate candidate remains.

## Safety Policy

- No market data is fetched.
- No POST requests are made.
- No config is mutated.
- No model is trained or reloaded.
- No paper trading is started.
- No live trading is enabled.
- No orders are sent.

Paper/live remain blocked.

## Run

```powershell
python tools/run_hyp003_candidate_refinement_branch_decision_4B436625L.py `
  --input-json reports\4B436625J_hyp003_regime_strategy_exploration_20260509_110246.json `
  --input-json reports\4B436625K_hyp003_robustness_walkforward_confirmation_20260509_113143.json `
  --out-dir reports `
  --review-ok
```

Alternative discovery:

```powershell
python tools/run_hyp003_candidate_refinement_branch_decision_4B436625L.py `
  --reports-dir reports `
  --include-all `
  --out-dir reports `
  --review-ok
```

## Decisions

- `HYP003_NEXT_CANDIDATE_SELECTED_FOR_ROBUSTNESS`: another 25J PASS candidate exists; run 25K against the generated next-candidate JSON.
- `HYP003_BRANCH_CLOSURE_RECOMMENDED`: selected candidate failed 25K and no alternate 25J PASS candidate meets refinement criteria.
- `HYP003_BRANCH_RESEARCH_CONTINUE`: 25K already passed; continue only to no-order planning.
- `HYP003_BRANCH_DECISION_PENDING_ROBUSTNESS`: 25K evidence is missing.

## Next Candidate Output

When an alternate candidate is selected, 25L writes:

```text
reports\4B436625L_hyp003_next_candidate_for_25K_*.json
```

Use that as `--input-json` for 25K.
