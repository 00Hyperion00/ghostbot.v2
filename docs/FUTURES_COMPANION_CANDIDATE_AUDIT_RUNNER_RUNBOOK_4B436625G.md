# 4B.4.3.6.6.25G Futures Companion Candidate Audit Runner

This patch prepares a no-order companion audit package for the futures funding hypothesis branch.

## Purpose

25F concluded that the BTCUSDT primary branch remained too sparse or terminally blocked, while the ETHUSDT companion candidate from 25B still required the same dry-run and median-edge refinement audit chain. 25G reads existing 25B/25C/25D/25E reports, selects the ETHUSDT `4h` `funding_trend_exhaustion` companion candidate, writes a companion spec, and emits the exact commands needed for 25D and 25E.

## Guardrails

- Training remains blocked.
- Paper/live remain blocked.
- No market data is fetched by this runner.
- No POST requests are made.
- No model reload is performed.
- No config mutation is performed.
- No orders are sent.

## Run

```powershell
python tools/run_futures_companion_candidate_audit_runner_4B436625G.py `
  --input-json reports\4B436625B_futures_funding_open_interest_edge_exploration_20260508_094539.json `
  --input-json reports\4B436625C_futures_candidate_robustness_audit_20260508_103728.json `
  --input-json reports\4B436625D_futures_research_candidate_simulator_20260508_082617.json `
  --input-json reports\4B436625E_futures_candidate_refinement_median_edge_recovery_20260508_135957.json `
  --out-dir reports `
  --review-ok
```

## Decision Meanings

- `COMPANION_AUDIT_READY`: ETH companion spec and downstream commands were generated. This is not a research PASS.
- `COMPANION_AUDIT_CONFIRMED`: downstream ETH audit evidence is present. The next phase must still gate it explicitly.
- `COMPANION_AUDIT_BLOCKED`: no valid ETH companion candidate was found.

Backtest PASS is not paper permission. Paper PASS is not live permission.
