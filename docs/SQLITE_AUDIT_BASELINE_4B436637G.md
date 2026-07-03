# 4B.4.3.6.6.37G SQLite Audit Baseline

This patch closes **P0_SQLITE_AUDIT_BASELINE** as a no-submit production hardening evidence gate.

## Baseline requirements

- File-backed runtime SQLite connections require WAL mode.
- Runtime SQLite connections require a non-zero busy timeout baseline.
- Schema/user version must be auditable before promotion gates advance.
- Integrity check must be declared as a required promotion gate.
- Backup hook must be declared before destructive persistence changes are allowed.

## Explicit exclusions

37G does not open, migrate, write, back up, or repair production databases. It does not bind the baseline to runtime DB loaders. It does not enable paper, live, exchange submit, network submit, runtime overlay, training, reload, report cleanup, backup cleanup, archive, move, delete, or deduplication.

## Expected output

`SQLITE_AUDIT_BASELINE_READY_NO_SUBMIT_PRODUCTION_HARDENING_P0_6_LOCKED`
