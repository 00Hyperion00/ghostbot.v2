# 4B.4.3.6.6.30O-H3 Reconciliation Checker Ledger Event Signature Hotfix

Purpose: repair the 30O checker module probe for reconciliation builders that require a `ledger_event` positional/keyword argument.

Scope:

- Updates only checker/probe compatibility.
- Keeps 30O runtime reconciliation logic unchanged.
- Preserves mismatch-zero proof and SQLite audit mirror validation.
- Preserves no-exchange-submit and no-live-real gates.
