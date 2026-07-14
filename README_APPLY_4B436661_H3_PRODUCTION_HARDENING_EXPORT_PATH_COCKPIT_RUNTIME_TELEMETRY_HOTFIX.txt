4B.4.3.6.6.61-H3 Production Hardening Export Path / Cockpit Runtime Telemetry Compatibility Hotfix

Purpose:
- Fix tradebot.production_hardening module/package ambiguity.
- Ensure build_production_hardening_snapshot is exported from the import path selected by Python.
- Preserve build_production_hardening_snapshot(project_root=...) compatibility.
- Restore OPERATOR_COCKPIT_V2_RISK_SIZING_RUNTIME_TELEMETRY read-only legacy export.
- Preserve no-paper-submit, no-network-order, no-live, no-exchange-submit locks.

This patch does not run the bot, start runtime, train, reload, access private API, submit paper orders, submit live orders, move/delete files, or perform git operations.
