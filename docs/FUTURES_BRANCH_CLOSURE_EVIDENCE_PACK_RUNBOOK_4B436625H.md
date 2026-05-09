# 4B.4.3.6.6.25H Futures Branch Closure Evidence Pack

This patch seals the HYP-002 `funding_trend_exhaustion` futures branch after final branch review produced `BRANCH_CLOSED_NO_GO`.

## Purpose

25H reads the 25B/25C/25D/25E/25F/25G report chain and generates a single evidence pack that records why the branch is closed. It is intentionally a documentation and governance tool, not a trading or training tool.

## Required evidence

- Final 25F report decision is `BRANCH_CLOSED_NO_GO`.
- Primary BTCUSDT 4h `funding_trend_exhaustion` has terminal 25D/25E block evidence.
- Companion ETHUSDT 4h `funding_trend_exhaustion` has terminal 25D/25E block evidence.
- No training, paper, live, reload, order, or config mutation approvals are present.

## Guardrails

- Paper/live remain blocked.
- No market data is fetched.
- No POST requests are made.
- No config is mutated.
- No model is trained or reloaded.
- No paper trading is started.
- No live trading is enabled.
- No orders are sent.

## Run

```powershell
python tools/run_futures_branch_closure_evidence_pack_4B436625H.py `
  --reports-dir reports `
  --include-all `
  --out-dir reports `
  --review-ok
```

Expected decision after 25F final closure evidence is present:

```text
FUTURES_BRANCH_CLOSURE_CONFIRMED
```

## Policy

A closure evidence pack is not permission to train, paper trade, or live trade. It only records that this branch is closed no-go and the next cycle must start with a new pre-registered edge hypothesis.
