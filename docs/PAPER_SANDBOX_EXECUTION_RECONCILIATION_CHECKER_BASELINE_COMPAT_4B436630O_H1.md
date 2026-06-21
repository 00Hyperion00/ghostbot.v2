# 4B.4.3.6.6.30O-H1 Reconciliation Checker Baseline Compatibility

Purpose: repair the 30O acceptance checker when the nested 30N checker reports a stale baseline cascade failure even though 30N local invariants and direct 30L-H2 checker are both clean.

Scope:
- Updates only `tools/check_4B436630O_paper_sandbox_execution_reconciliation_gate.py`.
- Keeps the 30O runtime module unchanged.
- Requires direct 30L-H2 checker to pass.
- Requires 30N local file/compile/module/no-submit/no-live-real invariants to pass.
- Preserves mismatch-zero proof and SQLite audit mirror checks.
- Does not submit to exchange.
- Does not enable live-real.
