4B.4.3.6.6.37A — Post-Phase-36 Production Readiness Re-Baseline

This patch is a planning-only production readiness re-baseline after Phase 36 final closure.
It validates 36G READY final seal, then emits:
- Closed Phase Carryforward
- P0 Hardening Gap Matrix
- No-Submit 37A Planning Gate

It does not close P0 gaps, mutate production code, enable paper/live, perform network requests, submit orders, activate runtime overlays, train/reload, or unlock the next phase.
