# 4B.4.3.6.6.25AE — HYP-005-R1 Eight-Symbol No-Order Shadow Scheduler Regeneration Pack

This operator-reviewed pack is generated only after the 25AD baseline-freeze planning report is ready.

## Purpose

- Create a separate `HYP-005-R1` no-order shadow scheduler pack.
- Enforce the fresh ledger namespace `HYP005_R1`.
- Use only eight refined symbols: `ADAUSDT,BNBUSDT,BTCUSDT,ETHUSDT,LINKUSDT,LTCUSDT,SOLUSDT,XRPUSDT`.
- Exclude `AVAXUSDT` and `DOGEUSDT` from refined revalidation.
- Write R1 runtime outputs only under `reports\hyp005_r1`.
- Prevent reuse of legacy baseline observations.

## Operator controls

The pack generator requires `--baseline-task-disabled` and `--review-ok`. The generated Windows registration helper independently checks that `TradeBot_HYP005_NoOrderShadowCollection` is in the `Disabled` state before registering `TradeBot_HYP005_R1_NoOrderShadowCollection`.

## Safety

Paper/live remain blocked. Training, model reload, POST requests, order actions, automatic scheduler mutation, and baseline ledger reuse are not allowed.
