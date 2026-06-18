# 4B.4.3.6.6.28G-H3 HYP-006 Runtime Candidate Scan Hook

Read-only HYP-006 runtime scan instrumentation for gate-level candidate, near-miss, and trigger diagnostics.

## Scope

- Adds gate-level diagnostics inside `scan_hyp006_short_probe_observations_with_diagnostics`.
- Emits `candidate_scan_diagnostics` into 28C/28D reports.
- Emits a runtime artifact named `4B436628G_H3_hyp006_r1_runtime_candidate_scan_gate_level_near_miss_*.json` during canonical 28D cycle writes.
- Preserves no-order behavior.

## Safety

- No parameter relaxation.
- No config mutation.
- No scheduler mutation.
- No training or reload.
- No paper/live enablement.
- No order action.
