# 4B.4.3.6.6.61-H3 — Production Hardening Export Path / Cockpit Runtime Telemetry Compatibility Hotfix

This hotfix targets the remaining full-repo pytest collection failures after 61-H2:

1. `tradebot.production_hardening` import path ambiguity still hides `build_production_hardening_snapshot` for legacy tests.
2. `OPERATOR_COCKPIT_V2_RISK_SIZING_RUNTIME_TELEMETRY` is missing from `tradebot.operator_cockpit_v2_read_only`.

The patch restores backward-compatible public API exports only. It is review-only and fail-closed.

Safety locks remain false:

- `paper_submit_enabled_by_patch=False`
- `paper_submit_performed=False`
- `network_order_submit_performed=False`
- `approved_for_live_real=False`
- `exchange_submit_performed=False`
- `private_api_access_allowed=False`
- `runtime_start_performed=False`
