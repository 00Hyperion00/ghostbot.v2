4B.4.3.6.6.37G SQLite Audit Baseline

Purpose:
- Validate 37F READY as the source gate.
- Declare and prove the SQLite audit baseline for WAL, busy_timeout, schema_version, integrity_check, and backup hook.
- Close P0_SQLITE_AUDIT_BASELINE only.
- Keep Phase 37 planning-only, no-submit, no paper/live, no runtime DB mutation.

Apply:
  python tools/apply_4B436637G_sqlite_audit_baseline.py

Check:
  $env:PYTHONPATH="src"
  python tools/check_4B436637G_sqlite_audit_baseline.py --once-json

Test:
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  $env:PYTHONPATH="src"
  python -m pytest -q tests/test_sqlite_audit_baseline_4B436637G.py

Run/write reports:
  $env:PYTHONPATH="src"
  python tools/run_4B436637G_sqlite_audit_baseline.py --reports-dir .\reports\recovery --once-json

Expected decision:
  SQLITE_AUDIT_BASELINE_READY_NO_SUBMIT_PRODUCTION_HARDENING_P0_6_LOCKED

Safety:
- Does not open or mutate production SQLite DB files.
- Does not run schema migration.
- Does not perform backup.
- Does not enable paper/live/submit/runtime overlay/training/reload.
- Does not delete/move/deduplicate reports or backups.
