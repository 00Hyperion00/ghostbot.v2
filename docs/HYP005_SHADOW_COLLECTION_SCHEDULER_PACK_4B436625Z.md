# 4B.4.3.6.6.25Z — HYP-005 Shadow Collection Automation Script / Windows Task Scheduler Pack

This patch generates a Windows Task Scheduler pack for the HYP-005 no-order shadow collection cycle.

## Purpose

The pack creates reviewed operator artifacts:

- `run_hyp005_shadow_cycle_no_order.ps1`
- `register_hyp005_shadow_cycle_task.ps1`
- `hyp005_shadow_collection_task.xml`
- `README_HYP005_NO_ORDER_SCHEDULER.md`

## Safety

Paper/live remain blocked.

The generated cycle runs only:

1. 25V shadow observation logger
2. 25X shadow collection orchestrator
3. 25W shadow acceptance/readiness
4. 25Y operator audit pack

It does not train, reload, mutate config, start paper trading, enable live trading, or send orders.

## Usage

```powershell
python tools/run_hyp005_shadow_collection_scheduler_pack_4B436625Z.py `
  --reports-dir reports `
  --include-all `
  --symbols BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT `
  --interval 4h `
  --days 30 `
  --base-url https://api.binance.com `
  --out-dir reports `
  --review-ok
```

Review the generated scripts before optionally registering the task.
