# 4B.4.3.6.6.25X HYP-005 Shadow Collection Orchestrator

- contract_version: `4B.4.3.6.6.25X`
- decision: **HYP005_SHADOW_COLLECTION_ORCHESTRATOR_READY**
- hypothesis_id: `HYP-005`
- branch_name: `liquidity_sweep_reversal_vol_compression`
- selected_strategy_family: `long_liquidity_sweep_reversal`
- shadow_collection_ready: `True`
- no_order_collection_only: `True`
- approved_for_shadow_collection: `True`
- approved_for_paper_transition_candidate: `False`
- approved_for_paper_candidate: `False`
- approved_for_live_real: `False`

## Progress

- shadow_observation_count: `23`
- shadow_sample_target: `30`
- progress_pct: `76.666667`
- duplicate_observation_count: `1039`
- duplicate_observation_pct: `97.834275`

## Commands

### collect_shadow_observations_no_order

Refresh no-order HYP-005 shadow observations. This command must remain GET-only and order-disabled.

```powershell
python tools/run_hyp005_shadow_observation_logger_4B436625V.py `
  --candidate-spec-json reports\4B436625U_hyp005_no_order_shadow_candidate_spec_20260509_175722.json `
  --symbols ADAUSDT,AVAXUSDT,BNBUSDT,BTCUSDT,DOGEUSDT,ETHUSDT,LINKUSDT,LTCUSDT,SOLUSDT,XRPUSDT `
  --interval 4h `
  --days 30 `
  --base-url https://api.binance.com `
  --out-dir reports `
  --review-ok
```

### evaluate_shadow_acceptance_readiness

Re-evaluate paper-transition readiness from accumulated shadow ledgers. This does not enable paper trading.

```powershell
python tools/run_hyp005_shadow_acceptance_readiness_4B436625W.py `
  --reports-dir reports `
  --include-all `
  --out-dir reports `
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
  "HYP005_SHADOW_ACCEPTANCE_DECISION_CONFIRMED",
  "HYP005_SHADOW_CANDIDATE_SPEC_CONFIRMED",
  "HYP005_SHADOW_LOGGER_READY_CONFIRMED",
  "NO_ORDER_SHADOW_COLLECTION_PLAN_READY",
  "NO_TRAINING_PAPER_LIVE_APPROVALS_DETECTED"
]
```

## Warnings

```
[
  "SHADOW_DUPLICATE_OBSERVATIONS_ELEVATED",
  "SHADOW_SAMPLE_COLLECTION_IN_PROGRESS"
]
```

Recommendation: HYP-005 no-order shadow collection orchestrator is ready. Keep running the logger/scheduler until the shadow acceptance gate passes; do not train, reload, paper trade, or enable live trading.
