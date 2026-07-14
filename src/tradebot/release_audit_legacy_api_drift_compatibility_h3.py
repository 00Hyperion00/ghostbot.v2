
from __future__ import annotations

import argparse
import importlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PATCH_ID = '4B436661_H3'
PATCH_VERSION = '4B.4.3.6.6.61-H3'
PATCH_NAME = 'Production Hardening Export Path / Cockpit Runtime Telemetry Compatibility Hotfix'
SAFETY_FALSE_FLAGS: dict[str, bool] = {'actual_evidence_accepted_by_patch': False, 'actual_evidence_ingested_by_patch': False, 'approved_for_exchange_submit': False, 'approved_for_live_real': False, 'destructive_cleanup_performed': False, 'dry_run_execution_performed_by_patch': False, 'duplicate_test_module_mismatch_cleanup_performed_by_patch': False, 'evidence_collection_performed_by_patch': False, 'exchange_submit_allowed': False, 'exchange_submit_enabled_by_patch': False, 'exchange_submit_performed': False, 'file_delete_performed': False, 'file_move_performed': False, 'git_add_performed': False, 'git_commit_performed': False, 'git_push_performed': False, 'git_tag_performed': False, 'legacy_tests_skipped_by_patch': False, 'live_real_approved_by_patch': False, 'live_real_submit_allowed': False, 'network_order_submit_allowed': False, 'network_order_submit_performed': False, 'network_request_performed': False, 'network_submit_allowed': False, 'next_phase_unlock_allowed': False, 'next_phase_unlock_performed': False, 'order_path_opened_by_patch': False, 'paper_order_path_opened_by_patch': False, 'paper_order_submit_allowed': False, 'paper_order_submit_performed': False, 'paper_runtime_start_performed': False, 'paper_submit_allowed': False, 'paper_submit_enabled_by_patch': False, 'paper_submit_performed': False, 'paper_submit_performed_by_patch': False, 'paper_trading_evidence_collected_by_patch': False, 'paper_trading_soak_accepted_by_patch': False, 'paper_trading_soak_started_by_patch': False, 'private_api_access_allowed': False, 'private_api_access_performed': False, 'reload_performed': False, 'repository_cleanup_performed_by_patch': False, 'runtime_health_endpoint_called': False, 'runtime_health_probe_performed': False, 'runtime_metrics_collection_performed': False, 'runtime_overlay_activated': False, 'runtime_process_started': False, 'runtime_process_start_performed': False, 'runtime_start_command_executed': False, 'runtime_start_command_execution_performed': False, 'runtime_start_performed': False, 'runtime_started_by_patch': False, 'signed_request_performed': False, 'training_performed': False, 'transition_to_next_phase_performed': False}


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _safe_import(module_name: str) -> tuple[Any | None, str | None]:
    try:
        return importlib.import_module(module_name), None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def build_phase61_h3_report(project_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(project_root).resolve() if project_root is not None else Path.cwd().resolve()
    contracts: list[dict[str, Any]] = []

    production_module, production_error = _safe_import("tradebot.production_hardening")
    production_symbol = getattr(production_module, "build_production_hardening_snapshot", None) if production_module else None
    production_snapshot: dict[str, Any] | None = None
    production_snapshot_error: str | None = None
    if callable(production_symbol):
        try:
            production_snapshot = production_symbol(project_root=root)
        except Exception as exc:
            production_snapshot_error = f"{type(exc).__name__}: {exc}"
    contracts.append({
        "module": "tradebot.production_hardening",
        "module_imported": production_module is not None,
        "module_file": getattr(production_module, "__file__", None) if production_module else None,
        "module_path": [str(p) for p in getattr(production_module, "__path__", [])] if production_module else [],
        "error": production_error,
        "symbol": "build_production_hardening_snapshot",
        "symbol_present": production_symbol is not None,
        "symbol_type": type(production_symbol).__name__ if production_symbol is not None else None,
        "callable_project_root_ok": isinstance(production_snapshot, dict) and production_snapshot.get("ok") is True,
        "callable_project_root_error": production_snapshot_error,
        "restored_by_patch": production_symbol is not None and production_snapshot_error is None,
    })

    cockpit_module, cockpit_error = _safe_import("tradebot.operator_cockpit_v2_read_only")
    for symbol in (
        "OPERATOR_COCKPIT_V2_RISK_SIZING_AUDIT_PARITY",
        "OPERATOR_COCKPIT_V2_RISK_SIZING_EVIDENCE_EXPORT_FAIL_CLOSED",
        "OPERATOR_COCKPIT_V2_RISK_SIZING_RUNTIME_TELEMETRY",
    ):
        value = getattr(cockpit_module, symbol, None) if cockpit_module else None
        contracts.append({
            "module": "tradebot.operator_cockpit_v2_read_only",
            "module_imported": cockpit_module is not None,
            "error": cockpit_error,
            "symbol": symbol,
            "symbol_present": value is not None,
            "symbol_type": type(value).__name__ if value is not None else None,
            "restored_by_patch": isinstance(value, str),
        })

    ready_count = sum(1 for item in contracts if item.get("restored_by_patch") is True)
    violations = [key for key, value in SAFETY_FALSE_FLAGS.items() if value is not False]
    ready = ready_count == len(contracts) and not violations
    return {
        **SAFETY_FALSE_FLAGS,
        "ok": ready,
        "status": "READY" if ready else "BLOCKED",
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "patch_name": PATCH_NAME,
        "phase": "61-H3",
        "phase_61_h3_closed": ready,
        "decision": "PRODUCTION_HARDENING_EXPORT_PATH_COCKPIT_RUNTIME_TELEMETRY_COMPATIBILITY_HOTFIX_READY_IMPORT_PATH_AND_RUNTIME_TELEMETRY_EXPORT_RESTORED_NO_PAPER_SUBMIT_NO_NETWORK_ORDER_NO_LIVE_NO_EXCHANGE_SUBMIT_LOCKED" if ready else "PRODUCTION_HARDENING_EXPORT_PATH_COCKPIT_RUNTIME_TELEMETRY_COMPATIBILITY_HOTFIX_BLOCKED",
        "final_phase_decision": "PRODUCTION_HARDENING_EXPORT_PATH_COCKPIT_RUNTIME_TELEMETRY_COMPATIBILITY_HOTFIX_CLOSURE_READY_PHASE61_H3_CLOSED_FULL_REPO_PYTEST_REMAINING_IMPORT_DRIFT_TARGETED_NO_PAPER_SUBMIT_NO_NETWORK_ORDER_NO_LIVE_NO_EXCHANGE_SUBMIT_LOCKED" if ready else "PRODUCTION_HARDENING_EXPORT_PATH_COCKPIT_RUNTIME_TELEMETRY_COMPATIBILITY_HOTFIX_CLOSURE_BLOCKED",
        "generated_at_utc": _utc_stamp(),
        "project_root": str(root),
        "legacy_api_drift_fix_performed_by_patch": True,
        "legacy_api_drift_report_only": False,
        "legacy_public_api_contracts_restored": ready_count == len(contracts),
        "legacy_api_contract_count": len(contracts),
        "legacy_api_contract_ready_count": ready_count,
        "legacy_api_contracts": contracts,
        "legacy_api_callable_failures": [item for item in contracts if not item.get("restored_by_patch")],
        "production_hardening_import_path_resolved": contracts[0].get("restored_by_patch") is True,
        "production_hardening_module_file": contracts[0].get("module_file"),
        "production_hardening_module_path": contracts[0].get("module_path"),
        "production_hardening_snapshot_error": production_snapshot_error,
        "production_hardening_snapshot_keys": sorted(production_snapshot.keys()) if isinstance(production_snapshot, dict) else [],
        "operator_cockpit_runtime_telemetry_export_present": any(item.get("symbol") == "OPERATOR_COCKPIT_V2_RISK_SIZING_RUNTIME_TELEMETRY" and item.get("restored_by_patch") is True for item in contracts),
        "manual_operator_review_required_before_paper_submit": True,
        "manual_governance_required_for_any_live_action": True,
        "repository_cleanup_performed_by_patch": False,
        "final_safety_violation_count": len(violations),
        "final_safety_violations": violations,
        "next_phase": "4B.4.3.6.6.62A",
        "next_phase_name": "Patch Artifact Consolidation / Repository Cleanup Review",
        "next_phase_unlock_allowed": False,
        "next_phase_unlock_performed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=PATCH_NAME)
    parser.add_argument("--reports-dir", default=None)
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    report = build_phase61_h3_report(Path.cwd())
    if args.reports_dir:
        reports_dir = Path(args.reports_dir)
        reports_dir.mkdir(parents=True, exist_ok=True)
        path = reports_dir / f"4B436661_H3_production_hardening_export_path_cockpit_runtime_telemetry_{report['generated_at_utc'].lower()}_{report['status'].lower()}.json"
        report["report_path"] = str(path)
        path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    else:
        report["report_path"] = None
    print(json.dumps(report, sort_keys=True) if args.once_json else json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
