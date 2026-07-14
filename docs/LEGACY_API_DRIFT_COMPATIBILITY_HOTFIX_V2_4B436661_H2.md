# 4B.4.3.6.6.61-H2 Legacy API Drift Compatibility Hotfix V2

This patch is a targeted follow-up to 61-H1.

It restores compatibility for canonical legacy tests without skipping tests, deleting files, starting runtime, submitting orders, calling private APIs, enabling paper submit, approving live-real, or enabling exchange submit.

## Restored / hardened public API contracts

- `tradebot.production_hardening.build_production_hardening_snapshot(project_root=...)`
- `tradebot.production_hardening` module/package import path compatibility
- `tradebot.operator_cockpit_v2_read_only.OPERATOR_COCKPIT_V2_RISK_SIZING_AUDIT_PARITY`
- `tradebot.operator_cockpit_v2_read_only.OPERATOR_COCKPIT_V2_RISK_SIZING_EVIDENCE_EXPORT_FAIL_CLOSED`
- `tradebot.paper_sandbox_execution_reconciliation_gate.SQLITE_MIRROR_REQUIRED_DECISION`

## Safety doctrine

This is a compatibility patch only. Any returned snapshot is report-only and fail-closed by default.
