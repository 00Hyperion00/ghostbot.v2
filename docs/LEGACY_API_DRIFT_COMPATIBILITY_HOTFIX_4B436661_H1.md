# 4B.4.3.6.6.61-H1 Legacy API Drift Compatibility Hotfix

This hotfix restores three legacy public API contracts that are still referenced by canonical tests.

It is intentionally conservative:

- no test is skipped;
- no legacy test is deleted;
- no runtime is started;
- no paper submit is enabled;
- no network/private/live/exchange action is performed.

## Restored contracts

1. `SQLITE_MIRROR_REQUIRED_DECISION`
2. `build_production_hardening_snapshot`
3. `OPERATOR_COCKPIT_V2_RISK_SIZING_AUDIT_PARITY`

## Safety doctrine

The compatibility snapshot is report-only. It must never be interpreted as paper-submit, live-real, or exchange-submit approval.
