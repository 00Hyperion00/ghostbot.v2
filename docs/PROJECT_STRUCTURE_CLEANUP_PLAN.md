# Project Structure Cleanup Plan

This repository has accumulated many phase/hotfix/evidence files. Production cleanup must be staged so runtime safety contracts are not removed while tests still depend on them.

## Canonical target structure

```text
src/tradebot/
  api.py                  # stable API facade until routes are split safely
  cli.py                  # process entrypoints
  config.py               # public settings contract
  engine.py               # runtime orchestration
  strategy.py             # technical + AI signal normalization
  models.py               # domain objects
  persistence.py          # SQLite store
  ai/                     # model provider, decision contract, feature schema
  exchange/               # exchange adapters only
  cockpit/                # canonical operator control-plane web app
    app.py                # FastAPI cockpit routes
    static/               # legacy cockpit retained for compatibility tests
    clean_static/         # new clean dashboard UI
  training/               # training pipeline and CLI helpers
  production_hardening/   # static safety/evidence helpers until archived

docs/
  ARCHITECTURE.md
  FINALIZATION_ROADMAP.md
  PROJECT_STRUCTURE_CLEANUP_PLAN.md
  archive/                # future destination for phase/hotfix history

tests/
  api/
  cockpit/
  engine/
  security/
  ai/
  legacy/                 # future destination for phase compatibility tests
```

## Cleanup policy

1. Do not delete a phase/hotfix module until its behavior is covered by a canonical runtime/API/cockpit test.
2. Keep `src/tradebot/cockpit/static/` until existing Operator Cockpit regression tests are migrated.
3. Use `src/tradebot/cockpit/clean_static/` as the new clean dashboard surface. It is read-first, lightweight and uses existing cockpit endpoints.
4. Move historical runbooks to `docs/archive/` only after README and architecture links point to canonical docs.
5. Move compatibility tests into `tests/legacy/` after active route contracts are frozen.

## Immediate cleanup status

- Added a new clean dashboard at `/dashboard` without breaking legacy `/` cockpit behavior.
- Preserved the legacy cockpit static bundle because multiple safety regression tests assert its existing selectors and strings.
- Deferred physical deletion of phase/hotfix files until P0/P1 active runtime contracts are frozen.

## Next safe deletion candidates

| Area | Action | Blocker |
| --- | --- | --- |
| Root `README_APPLY_*` files | Move unreferenced files to `docs/archive/apply-notes/` | Confirm no install/apply workflow imports them |
| Phase-specific docs | Move to `docs/archive/phases/` | Canonical README/ARCHITECTURE links complete |
| Operator cockpit hotfix modules | Move to `src/tradebot/legacy/` or delete | Tests migrated to canonical cockpit package |
| `tests/test_*4B*.py` compatibility tests | Move to `tests/legacy/` | CI matrix updated |

## Dashboard direction

The clean dashboard should remain:

- dependency-free static HTML/CSS/JS;
- read-first by default;
- backed by existing `/api/cockpit/health` and `/api/cockpit/snapshot` contracts;
- visually separate from legacy phase-heavy cockpit UI;
- safe to iterate without mutating trading state.
