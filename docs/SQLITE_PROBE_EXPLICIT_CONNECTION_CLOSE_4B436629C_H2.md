# 4B.4.3.6.6.29C-H2 SQLite Probe Explicit Connection Close Hotfix

Purpose: close the remaining Windows SQLite probe leak caused by `sqlite3.Connection` context manager usage. Python's sqlite3 connection context manager commits or rolls back but does not close the connection, which can keep `.db` files locked on Windows.

This hotfix:

- replaces the 29C-H1 release probe with `tempfile.mkdtemp` plus explicit cleanup,
- uses explicit `conn.close()` for verification reads,
- deletes SQLite `.db`, `-wal`, and `-shm` artifacts with retry,
- updates the H1 regression test to avoid leaking sqlite3 handles,
- keeps live-real, paper/live, runtime overlay, training/reload, and order actions blocked.

Decision remains fail-closed:

- `approved_for_live_real=False`
- `approved_for_paper_candidate=False`
- `approved_for_runtime_overlay_activation_candidate=False`
- `trading_action_performed=False`
