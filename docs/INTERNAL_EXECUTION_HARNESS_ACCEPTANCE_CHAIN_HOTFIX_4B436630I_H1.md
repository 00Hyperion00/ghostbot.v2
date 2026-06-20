# 4B.4.3.6.6.30I-H1 Internal Execution Harness Acceptance Chain Hotfix

This hotfix repairs the acceptance-chain failure observed after 30I. The functional 30I internal harness passed, but the standalone 30I checker failed because the base-checker cascade reported a 30D runner `py_compile` failure.

Scope:

- Replace `tools/run_4B436630D_operator_approval_evidence_capture.py` with a clean Windows/UTF-8-safe runner.
- Verify the 30D checker returns `ok=true` again.
- Verify the 30H checker returns `ok=true` again.
- Verify the 30I checker returns `ok=true` and preserves the accepted internal simulated fill ledger baseline.

Fail-closed guarantees:

- No exchange submit is enabled.
- No paper sandbox execution is enabled.
- No paper transition candidate is enabled.
- No paper candidate is enabled.
- No live-real is enabled.
- No runtime overlay, training, reload, scheduler mutation, or strategy parameter mutation is performed.
