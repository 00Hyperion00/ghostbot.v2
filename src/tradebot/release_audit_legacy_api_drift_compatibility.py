from __future__ import annotations

import hashlib
import importlib
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PATCH_ID = "4B436661_H1"
PATCH_VERSION = "4B.4.3.6.6.61-H1"
PATCH_NAME = "Legacy API Drift Compatibility Hotfix"

DECISION = (
    "LEGACY_API_DRIFT_COMPATIBILITY_HOTFIX_READY_PUBLIC_API_CONTRACTS_RESTORED_"
    "NO_PAPER_SUBMIT_NO_NETWORK_ORDER_NO_LIVE_NO_EXCHANGE_SUBMIT_LOCKED"
)

FINAL_PHASE_DECISION = (
    "LEGACY_API_DRIFT_COMPATIBILITY_HOTFIX_CLOSURE_READY_PHASE61_H1_CLOSED_"
    "FULL_REPO_PYTEST_LEGACY_IMPORT_DRIFT_TARGETED_NO_PAPER_SUBMIT_NO_NETWORK_ORDER_"
    "NO_LIVE_NO_EXCHANGE_SUBMIT_LOCKED"
)

NEXT_PHASE = "4B.4.3.6.6.62A"
NEXT_PHASE_NAME = "Patch Artifact Consolidation / Repository Cleanup Review"

SAFETY_LOCKS: dict[str, bool] = {
    "actual_evidence_accepted_by_patch": False,
    "actual_evidence_ingested_by_patch": False,
    "approved_for_exchange_submit": False,
    "approved_for_live_real": False,
    "destructive_cleanup_performed": False,
    "dry_run_execution_performed_by_patch": False,
    "evidence_collection_performed_by_patch": False,
    "exchange_submit_allowed": False,
    "exchange_submit_enabled_by_patch": False,
    "exchange_submit_performed": False,
    "file_delete_performed": False,
    "file_move_performed": False,
    "legacy_tests_skipped_by_patch": False,
    "live_real_approved_by_patch": False,
    "live_real_submit_allowed": False,
    "network_order_submit_allowed": False,
    "network_order_submit_performed": False,
    "network_request_performed": False,
    "network_submit_allowed": False,
    "order_path_opened_by_patch": False,
    "paper_order_path_opened_by_patch": False,
    "paper_order_submit_allowed": False,
    "paper_order_submit_performed": False,
    "paper_runtime_start_performed": False,
    "paper_submit_allowed": False,
    "paper_submit_enabled_by_patch": False,
    "paper_submit_performed": False,
    "paper_submit_performed_by_patch": False,
    "paper_trading_evidence_collected_by_patch": False,
    "paper_trading_soak_accepted_by_patch": False,
    "paper_trading_soak_started_by_patch": False,
    "private_api_access_allowed": False,
    "private_api_access_performed": False,
    "reload_performed": False,
    "runtime_health_endpoint_called": False,
    "runtime_health_probe_performed": False,
    "runtime_metrics_collection_performed": False,
    "runtime_overlay_activated": False,
    "runtime_process_started": False,
    "runtime_start_command_executed": False,
    "runtime_start_command_execution_performed": False,
    "runtime_start_performed": False,
    "runtime_started_by_patch": False,
    "signed_request_performed": False,
    "training_performed": False,
    "transition_to_next_phase_performed": False,
}

@dataclass(frozen=True)
class LegacyApiContract:
    module: str
    symbol: str
    target_path_hint: str
    restored_by_patch: bool = True

REQUIRED_CONTRACTS: tuple[LegacyApiContract, ...] = (
    LegacyApiContract(
        module="tradebot.paper_sandbox_execution_reconciliation_gate",
        symbol="SQLITE_MIRROR_REQUIRED_DECISION",
        target_path_hint="src/tradebot/paper_sandbox_execution_reconciliation_gate.py",
    ),
    LegacyApiContract(
        module="tradebot.production_hardening",
        symbol="build_production_hardening_snapshot",
        target_path_hint="src/tradebot/production_hardening.py or src/tradebot/production_hardening/__init__.py",
    ),
    LegacyApiContract(
        module="tradebot.operator_cockpit_v2_read_only",
        symbol="OPERATOR_COCKPIT_V2_RISK_SIZING_AUDIT_PARITY",
        target_path_hint="src/tradebot/operator_cockpit_v2_read_only.py",
    ),
)

