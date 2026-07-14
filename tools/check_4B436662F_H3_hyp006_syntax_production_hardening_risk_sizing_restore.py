from __future__ import annotations
import argparse
import json
import py_compile
from pathlib import Path

PATCH_ID = "4B436662F-H3"
PATCH_VERSION = "4B.4.3.6.6.62F-H3"
SAFETY_FALSE = {
    "paper_submit_enabled_by_patch": False,
    "paper_submit_performed": False,
    "paper_order_submit_performed": False,
    "network_request_performed": False,
    "network_order_submit_performed": False,
    "approved_for_live_real": False,
    "live_real_approved_by_patch": False,
    "approved_for_exchange_submit": False,
    "exchange_submit_performed": False,
    "runtime_start_performed": False,
    "training_performed": False,
    "reload_performed": False,
    "private_api_access_allowed": False,
    "trading_action_performed": False,
    "order_actions_performed": False,
}

def build_report() -> dict[str, object]:
    contracts: list[dict[str, object]] = []
    def add(name: str, ok: bool, detail: str = "") -> None:
        contracts.append({"name": name, "ok": bool(ok), "detail": detail})
    for rel in ["src/tradebot/hyp006_shadow_registration_operator_approval.py", "src/tradebot/_production_hardening_compat.py"]:
        try:
            py_compile.compile(rel, doraise=True)
            add(f"py_compile_{rel}", True)
        except Exception as exc:
            add(f"py_compile_{rel}", False, str(exc))
    try:
        from tradebot.production_hardening import acquire_runtime_lock, build_production_hardening_snapshot, release_runtime_lock
        snap = build_production_hardening_snapshot(project_root=Path.cwd())
        handle = acquire_runtime_lock(project_root=Path.cwd())
        release_runtime_lock(handle)
        add("production_hardening_legacy_keys", snap.get("project_root") == str(Path.cwd().resolve()) and snap.get("paper_order_submit_performed") is False and snap.get("production_hardening_signature_compatibility_v2") is True)
        add("runtime_lock_handle_mapping", handle.get("ok") is True and handle.get("released") is True)
    except Exception as exc:
        add("production_hardening_import", False, str(exc))
    try:
        from tradebot.operator_cockpit_v2_read_only import OPERATOR_COCKPIT_V2_RISK_SIZING_TELEMETRY_VERSION, _build_risk_sizing_in_memory_evidence_pack
        add("telemetry_version_dual_contract", OPERATOR_COCKPIT_V2_RISK_SIZING_TELEMETRY_VERSION == "4B.4.3.6.6.27G" and "61-H4" in OPERATOR_COCKPIT_V2_RISK_SIZING_TELEMETRY_VERSION)
        add("risk_sizing_pack_dict", isinstance(_build_risk_sizing_in_memory_evidence_pack(), dict) and isinstance(_build_risk_sizing_in_memory_evidence_pack(Path.cwd()), dict))
    except Exception as exc:
        add("operator_contracts", False, str(exc))
    ok = all(c["ok"] for c in contracts)
    return {"ok": ok, "status": "READY" if ok else "BLOCKED", "patch_id": PATCH_ID, "patch_version": PATCH_VERSION, "contract_count": len(contracts), "contract_ready_count": sum(1 for c in contracts if c["ok"]), "contracts": contracts, "decision": "HYP006_SYNTAX_PRODUCTION_HARDENING_RISK_SIZING_RESTORE_READY_NO_PAPER_SUBMIT_NO_NETWORK_ORDER_NO_LIVE_NO_EXCHANGE_SUBMIT_LOCKED" if ok else "HYP006_SYNTAX_PRODUCTION_HARDENING_RISK_SIZING_RESTORE_BLOCKED", **SAFETY_FALSE}

def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--once-json", action="store_true"); parser.parse_args()
    report = build_report()
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["ok"] else 1
if __name__ == "__main__":
    raise SystemExit(main())
