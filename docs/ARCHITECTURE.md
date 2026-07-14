# TradeBot Production Architecture & Operating Guide

This document is the canonical production-readiness map for the active TradeBot runtime. Historical phase notes and evidence packs remain useful, but this file defines the preferred path for new development, operator workflows, and safety reviews.

## Current production intent

TradeBot is a Python spot-trading runtime with these active responsibilities:

1. Collect market data from the configured exchange environment.
2. Produce a deterministic technical signal and optionally normalize it with the configured AI provider.
3. Gate every entry/exit action through runtime, reconciliation, sizing, risk, and operator controls.
4. Persist runtime state, audit events, orders, fills, positions, risk events, model decisions, and balance snapshots in SQLite.
5. Expose operator controls through the guarded Operator Cockpit rather than unguarded legacy destructive API paths.

## Canonical runtime flow

```text
tradebot cockpit --config config.local.yaml
  -> Settings.from_yaml(...)
  -> create_cockpit_app(...)
  -> TradeBotOrchestrator
  -> TradeBotEngine
  -> BinanceSpotClient
  -> evaluate_technical_strategy(...)
  -> normalize_signal_with_ai(...)
  -> order/risk/sizing/preflight/reconciliation gates
  -> guarded exchange adapter call, when explicitly allowed
  -> SQLiteStore audit/runtime persistence
```

## Canonical control plane

The Operator Cockpit is the preferred control plane for production-like operation. Destructive actions should stay behind:

- local/API authentication checks,
- operator identity checks,
- typed confirmation where required,
- runtime lock and duplicate-instance checks,
- reconciliation and risk badge checks,
- append-only operator action audit records.

Legacy destructive API endpoints must remain fail-closed unless a future migration explicitly proves parity with the cockpit guard chain.

## Safety boundaries

Default runtime posture is intentionally conservative:

- dry-run execution is the default,
- live trading is not armed by default,
- live-real operation requires explicit double-confirm style controls,
- AI provider failures must not crash the runtime,
- AI provider failures must be observable through audit/logging,
- exchange-submit paths must never bypass preflight, sizing, risk, and reconciliation checks.

## AI decision path

The AI layer is a normalization layer, not an unconditional execution authority:

1. The technical strategy produces the base `SignalDecision`.
2. If local XGBoost is enabled and available, the AI provider may return an action or an AI-held decision.

## Persistence contract

SQLite is the local source of runtime evidence. Production-facing changes should preserve or migrate these record types:

- runtime key/value state,
- logs,
- operator actions,
- orders,
- fills,
- positions,
- risk events,
- model decisions,
- balance snapshots.

Schema changes should be additive or explicitly migrated with tests. WAL, busy timeout, and foreign key behavior are part of the persistence hardening posture.

## Recommended target directory model

The repository currently contains many historical phase and hotfix modules. Do not move them casually because tests and evidence references may depend on their paths. New development should converge toward this logical model:

```text
src/tradebot/
  api/ or api.py                  # external API surface; keep destructive routes guarded
  cockpit/                        # canonical operator control plane
  engine.py                       # runtime orchestration; gradually split only with tests
  exchange/                       # exchange adapters and environment routing
  strategy.py                     # technical + AI signal normalization
  ai/                             # providers, decision contract, AI service
  training/                       # model training, schema, labeling, calibration
  persistence.py                  # SQLite store and migrations
  risk.py / position_sizing.py    # risk plan and deterministic sizing contracts
  safety/                         # future home for consolidated gates/guards
  legacy/                         # future home for retained compatibility shims
```

## Refactoring rules for future work

1. Prefer safe, tested extraction over large file moves.
2. Keep public import paths stable until a compatibility shim and migration note exist.
3. Do not weaken live-real, exchange-submit, destructive-action, or auth gates to make tests pass.
4. Any fallback from AI, exchange, persistence, or reconciliation failures must be observable.
5. New order paths require tests that prove no submit occurs when any guard is red.

## Local runbook

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Run the guarded cockpit:

```bash
tradebot cockpit --config config.local.yaml
```

Run the managed API for local integration checks:

```bash
tradebot api --config examples/config.demo.yaml
```

Run AI service separately:

```bash
tradebot ai-service --model-path models/SOLUSDT_model.ubj --threshold 0.60
```

Train a model:

```bash
tradebot train-model --symbol SOLUSDT --interval 1m --days 30 --out models/SOLUSDT_model.ubj
```

Run focused validation:

```bash
PYTHONPATH=src pytest -q tests/test_strategy_ai_merge.py
python -m compileall -q src/tradebot tests
```