def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

def _digest_json(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()

def _ensure_src_on_path(project_root: Path) -> None:
    src = str((project_root / "src").resolve())
    if src not in sys.path:
        sys.path.insert(0, src)

def verify_legacy_api_contracts(project_root: str | Path | None = None) -> list[dict[str, Any]]:
    root = Path(project_root) if project_root is not None else Path.cwd()
    root = root.resolve()
    _ensure_src_on_path(root)
    findings: list[dict[str, Any]] = []
    for contract in REQUIRED_CONTRACTS:
        module_imported = False
        symbol_present = False
        symbol_type: str | None = None
        error: str | None = None
        try:
            module = importlib.import_module(contract.module)
            module_imported = True
            symbol_present = hasattr(module, contract.symbol)
            if symbol_present:
                symbol_type = type(getattr(module, contract.symbol)).__name__
        except Exception as exc:  # pragma: no cover - intentionally diagnostic
            error = f"{type(exc).__name__}: {exc}"
        findings.append(
            {
                **asdict(contract),
                "module_imported": module_imported,
                "symbol_present": symbol_present,
                "symbol_type": symbol_type,
                "error": error,
            }
        )
    return findings

def build_legacy_api_drift_compatibility_snapshot(project_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(project_root) if project_root is not None else Path.cwd()
    root = root.resolve()
    contracts = verify_legacy_api_contracts(root)
    missing = [item for item in contracts if not item["module_imported"] or not item["symbol_present"]]
    safety_violations = [key for key, value in SAFETY_LOCKS.items() if value]
    ok = not missing and not safety_violations
    payload: dict[str, Any] = {
        "ok": ok,
        "status": "READY" if ok else "BLOCKED",
        "patch_id": PATCH_ID,
        "patch_name": PATCH_NAME,
        "patch_version": PATCH_VERSION,
        "phase": "61-H1",
        "phase_61_h1_closed": ok,
        "decision": DECISION if ok else "LEGACY_API_DRIFT_COMPATIBILITY_HOTFIX_BLOCKED_PUBLIC_API_CONTRACTS_MISSING",
        "final_phase_decision": FINAL_PHASE_DECISION if ok else "LEGACY_API_DRIFT_COMPATIBILITY_HOTFIX_BLOCKED",
        "generated_at_utc": utc_stamp(),
        "project_root": str(root),
        "legacy_api_contracts": contracts,
        "legacy_api_contract_count": len(contracts),
        "legacy_api_contract_ready_count": len(contracts) - len(missing),
        "missing_legacy_api_contracts": missing,
        "legacy_api_drift_fix_performed_by_patch": True,
        "legacy_api_drift_report_only": False,
        "legacy_public_api_contracts_restored": ok,
        "legacy_tests_skipped_by_patch": False,
        "repository_cleanup_performed_by_patch": False,
        "duplicate_test_module_mismatch_cleanup_performed_by_patch": False,
        "manual_operator_review_required_before_paper_submit": True,
        "manual_governance_required_for_any_live_action": True,
        "next_phase": NEXT_PHASE,
        "next_phase_name": NEXT_PHASE_NAME,
        "next_phase_unlock_allowed": False,
        "next_phase_unlock_performed": False,
        "final_safety_violations": safety_violations,
        "final_safety_violation_count": len(safety_violations),
        **SAFETY_LOCKS,
    }
    payload["report_digest"] = _digest_json({k: v for k, v in payload.items() if k not in {"generated_at_utc", "report_digest"}})
    return payload

def write_report(snapshot: dict[str, Any], reports_dir: str | Path) -> Path:
    directory = Path(reports_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"4B436661_H1_legacy_api_drift_compatibility_hotfix_{utc_stamp()}_{snapshot['status'].lower()}.json"
    payload = dict(snapshot)
    payload["report_path"] = str(path)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path
