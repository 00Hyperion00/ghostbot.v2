
from typing import Any
from pathlib import Path

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
}

def build_phase62e_report(project_root: str | Path | None = None) -> dict[str, Any]:
    contracts = []
    def add(name: str, ok: bool, detail: str = "") -> None:
        contracts.append({"name": name, "ok": bool(ok), "detail": detail})
    try:
        from tradebot.release_audit_legacy_api_drift_compatibility_h4 import build_phase61_h4_report
        h4 = build_phase61_h4_report(project_root=project_root)
        add("phase61_h4_report_keys", bool(h4.get("phase_61_h4_closed") and h4.get("production_hardening_signature_compatibility_v2_preserved")))
    except Exception as exc:
        add("phase61_h4_report_keys", False, repr(exc))
    try:
        from tradebot.release_audit_legacy_api_drift_compatibility_h5 import build_phase61_h5_report
        h5 = build_phase61_h5_report(project_root=project_root)
        add("phase61_h5_report_keys", bool(h5.get("phase_61_h5_closed") and h5.get("h4_report_predicate_fixed_by_h5")))
    except Exception as exc:
        add("phase61_h5_report_keys", False, repr(exc))
    try:
        from tradebot.release_audit_legacy_api_drift_compatibility_h6 import build_phase61_h6_report
        h6 = build_phase61_h6_report(project_root=project_root)
        add("phase61_h6_report_keys", bool(h6.get("phase_61_h6_closed") and h6.get("production_hardening_unknown_location_closed")))
    except Exception as exc:
        add("phase61_h6_report_keys", False, repr(exc))
    try:
        from tradebot.production_hardening import RuntimeLockHandle, acquire_runtime_lock, release_runtime_lock
        handle = acquire_runtime_lock(project_root=project_root)
        released = release_runtime_lock(handle)
        add("runtime_lock_handle_release_type", isinstance(released, RuntimeLockHandle))
    except Exception as exc:
        add("runtime_lock_handle_release_type", False, repr(exc))
    try:
        from tradebot.binance_environment import resolve_binance_environment
        profile = resolve_binance_environment("spot_demo", "https://demo-api.binance.com")
        add("binance_endpoint_profile_fields", bool(getattr(profile, "allowed_rest_hosts", None) and getattr(profile, "market_stream_base_url", None)))
    except Exception as exc:
        add("binance_endpoint_profile_fields", False, repr(exc))
    try:
        from tradebot.config_safety import build_config_safety_snapshot
        snap = build_config_safety_snapshot(None)
        add("config_safety_contract_version", snap.get("contract_version") == "4B.4.3.6.6.15")
    except Exception as exc:
        add("config_safety_contract_version", False, repr(exc))
    ready = sum(1 for item in contracts if item["ok"])
    ok = ready == len(contracts)
    return {
        "ok": ok,
        "status": "READY" if ok else "BLOCKED",
        "patch_id": "4B436662E",
        "patch_version": "4B.4.3.6.6.62E",
        "decision": "API_BINANCE_CONFIG_ENGINE_CONTRACT_FINALIZATION_READY_NO_PAPER_SUBMIT_NO_NETWORK_ORDER_NO_LIVE_NO_EXCHANGE_SUBMIT_LOCKED" if ok else "API_BINANCE_CONFIG_ENGINE_CONTRACT_FINALIZATION_BLOCKED",
        "contract_count": len(contracts),
        "contract_ready_count": ready,
        "contracts": contracts,
        "final_safety_violation_count": 0 if ok else len(contracts) - ready,
        "final_safety_violations": [item for item in contracts if not item["ok"]],
        **SAFETY_FALSE,
    }
