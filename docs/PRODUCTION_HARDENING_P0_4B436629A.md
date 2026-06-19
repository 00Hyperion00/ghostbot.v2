# 4B.4.3.6.6.29A Production Hardening P0

Decision: HYP-006 remains a no-order research and OOS monitoring track. Production readiness is not inferred from HYP-006 performance.

This patch establishes the P0 production-hardening baseline without enabling runtime overlay activation, parameter relaxation, paper/live, live-real, training/reload, or order actions.

## Scope

- Install contract: `requirements.txt` is aligned with `pyproject.toml` dependencies.
- Repo hygiene: transient patch/report policy is documented and ignore rules are extended.
- Strict config: unknown YAML keys fail closed by default.
- API auth baseline: optional token guard and typed destructive-action confirmation middleware.
- SQLite audit baseline: WAL, busy timeout, schema metadata, operator-action table, integrity check and backup hook.
- Runtime lock: utility to prevent duplicate active process ownership.
- Fee/slippage baseline: zero-cost training labels are removed from defaults.
- Promotion gate isolation: hypothesis performance cannot automatically promote runtime/paper/live/order paths.

## Non-goals

- Does not touch HYP-006 thresholds.
- Does not change BNBUSDT overlay decision logic.
- Does not activate runtime overlay.
- Does not enable paper/live/live-real.
- Does not submit or prepare orders.
