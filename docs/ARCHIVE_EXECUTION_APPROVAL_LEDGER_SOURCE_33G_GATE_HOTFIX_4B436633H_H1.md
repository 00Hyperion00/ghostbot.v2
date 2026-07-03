# 4B.4.3.6.6.33H-H1 — Source 33G Completion Gate Hotfix

This hotfix updates the 33H source gate to accept both 33G stdout summary schema and persisted full run-report schema.

## Scope

- Resolve `source_33g_complete=false` caused by nested 33G report fields.
- Read `manifest_sha256` from `manifest_hash_verification.manifest_sha256`.
- Read dry-run move counts from `dry_run_archive_move_preview`.
- Read rollback counts from `rollback_plan`.
- Preserve final no-execution gate and all fail-closed safety constraints.

## Non-actions

This patch does not move files, delete files, execute archive operations, submit orders, train, reload, enable overlays, or approve paper/live/live-real mode.
