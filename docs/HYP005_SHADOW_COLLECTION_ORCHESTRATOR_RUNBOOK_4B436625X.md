# HYP-005 Shadow Collection Orchestrator / No-Order Scheduler Gate

Contract version: `4B.4.3.6.6.25X`

This gate advances HYP-005 from a ready no-order shadow logger to a repeatable
collection plan. It reads the 25U no-order candidate spec, the 25V logger report,
the 25W shadow acceptance report, and any 25V shadow ledgers. It then writes a
no-order scheduler plan, a merged de-duplicated ledger, and a progress report.

## Safety Policy

- No order actions are allowed.
- No POST requests are allowed.
- No paper trading is started.
- No live trading is enabled.
- No model training is performed.
- No model reload is performed.
- No config mutation is performed.
- Paper-transition readiness still requires a separate gate.
- Live trading requires a separate future gate.

## Expected Decision

When the 25U spec, 25V logger report, and 25W acceptance report are present and
safe, this gate returns:

`HYP005_SHADOW_COLLECTION_ORCHESTRATOR_READY`

This means only that the no-order collection plan is ready. It is not paper
permission and it is not live permission.

## Example

```powershell
python tools/run_hyp005_shadow_collection_orchestrator_4B436625X.py `
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

- `reports/4B436625X_hyp005_shadow_collection_orchestrator_*.json`
- `reports/4B436625X_hyp005_shadow_collection_orchestrator_*.md`
- `reports/4B436625X_hyp005_shadow_collection_plan_*.json`
- `reports/4B436625X_hyp005_shadow_merged_ledger_*.json`
- `reports/4B436625X_hyp005_shadow_merged_ledger_*.jsonl`

## Operational Use

Run the generated logger command after each fully closed 4h candle, or at least
once daily. Then run the generated 25W acceptance command to check whether the
shadow ledger has reached paper-transition readiness. Do not start paper trading
from this gate.
