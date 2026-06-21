# 4B.4.3.6.6.30O-H4 Reconciliation SQLite Mirror Finalize

Purpose: finalize 30O acceptance by replacing the reconciliation checker probe with a deterministic synthetic ledger + SQLite mirror probe and by using a fresh SQLite mirror path in the run tool.

Scope:
- Updates checker/probe compatibility only.
- Updates run tool to avoid stale/corrupt SQLite mirror files by default.
- Keeps mismatch zero proof required.
- Keeps exchange submit blocked.
- Keeps live-real blocked.
