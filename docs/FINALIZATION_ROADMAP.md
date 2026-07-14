# TradeBot Finalization Roadmap

This roadmap defines the remaining work to move the repository from a heavily governed hardening branch to a maintainable production-ready runtime. It is intentionally ordered to avoid weakening existing no-submit, paper/live, and Operator Cockpit safety gates.

## Current status

The project already has these production-readiness foundations:

- Python package/runtime entrypoints for bot, API, cockpit, AI service, and training.
- Operator Cockpit as the preferred guarded control surface.
- SQLite runtime/audit persistence.
- AI provider fallback telemetry and training quality-gate responses.
- Local destructive endpoint token validation helpers.
- Phase/runbook evidence for paper-to-live readiness review gates; recent phase notes still state no runtime start, paper/network order, private API access, live-real approval, or exchange-submit enablement.

## P0 — Freeze the active runtime contract

Goal: make the current exported behavior explicit before any large refactor.

Remaining work:

1. Document the final exported app factories and aliases in `tradebot.api`.
2. Add a focused test that imports `tradebot.api.create_app` and `create_managed_app` and asserts the final aliases are the intended active implementations.
3. Add route contract tests for `/health`, `/status`, `/logs`, `/ai/reload`, `/ai/train`, and destructive/no-submit endpoints.
4. Capture the active exchange-submit call chain and prove no submit can happen without preflight, sizing, risk, reconciliation, and operator controls.

Exit criteria:

- API compatibility tests pass in one documented command.
- Destructive and exchange-submit paths have explicit fail-closed regression tests.
- The current runtime contract is documented in one place.

## P1 — Split legacy compatibility from canonical runtime

Goal: reduce `api.py`/`engine.py` overlay complexity without breaking historical tests.

Remaining work:

1. Move final compatibility helpers into a dedicated module such as `tradebot.api_compat` or `tradebot.legacy.api_overlays`.
2. Keep public aliases stable from `tradebot.api` while moving implementation in small tested steps.
3. Add import-path compatibility tests before every move.
4. Convert historical phase overlays into documented legacy shims only after tests prove behavior is unchanged.

Exit criteria:

- `tradebot.api` becomes a thin public facade.
- Active runtime implementation has one canonical location.
- Legacy overlays remain importable or have explicit deprecation shims.

## P2 — Cockpit-first operator workflow closure

Goal: make Operator Cockpit the only write/control workflow for production-like operation.

Remaining work:

1. Verify cockpit action endpoints enforce auth, operator identity, typed confirmation, runtime lock, reconciliation, and risk guard behavior.
2. Ensure legacy destructive API endpoints stay fail-closed or delegate to the same cockpit guard contract.
3. Add audit assertions for every protected operator action.
4. Add a cockpit route inventory with read-only vs destructive classification.

Exit criteria:

- All destructive actions produce audit records.
- Legacy destructive endpoints cannot bypass cockpit-equivalent controls.
- Entry guard, reconciliation guard, and runtime lock states are visible to operators.

## P3 — Runtime lifecycle and shutdown hardening

Goal: ensure long-running tasks, exchange clients, persistence handles, and background workers close deterministically.

Remaining work:

1. Audit all async tasks created by engine, cockpit broadcaster, managed API lifespan, and dashboard subprocess tooling.
2. Add tests for repeated start/stop/restart and cancellation timeout paths.
3. Replace silent broad exception swallowing in active runtime paths with rate-limited observable events where safe.
4. Confirm SQLite connections and exchange sessions are closed on every shutdown path.

Exit criteria:

- Repeated lifecycle tests pass without leaked tasks or open sessions.
- Shutdown errors are observable but non-fatal.
- Managed API lifespan degrades safely on startup failure and closes resources on exit.

## P4 — AI/model lifecycle production closure

Goal: make AI reload/training behavior operationally safe and auditable.

Remaining work:

1. Persist model reload decisions and quality-gate payloads to the audit log.
2. Include model artifact hash, schema path, manifest path, feature schema version, and quality decision in reload responses.
3. Add tests that reload never mutates active settings when provider load fails.
4. Add model staleness and schema mismatch checks to the operator-facing status payload.

Exit criteria:

- Weak models block reload with structured reasons.
- Failed reloads preserve active settings and provider state.
- Operators can see active model identity, schema status, and quality gate state.

## P5 — Paper/live transition evidence closure

Goal: turn the many phase runbooks into a single auditable transition checklist.

Remaining work:

1. Consolidate paper sandbox, paper-to-live, live-real readiness, credential isolation, endpoint separation, and rollback criteria into one operator checklist.
2. Link each checklist item to the report/test that proves it.
3. Require explicit human approval artifacts for any live-real transition.
4. Keep exchange-submit disabled until every checklist item is green.

Exit criteria:

- There is one paper-to-live checklist with evidence links.
- Live-real readiness cannot be inferred from docs alone; it must be proven by reports/tests.
- Rollback and kill-switch drills are part of the required evidence.

## Recommended next implementation order

1. Add final API alias/route contract tests.
2. Extract active API compatibility helpers behind a stable facade.
3. Add cockpit destructive action audit coverage.
4. Add managed runtime lifecycle leak/shutdown tests.
5. Persist AI reload quality-gate decisions.
6. Consolidate paper-to-live evidence into a single checklist.

## High-value validation command

```bash
PYTHONPATH=src pytest -q \
  tests/test_api_logs_compat.py \
  tests/test_api_ai_reload.py \
  tests/test_api_start_stop.py \
  tests/test_model_retrain_reload_workflow.py \
  tests/test_api_auth_destructive_endpoint_guard_4B436637E.py \
  tests/test_strategy_ai_merge.py
python -m compileall -q src/tradebot tests
```
