# 4B.4.3.6.6.61 Release Audit / Repository Hygiene / Pytest Collection Isolation

## Scope

This patch introduces release-audit hygiene for pytest collection isolation.

It configures canonical pytest discovery to collect tests from `tests/` and excludes accumulated patch artifacts:

- `tools/_patch_backup_*`
- `tools/_patch_payload_*`
- `legacy_patches`
- nested `_patch_backup*` directories
- nested `_patch_payload*` directories
- nested `legacy_patches` directories

It also enables `--import-mode=importlib` to reduce duplicate test module import mismatch failures caused by repeated patch-generated test module names.

## Legacy API drift report-only list

The patch reports the known drift symbols without changing trading behavior:

- `SQLITE_MIRROR_REQUIRED_DECISION`
- `build_production_hardening_snapshot`
- `OPERATOR_COCKPIT_V2_RISK_SIZING_AUDIT_PARITY`

## Non-goals

This patch does not delete files, move files, clean legacy patches, start runtime, call health endpoints, collect metrics, enable paper submit, submit network orders, approve live-real, access private APIs, or enable exchange-submit.

## Safety decision

`RELEASE_AUDIT_REPOSITORY_HYGIENE_PYTEST_COLLECTION_ISOLATION_READY_CANONICAL_TEST_DISCOVERY_CONFIGURED_NO_PAPER_SUBMIT_NO_NETWORK_ORDER_NO_LIVE_NO_EXCHANGE_SUBMIT_LOCKED`

## Final closure decision

`RELEASE_AUDIT_REPOSITORY_HYGIENE_CLOSURE_READY_PHASE61_CLOSED_PYTEST_COLLECTION_ISOLATED_LEGACY_DRIFT_REPORTED_NO_PAPER_SUBMIT_NO_NETWORK_ORDER_NO_LIVE_NO_EXCHANGE_SUBMIT_LOCKED`
