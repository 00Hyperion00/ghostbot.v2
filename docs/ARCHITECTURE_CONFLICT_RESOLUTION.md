# Architecture Doc Conflict Resolution Guide

Use this guide when applying production-readiness patches conflicts on `docs/ARCHITECTURE.md`.

## Why this file may conflict

`docs/ARCHITECTURE.md` is intended to be a canonical, human-maintained architecture/runbook entry point. Some downstream branches may already have their own architecture document, so patch application can conflict when a branch already contains that file.

## Safe merge policy

When `docs/ARCHITECTURE.md` conflicts, prefer this policy instead of dropping either side:

1. Keep the downstream branch's existing project-specific sections if they describe local deployment, operator workflow, evidence locations, or phase history.
2. Preserve the production-readiness sections from the incoming patch if they describe active runtime flow, Operator Cockpit safety boundaries, AI fallback behavior, persistence contracts, or high-value test slices.
3. If both sides contain run commands, keep the commands that match current code behavior:
   - model artifacts should use `.ubj`,
   - focused Python tests should run with `PYTHONPATH=src`,
   - compile validation should include `python -m compileall -q src/tradebot tests`.
4. Do not remove safety constraints during conflict resolution. In particular, keep fail-closed guidance for destructive routes, live-real enablement, exchange-submit paths, and operator confirmation.
5. If the conflict is large, keep the existing `docs/ARCHITECTURE.md` and move the incoming content into a new dated runbook, then link both from README.

## Minimal accepted post-merge shape

After resolving the conflict, the architecture entry point should still include these headings or equivalent content:

- Current production intent
- Canonical runtime flow
- Canonical control plane
- Safety boundaries
- AI decision path
- Persistence contract
- Refactoring rules for future work
- Current high-value test slices

## Validation after conflict resolution

Run the focused validation slice after resolving the document conflict:

```bash
PYTHONPATH=src pytest -q tests/test_strategy_ai_merge.py tests/test_api_logs_compat.py tests/test_api_ai_reload.py tests/test_model_retrain_reload_workflow.py
python -m compileall -q src/tradebot tests
```

This does not prove the documentation is perfect, but it confirms the active runtime/API behavior referenced by the runbook still compiles and passes the focused regression checks.
