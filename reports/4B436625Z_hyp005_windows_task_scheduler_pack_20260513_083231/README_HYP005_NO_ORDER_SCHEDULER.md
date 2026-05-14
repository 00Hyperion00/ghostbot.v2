# HYP-005 No-Order Shadow Collection Scheduler Pack

- contract_version: `4B.4.3.6.6.25Z`
- task_name: `TradeBot_HYP005_NoOrderShadowCollection`
- cadence_hours: `4`
- symbols: `BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT`
- interval: `4h`
- days: `30`
- base_url: `https://api.binance.com`

## Safety

This pack is no-order only. It does not train, reload, paper trade, live trade, mutate config, or send orders.

## Current State From 25Y

- latest_logger_decision: `HYP005_SHADOW_OBSERVATION_LOGGER_READY`
- latest_collection_decision: `HYP005_SHADOW_COLLECTION_ORCHESTRATOR_READY`
- latest_acceptance_decision: `HYP005_SHADOW_PAPER_TRANSITION_BLOCK`
- shadow_observation_count: `0`
- shadow_sample_target: `30`
- paper_transition_ready: `False`

## Manual Steps

1. Review `run_hyp005_shadow_cycle_no_order.ps1`.
2. Run it manually once from PowerShell.
3. Review the generated 25V/25X/25W/25Y reports.
4. Only after review, optionally run `register_hyp005_shadow_cycle_task.ps1` as a Windows Task Scheduler helper.

## Important

Paper-transition readiness is not paper permission. Paper/live remain blocked until a separate explicit enablement gate exists and passes.
