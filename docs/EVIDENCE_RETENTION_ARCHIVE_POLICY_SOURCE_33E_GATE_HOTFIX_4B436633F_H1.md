# 4B.4.3.6.6.33F-H1 — Source 33E Completion Gate Hotfix

Fixes 33F source gate parsing for 33E full run reports.

33F originally accepted top-level check-summary fields. 33E run reports can store equivalent values in nested sections: `source_gate`, `status_conflict_summary`, `unknown_evidence_summary`, and `malformed_json_summary`.

This hotfix accepts both formats and remains fail-closed when the source is missing, malformed, not READY, or has unresolved conflicts.

No evidence files are modified. No cleanup, archive execution, submit, training, reload, runtime overlay, paper, live, or live-real approval is performed.
