# HYP-005 Shadow Operator Runbook / Daily No-Order Audit Pack

Contract version: `4B.4.3.6.6.25Y`

This patch adds a daily operator audit pack for the HYP-005 no-order shadow process.
It reads the 25U candidate spec, 25V logger output, 25X collection orchestrator output,
25W acceptance/readiness output, and available shadow ledgers.

## Purpose

- Summarize the latest HYP-005 shadow status.
- Show sample progress toward the shadow acceptance target.
- Show whether paper-transition readiness is still blocked.
- Produce a dashboard JSON and operator runbook Markdown.
- Keep the system strictly no-order.

## Paper/live remain blocked

25Y is not a trading enablement patch.
It does not start paper trading, live trading, model training, reload, config mutation, or orders.

A paper-transition-ready result from 25W still requires a separate future paper-enablement gate.

## Expected current state

With the current 25V/25W chain, the expected state is:

- `shadow_observation_count: 0`
- `shadow_sample_target: 30`
- `dashboard_status: SHADOW_COLLECTION_IN_PROGRESS`
- `approved_for_paper_candidate: False`
- `approved_for_live_real: False`

## Usage

```powershell
python tools/run_hyp005_shadow_operator_runbook_4B436625Y.py `
  --reports-dir reports `
  --include-all `
  --symbols BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT `
  --interval 4h `
  --days 30 `
  --base-url https://api.binance.com `
  --out-dir reports `
  --review-ok
```

## Outputs

- `reports/4B436625Y_hyp005_shadow_operator_daily_audit_*.json`
- `reports/4B436625Y_hyp005_shadow_operator_daily_audit_*.md`
- `reports/4B436625Y_hyp005_shadow_operator_dashboard_*.json`
- `reports/4B436625Y_hyp005_shadow_operator_runbook_*.md`
