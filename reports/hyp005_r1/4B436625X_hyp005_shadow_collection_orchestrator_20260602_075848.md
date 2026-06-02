# 4B.4.3.6.6.25X HYP-005 Shadow Collection Orchestrator

- contract_version: `4B.4.3.6.6.25X`
- decision: **HYP005_SHADOW_COLLECTION_ORCHESTRATOR_BLOCK**
- hypothesis_id: `HYP-005`
- branch_name: `liquidity_sweep_reversal_vol_compression_r1_pruned_symbol_revalidation`
- selected_strategy_family: `long_liquidity_sweep_reversal`
- shadow_collection_ready: `False`
- no_order_collection_only: `True`
- approved_for_shadow_collection: `False`
- approved_for_paper_transition_candidate: `False`
- approved_for_paper_candidate: `False`
- approved_for_live_real: `False`

## Progress

- shadow_observation_count: `0`
- shadow_sample_target: `30`
- progress_pct: `0.0`
- duplicate_observation_count: `0`
- duplicate_observation_pct: `0.0`

## Commands

### collect_shadow_observations_no_order

Refresh no-order HYP-005 shadow observations. This command must remain GET-only and order-disabled.

```powershell
python tools/run_hyp005_shadow_observation_logger_4B436625V.py `
  --candidate-spec-json C:\Users\muhas\OneDrive\Masaüstü\trade_botV2\reports\4B436625AE_hyp005_r1_windows_task_scheduler_pack_20260602_075823\hyp005_r1_runtime_candidate_spec.json `
  --symbols ADAUSDT,BNBUSDT,BTCUSDT,ETHUSDT,LINKUSDT,LTCUSDT,SOLUSDT,XRPUSDT `
  --interval 4h `
  --days 30 `
  --base-url https://api.binance.com `
  --out-dir C:\Users\muhas\OneDrive\Masaüstü\trade_botV2\reports\hyp005_r1 `
  --review-ok
```

### evaluate_shadow_acceptance_readiness

Re-evaluate paper-transition readiness from accumulated shadow ledgers. This does not enable paper trading.

```powershell
python tools/run_hyp005_shadow_acceptance_readiness_4B436625W.py `
  --reports-dir C:\Users\muhas\OneDrive\Masaüstü\trade_botV2\reports\hyp005_r1 `
  --include-all `
  --out-dir C:\Users\muhas\OneDrive\Masaüstü\trade_botV2\reports\hyp005_r1 `
  --review-ok
```

## Guardrails

- This gate does not send orders.
- This gate does not start paper trading.
- This gate does not enable live trading.
- This gate does not train or reload models.
- Paper-transition readiness requires a separate gate and manual review.

## Reason Codes

```
[
  "HYP005_SHADOW_ACCEPTANCE_BLOCK_OR_PENDING_CONFIRMED",
  "HYP005_SHADOW_ACCEPTANCE_REPORT_MISSING",
  "HYP005_SHADOW_CANDIDATE_SPEC_CONFIRMED",
  "HYP005_SHADOW_COLLECTION_PREREQUISITES_NOT_MET",
  "HYP005_SHADOW_LOGGER_READY_NOT_CONFIRMED"
]
```

## Warnings

```
[
  "SHADOW_SAMPLE_COLLECTION_IN_PROGRESS"
]
```

Recommendation: HYP-005 shadow collection prerequisites are incomplete. Fix the missing no-order spec/logger/acceptance evidence before scheduling collection; do not train, reload, paper trade, or enable live trading.
