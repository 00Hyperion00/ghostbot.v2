# 4B.4.3.6.6.25R Research Backlog Advancement After HYP-004 Closure

This patch advances the research backlog after the HYP-004 `cross_symbol_relative_strength_rotation` branch is closed by the 25Q evidence pack.

## Purpose

25Q confirms that HYP-004 has no approvable exploration or refinement candidate. 25R records HYP-004 as `CLOSED_NO_GO` and selects the next pre-registered hypothesis for research-only exploration.

Default next hypothesis:

- `HYP-005` — Liquidity sweep reversal with volatility compression filter
- branch: `liquidity_sweep_reversal_vol_compression`

## Safety Policy

- Training remains blocked.
- Paper/live remain blocked.
- No market data is fetched.
- No POST requests are sent.
- No model is trained or reloaded.
- No config mutation is performed.
- No orders are sent.

A selected next hypothesis is research-only. It is not paper permission and not live permission.

## Run

```powershell
python tools/run_research_backlog_after_hyp004_closure_4B436625R.py `
  --reports-dir reports `
  --out-dir reports `
  --review-ok
```

Or with an explicit closure report:

```powershell
python tools/run_research_backlog_after_hyp004_closure_4B436625R.py `
  --input-json reports\4B436625Q_hyp004_branch_closure_evidence_pack_20260509_155354.json `
  --out-dir reports `
  --review-ok
```

Expected decision:

```text
NEXT_HYPOTHESIS_SELECTED
```

## Outputs

- `reports/4B436625R_research_backlog_after_hyp004_closure_*.json`
- `reports/4B436625R_research_backlog_after_hyp004_closure_*.md`
- `reports/4B436625R_proposed_research_registry_snapshot_*.json`
