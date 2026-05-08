# 4B.4.3.6.6.25F-H1 Companion Terminal Audit Recognition Hotfix

This hotfix repairs the 25F branch-review parser so it recognizes completed companion 25D and 25E terminal audit reports.

## What changed

- 25D dry-run reports with `selected` as an object and metrics under `candidate.metrics` are normalized correctly.
- 25E refinement reports with symbol/interval/strategy under `candidate_spec` and metrics under `selected.metrics` are normalized correctly.
- Terminal dry-run/refinement reason codes such as `DRY_RUN_OOS_EDGE_LOW`, `REFINEMENT_MEAN_EDGE_LOW`, and `REFINEMENT_MEDIAN_EDGE_LOW` are recognized.
- If the BTC primary and ETH companion both have terminal 25D/25E BLOCK evidence, 25F can now return `BRANCH_CLOSED_NO_GO` instead of remaining stuck at `BRANCH_REVIEW_PENDING_COMPANION_AUDIT`.

## Guardrails

- No market data is fetched.
- No config is mutated.
- No model is trained or reloaded.
- No paper trading is started.
- No live trading is enabled.
- No orders are sent.

Paper/live remain blocked.

## Validation

Run:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH="src"

python -m pytest -q `
tests/test_futures_hypothesis_branch_review_hotfix_25FH1.py `
tests/test_futures_hypothesis_branch_review_4B436625F.py
```

Expected:

```text
8 passed
```

Then rerun 25F:

```powershell
python tools/run_futures_hypothesis_branch_review_4B436625F.py `
  --reports-dir reports `
  --include-all `
  --out-dir reports `
  --review-ok
```

Expected decision after BTC and ETH terminal 25D/25E BLOCK evidence is present:

```text
BRANCH_CLOSED_NO_GO
```
