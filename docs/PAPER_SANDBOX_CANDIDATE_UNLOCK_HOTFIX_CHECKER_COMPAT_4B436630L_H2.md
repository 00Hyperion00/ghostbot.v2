# 4B.4.3.6.6.30L-H2 Candidate Unlock Hotfix Checker Compatibility

Purpose: repair the 30L-H1 meta-checker key mapping after the target 30L checker used canonical check names:

- `explicit_paper_candidate_unlock_gate_present`
- `sandbox_only_order_enablement_preflight_gate_present`

Scope:

- Updates only the H1 acceptance checker compatibility layer.
- Preserves 30L target checker acceptance.
- Preserves candidate-only unlock proof.
- Does not enable paper sandbox dry-run execution.
- Does not submit to exchange.
- Does not enable live-real.
