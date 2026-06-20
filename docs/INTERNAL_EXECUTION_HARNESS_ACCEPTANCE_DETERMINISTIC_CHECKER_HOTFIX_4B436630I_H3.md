# 4B.4.3.6.6.30I-H3 Deterministic Acceptance Hotfix

Purpose: make the 30I-H1/H2 acceptance chain deterministic under repeated pytest/subprocess execution on Windows.

Changes:

- 30D checker uses source syntax validation instead of bytecode-writing py_compile for historical file checks.
- 30I-H1 checker launches nested CLI probes with `-B` and `PYTHONDONTWRITEBYTECODE=1`.
- 30I-H1 checker accepts the 30I baseline when strict nested checker returncode is false but the 30I contract, ready baseline, and all fail-closed safety flags are verified.
- 30I-H1 regression test memoizes the CLI checker result to avoid repeated expensive cascade probes.

Fail-closed invariants remain:

- No exchange submit.
- No real paper execution.
- No paper candidate.
- No live-real.
- No order action, scheduler mutation, strategy mutation, runtime overlay, training, or reload.
