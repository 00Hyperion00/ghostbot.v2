# Apply Conflict Resolution Guide

Use this guide when applying production-readiness patches conflicts on `README.md`, `docs/ARCHITECTURE.md`, `src/tradebot/strategy.py`, or `tests/test_strategy_ai_merge.py`.

## Why these files may conflict

These four files are high-churn integration points:

- `README.md` is edited by quick-start, architecture-link, model artifact, and validation-command changes.
- `docs/ARCHITECTURE.md` is the canonical human-maintained architecture/runbook entry point and may already exist downstream.
- `src/tradebot/strategy.py` contains the AI fallback normalization path; downstream branches often touch the same `normalize_signal_with_ai` block.
- `tests/test_strategy_ai_merge.py` carries regression tests for the same AI fallback behavior and therefore conflicts when strategy behavior is patched.

## Reported conflict set and required resolution

If a patch reports these files as conflicted, resolve them as follows.

### `README.md`

Keep all downstream project-specific quick-start notes, but ensure the merged README still contains:

- `.ubj` model examples for `tradebot ai-service` and `tradebot train-model`;
- links to `docs/ARCHITECTURE.md`, `docs/FINALIZATION_ROADMAP.md`, and this conflict guide;
- focused validation commands using `PYTHONPATH=src` and `python -m compileall -q src/tradebot tests`.

### `docs/ARCHITECTURE.md`

Prefer this policy instead of dropping either side:

1. Keep the downstream branch's existing project-specific sections if they describe local deployment, operator workflow, evidence locations, or phase history.
2. Preserve the production-readiness sections from the incoming patch if they describe active runtime flow, Operator Cockpit safety boundaries, AI fallback behavior, persistence contracts, or high-value test slices.
3. If both sides contain run commands, keep commands that match current code behavior:
   - model artifacts should use `.ubj`,
   - focused Python tests should run with `PYTHONPATH=src`,
   - compile validation should include `python -m compileall -q src/tradebot tests`.
4. Do not remove safety constraints during conflict resolution. In particular, keep fail-closed guidance for destructive routes, live-real enablement, exchange-submit paths, and operator confirmation.
5. If the conflict is large, keep the existing `docs/ARCHITECTURE.md` and move the incoming content into a new dated runbook, then link both from README.

The architecture entry point should still include these headings or equivalent content:

- Current production intent
- Canonical runtime flow
- Canonical control plane
- Safety boundaries
- AI decision path
- Persistence contract
- Refactoring rules for future work
- Current high-value test slices

### `src/tradebot/strategy.py`

The merged strategy file must preserve the production AI fallback behavior:

- `_StrategyEventLogger` protocol with `warn(..., dedupe_ms=...)` support;
- `_warn_ai_provider_failure(...)` that logs `AI_PROVIDER_PREDICT_FAILED` and never lets logger failure break fallback;
- `_build_ai_provider_failure_metrics(...)` with `aiProviderError`, `aiProviderErrorType`, and `aiFallbackMode` markers;
- `normalize_signal_with_ai(..., event_logger=None)` parameter;
- provider `predict` exceptions falling back to deterministic heuristic normalization instead of raising.

Do not wrap imports in try/except while resolving this file.

### `tests/test_strategy_ai_merge.py`

The merged tests must preserve coverage for:

- AI HOLD decisions preserving AI metrics;
- AI BUY decisions preserving merged technical/AI metrics;
- provider failure logging `AI_PROVIDER_PREDICT_FAILED` with `dedupe_ms == 60_000`;
- logger sink failure not breaking fallback;
- runtime metrics containing `aiProviderError`, `aiProviderErrorType`, and `aiFallbackMode`.

## Machine-checkable status

After manual conflict resolution, run the checker to confirm all reported files are present, have no conflict markers, and still contain the required production-readiness tokens:

```bash
PYTHONPATH=src python tools/check_apply_conflict_resolution.py --once-json
```

## Validation after conflict resolution

Run this focused validation slice after resolving the conflict set:

```bash
PYTHONPATH=src pytest -q tests/test_strategy_ai_merge.py tests/test_api_logs_compat.py tests/test_api_ai_reload.py tests/test_model_retrain_reload_workflow.py
python -m compileall -q src/tradebot tests
```

These checks do not prove the documentation is perfect, but they confirm the active runtime/API behavior referenced by the runbook still compiles and passes the focused regression checks.
