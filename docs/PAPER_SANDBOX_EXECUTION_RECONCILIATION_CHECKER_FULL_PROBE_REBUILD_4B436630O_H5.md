# 4B.4.3.6.6.30O-H5 Reconciliation Checker Full Probe Rebuild

This hotfix rebuilds the checker layer only. It avoids stale probe signatures by inspecting the installed reconciliation function signature and using a deterministic synthetic 30N ledger event plus a fresh SQLite mirror path.

Runtime reconciliation behavior is not relaxed. Exchange submit and live-real remain blocked.
