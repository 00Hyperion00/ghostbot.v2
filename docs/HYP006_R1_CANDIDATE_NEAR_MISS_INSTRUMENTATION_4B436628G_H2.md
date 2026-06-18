# 4B.4.3.6.6.28G-H2 HYP-006 Candidate / Near-Miss Scan Instrumentation

Purpose: create a read-only diagnostic artifact that summarizes HYP-006 candidate, near-miss, trigger, and gate-block evidence before any parameter relaxation or research branch decision.

Scope:

- Reads `reports/hyp006_r1_canonical` artifacts.
- Summarizes recent HYP-006 ledgers.
- Searches candidate, near-miss, trigger, rejection, and gate JSON artifacts if present.
- Falls back to latest 28G / 28G-H1 blockers when raw candidate scan artifacts are absent.
- Writes JSON and Markdown diagnostics only.

Strict exclusions:

- No config mutation.
- No scheduler mutation.
- No strategy parameter mutation.
- No training.
- No model reload.
- No paper/live/order enablement.
- No network request.

Decision policy:

- `approved_for_candidate_near_miss_diagnostics` may be true.
- `approved_for_parameter_relaxation_candidate` remains false.
- `approved_for_paper_candidate` remains false.
- `approved_for_live_real` remains false.

If raw candidate scan artifacts are missing, this patch does not infer parameter changes. It only records that integrated raw scan hooks are required through a later read-only research gate.
