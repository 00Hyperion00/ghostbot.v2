from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
from typing import Any

FALSE_FLAGS = {
    "paper_submit_enabled_by_patch": False,
    "paper_submit_performed": False,
    "paper_order_submit_performed": False,
    "network_request_performed": False,
    "network_order_submit_performed": False,
    "approved_for_live_real": False,
    "approved_for_exchange_submit": False,
    "exchange_submit_performed": False,
    "runtime_start_performed": False,
    "training_performed": False,
    "reload_performed": False,
}

def build_report(project_root: Path | None = None) -> dict[str, Any]:
    root = Path(project_root or Path.cwd()).resolve()
    contracts: list[dict[str, Any]] = []
    def probe(module: str, symbol: str, *, callable_required: bool = False, contains: str | None = None) -> None:
        row = {"module": module, "symbol": symbol, "ok": False, "detail": ""}
        try:
            mod = importlib.import_module(module)
            value = getattr(mod, symbol)
            ok = True
            if callable_required:
                ok = ok and callable(value)
            if contains is not None:
                ok = ok and contains in value
            row.update(ok=ok, detail=type(value).__name__)
        except Exception as exc:
            row.update(ok=False, detail=repr(exc))
        contracts.append(row)
    probe("tradebot.operator_cockpit_v2_read_only", "OPERATOR_COCKPIT_V2_RISK_SIZING_AUDIT_PARITY", contains="RISK_SIZING_AUDIT_PARITY")
    probe("tradebot.operator_cockpit_v2_read_only", "OPERATOR_COCKPIT_V2_RISK_SIZING_RUNTIME_TELEMETRY", contains="RUNTIME_TELEMETRY")
    probe("tradebot.operator_cockpit_v2_read_only", "OPERATOR_COCKPIT_V2_RISK_SIZING_TELEMETRY_VERSION", contains="61-H4")
    probe("tradebot.operator_cockpit_v2_read_only", "_build_risk_sizing_in_memory_evidence_pack", callable_required=True)
    probe("tradebot.production_hardening", "RuntimeLockHandle", callable_required=True)
    probe("tradebot.production_hardening", "build_production_hardening_snapshot", callable_required=True)
    probe("tradebot.hyp005_shadow_evidence_path_contract", "write_json_ascii_atomic", callable_required=True)
    probe("tradebot.hyp005_shadow_evidence_path_contract", "resolve_existing_evidence_path", callable_required=True)
    ready = all(row["ok"] for row in contracts)
    snapshot_ok = False
    try:
        from tradebot.production_hardening import build_production_hardening_snapshot
        snap = build_production_hardening_snapshot(project_root=root)
        snapshot_ok = bool(snap.get("ok") is True and snap.get("private_api_access_allowed") is False and snap.get("production_hardening_import_finalization_h5") is True and snap.get("runtime_lock_handle_export_compatibility_h7") is True)
    except Exception:
        snapshot_ok = False
    try:
        from tradebot.operator_cockpit_v2_read_only import _build_risk_sizing_in_memory_evidence_pack
        risk_pack_ok = isinstance(_build_risk_sizing_in_memory_evidence_pack(), dict)
    except Exception:
        risk_pack_ok = False
    ok = ready and snapshot_ok and risk_pack_ok
    return {
        "ok": ok,
        "status": "READY" if ok else "BLOCKED",
        "patch_id": "4B436662C",
        "patch_version": "4B.4.3.6.6.62C",
        "decision": "PHASE61_REGRESSION_RESTORE_SHADOW_EVIDENCE_COLLECTION_FIX_READY_NO_PAPER_SUBMIT_NO_NETWORK_ORDER_NO_LIVE_NO_EXCHANGE_SUBMIT_LOCKED" if ok else "PHASE61_REGRESSION_RESTORE_SHADOW_EVIDENCE_COLLECTION_FIX_BLOCKED",
        "contract_count": len(contracts),
        "contract_ready_count": sum(1 for row in contracts if row["ok"]),
        "contracts": contracts,
        "production_hardening_snapshot_ok": snapshot_ok,
        "risk_sizing_evidence_pack_dict_ok": risk_pack_ok,
        "final_safety_violation_count": 0 if all(v is False for v in FALSE_FLAGS.values()) else 1,
        "final_safety_violations": [],
        "next_phase": "4B.4.3.6.6.62D",
        "next_phase_name": "Full Repo Regression Stabilization Remaining Functional Sweep",
        **FALSE_FLAGS,
    }

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    payload = build_report()
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0 if payload["ok"] else 2

if __name__ == "__main__":
    raise SystemExit(main())
