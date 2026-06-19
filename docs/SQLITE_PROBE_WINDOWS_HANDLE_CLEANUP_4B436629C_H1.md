# 4B.4.3.6.6.29C-H1 SQLite Probe Windows Handle Cleanup

This hotfix resolves a Windows-only cleanup failure in the 29C SQLite audit ledger checker.

## Root cause

`tools/check_4B436629C_sqlite_audit_ledger_upgrade.py` created a temporary `audit_probe.db` and instantiated `SQLiteStore`, but the SQLite connection remained open when `TemporaryDirectory` tried to delete the file. On Windows this can raise `PermissionError: [WinError 32]`.

## Changes

- Adds explicit `SQLiteStore.close()` and context manager support.
- Updates the 29C SQLite probe to close the store before reading and cleaning up the temp DB.
- Adds retry-safe temp directory cleanup for Windows file handle release timing.
- Adds tests for close/release behavior and checker source guard markers.

## Safety contract

- Read-only verification hotfix.
- No scheduler mutation.
- No strategy parameter mutation.
- No runtime overlay activation.
- No paper/live/live-real/order enablement.
- No training/reload action.

## Acceptance

Run the 29C-H1 checker, the original 29C checker, and both targeted test files before committing.
