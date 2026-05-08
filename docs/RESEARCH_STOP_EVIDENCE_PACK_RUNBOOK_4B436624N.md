# 4B.4.3.6.6.24N Research Stop / No-Edge Evidence Pack Runbook

## Purpose

24N consolidates the 24A-24M recovery and exploration reports into one no-go evidence pack. It is an observation-only report generator. It does not train models, reload models, mutate configuration, start paper trading, or send orders.

## Why this exists

The 24I-24M chain showed that a cost-aware label policy can be identified, but later retrain, two-stage, regime/meta-label, and symbol/timeframe/strategy exploration gates still failed to prove positive net edge. 24N freezes that evidence into a single operator-facing report.

## Usage

Generate from the latest report per phase in `reports`:

```powershell
python tools/run_research_stop_evidence_pack_4B436624N.py `
  --reports-dir reports `
  --out-dir reports `
  --review-ok
```

Generate from explicit report files:

```powershell
python tools/run_research_stop_evidence_pack_4B436624N.py `
  --input-json reports/4B436624J_cost_aware_retrain_sweep_YYYYMMDD_HHMMSS.json `
  --input-json reports/4B436624K_two_stage_action_side_recovery_YYYYMMDD_HHMMSS.json `
  --input-json reports/4B436624L_edge_meta_label_regime_recovery_YYYYMMDD_HHMMSS.json `
  --input-json reports/4B436624M_timeframe_symbol_strategy_edge_exploration_YYYYMMDD_HHMMSS.json `
  --review-ok
```

## Expected output

- `reports/4B436624N_research_stop_evidence_pack_*.json`
- `reports/4B436624N_research_stop_evidence_pack_*.md`

## Decision interpretation

`RESEARCH_STOP_NO_GO` means:

- Do not promote candidate models.
- Do not reload candidate models.
- Do not start paper trading.
- Do not enable live trading.
- Start only a new research cycle with a pre-registered hypothesis and acceptance metrics.

## Guardrails

24N always reports:

- `post_requests_allowed: false`
- `config_mutation_performed: false`
- `order_actions_performed: false`
- `reload_performed: false`
- `live_real_allowed: false`
- `promotion_performed: false`
