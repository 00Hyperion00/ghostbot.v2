# 4B.4.3.6.6.34A-H1 — Source 33I Completion Gate Hotfix

34A-H1 fixes the 34A source gate parser for persisted 33I full-report evidence.

## Fix

- Reads `final_phase_acceptance_matrix.accepted_for_closure`.
- Reads `final_phase_acceptance_matrix.missing_required_phase_tokens`.
- Reads `final_phase_acceptance_matrix.rejected_required_phase_tokens`.
- Reads `source_33h_gate.complete`.
- Reads `source_33h_gate.manifest_sha256`.
- Reads `source_33h_gate.immutable_plan_digest`.
- Reads nested `safety_snapshot.*` fail-closed flags.

## Safety

Planning-only hotfix. No submit, no runtime overlay, no training/reload, no archive execution, no file move/delete.
