# 4B.4.3.6.6.30I-H2 Internal Execution Harness Acceptance Pytest Compatibility Hotfix

This hotfix preserves the accepted 30I-H1 acceptance-chain repair and removes the in-process pytest fragility in the H1 regression test.

Fail-closed guarantees:

- It does not change runtime execution logic.
- It does not enable exchange submit.
- It does not enable paper sandbox dry-run execution.
- It does not enable paper candidate or live-real.
- It keeps the 30D runner compatibility repair intact.
- It verifies the H1 checker through the same CLI path used by the operator runbook.
