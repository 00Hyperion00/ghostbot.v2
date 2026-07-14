from __future__ import annotations

import argparse
import json
import py_compile
import tempfile
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

PATCH_ID = "4B436662F-H6"
PATCH_VERSION = "4B.4.3.6.6.62F-H6"
SAFETY = {
    "approved_for_exchange_submit": False,
    "approved_for_live_real": False,
    "exchange_submit_performed": False,
    "live_real_approved_by_patch": False,
    "network_order_submit_performed": False,
    "network_request_performed": False,
    "order_actions_performed": False,
    "paper_order_submit_performed": False,
    "paper_submit_enabled_by_patch": False,
    "paper_submit_performed": False,
    "private_api_access_allowed": False,
    "reload_performed": False,
    "runtime_start_performed": False,
    "trading_action_performed": False,
    "training_performed": False,
}


def _contract(name: str, ok: bool, detail: str = "") -> dict[str, Any]:
    return {"name": name, "ok": bool(ok), "detail": detail}


def build_report() -> dict[str, Any]:
    contracts: list[dict[str, Any]] = []
    compile_targets = (
        "src/tradebot/api.py",
        "src/tradebot/config_safety.py",
        "src/tradebot/engine.py",
        "src/tradebot/models.py",
        "src/tradebot/ui/dashboard.py",
        "src/tradebot/hyp005_shadow_evidence_path_contract.py",
        "src/tradebot/hyp006_shadow_registration_operator_approval.py",
        "src/tradebot/operator_cockpit_v2_read_only.py",
        "src/tradebot/paper_sandbox_execution_reconciliation_gate.py",
        "src/tradebot/_production_hardening_compat.py",
    )
    for target in compile_targets:
        try:
            py_compile.compile(target, doraise=True)
            contracts.append(_contract(f"py_compile_{target}", True))
        except Exception as exc:
            contracts.append(_contract(f"py_compile_{target}", False, str(exc)))
    try:
        from tradebot.config_safety import build_config_safety_snapshot

        class Settings:
            execution_mode = "live_real"
            market_type = "spot_mainnet"
            base_url = "https://api.binance.com"
            api_key = "ABCD1234SECRET"
            api_secret = "VERYSECRET"
            live_trading_armed = False
            live_real_double_confirm = False
            ai_provider_enabled = False

        snapshot = build_config_safety_snapshot(Settings())
        contracts.append(
            _contract(
                "config_safety_final_contract",
                snapshot.get("safe_to_trade") is False
                and "LIVE_REAL_NOT_ARMED" in snapshot.get("reason_codes", [])
                and "LIVE_REAL_DOUBLE_CONFIRM_MISSING" in snapshot.get("reason_codes", [])
                and snapshot.get("binance_environment", {}).get("ok") is True
                and str(snapshot.get("api_key", {}).get("redacted", "")).startswith("ABCD")
                and snapshot.get("api_secret", {}).get("redacted") == "***",
            )
        )
    except Exception as exc:
        contracts.append(_contract("config_safety_final_contract", False, str(exc)))
    try:
        from tradebot.operator_cockpit_v2_read_only import (
            _safe_action_manifest,
            collect_operator_cockpit_snapshot,
            make_operator_cockpit_server,
        )

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            snapshot = collect_operator_cockpit_snapshot(root)
            manifest = _safe_action_manifest(root)
            server = make_operator_cockpit_server(root, port=0)
            server.server_close()
            contracts.append(
                _contract(
                    "operator_cockpit_final_contract",
                    snapshot.get("read_only") is True
                    and snapshot.get("contract_version") == "4B.4.3.6.6.26A"
                    and manifest.get("read_only") is True
                    and manifest.get("get_only") is True,
                )
            )
    except Exception as exc:
        contracts.append(_contract("operator_cockpit_final_contract", False, str(exc)))
    try:
        from tradebot.paper_sandbox_execution_reconciliation_gate import (
            READY_DECISION,
            build_paper_sandbox_execution_reconciliation_snapshot,
        )

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            ready = build_paper_sandbox_execution_reconciliation_snapshot(
                None,
                {"ok": True},
                {"submitted_to_exchange": False, "quote_balance_delta_usd": 0.0},
                sqlite_path=root / "ready.sqlite",
            )
            blocked = build_paper_sandbox_execution_reconciliation_snapshot(
                None,
                {"ok": True},
                {"submitted_to_exchange": False, "quote_balance_delta_usd": -1.0},
                sqlite_path=root / "blocked.sqlite",
            )
        contracts.append(
            _contract(
                "paper30o_final_contract",
                ready.get("decision") == READY_DECISION
                and ready.get("sqlite_audit_mirror_verified") is True
                and blocked.get("approved_for_mismatch_zero_proof") is False,
            )
        )
    except Exception as exc:
        contracts.append(_contract("paper30o_final_contract", False, str(exc)))
    try:
        from tradebot.hyp005_shadow_evidence_path_contract import normalize_logger_report_evidence_paths

        value = normalize_logger_report_evidence_paths({"source_reports": []})
        contracts.append(
            _contract(
                "hyp005_utf8_final_contract",
                value.get("evidence_paths_resolved") is True
                and value.get("powershell_safe_ascii_json") is True,
            )
        )
    except Exception as exc:
        contracts.append(_contract("hyp005_utf8_final_contract", False, str(exc)))
    try:
        from tradebot.hyp006_shadow_registration_operator_approval import build_registration_script

        script = build_registration_script(project_root=Path.cwd(), approval_json=Path("approval.json"), reports_dir=Path("reports"), symbols=["ADAUSDT"])
        contracts.append(
            _contract(
                "hyp006_registration_final_contract",
                "System.Text.UTF8Encoding($false)" in script
                and "--registration-json" in script
                and "--registration-approval-json" in script,
            )
        )
    except Exception as exc:
        contracts.append(_contract("hyp006_registration_final_contract", False, str(exc)))
    try:
        from fastapi.testclient import TestClient
        from types import SimpleNamespace
        from tradebot.api import create_app

        class _Provider:
            def __init__(self) -> None:
                self.args = None

            def reload(self, *args):
                self.args = args
                return {"ok": True, "available": True}

        class _Store:
            def list_logs(self, limit=100):
                return [{"ts": 1}, {"ts": 2}]

            def append_log(self, event):
                return None

        class _Engine:
            def __init__(self) -> None:
                self.settings = SimpleNamespace(
                    symbol="ETHUSDT",
                    ai_model_path="old.ubj",
                    ai_confidence_threshold=0.50,
                    ai_buy_threshold=0.64,
                    ai_sell_threshold=0.57,
                    ai_hold_threshold=0.45,
                    ai_margin_threshold=0.55,
                    ai_reject_low_margin_threshold=0.08,
                )
                self.ai_provider = _Provider()
                self.store = _Store()
                self.runtime = SimpleNamespace(state="FLAT")
                self._running = False

            async def start(self):
                return False

            async def stop(self):
                return False

        engine = _Engine()
        client = TestClient(create_app(engine))
        reload_payload = client.post(
            "/ai/reload",
            json={"model_path": "models/new.ubj", "threshold": 0.73},
        ).json()
        logs_payload = client.get("/logs?limit=2&order=desc").json()
        start_payload = client.post("/start").json()
        stop_payload = client.post("/stop").json()
        contracts.append(
            _contract(
                "api_behavior_final_contract",
                reload_payload.get("ok") is True
                and engine.ai_provider.args
                == ("models/new.ubj", 0.73, 0.64, 0.57, 0.45, 0.55, 0.08)
                and logs_payload == [{"ts": 1}, {"ts": 2}]
                and start_payload.get("started") is False
                and stop_payload.get("stopped") is False,
            )
        )
    except Exception as exc:
        contracts.append(_contract("api_behavior_final_contract", False, str(exc)))
    try:
        from tradebot.models import RuntimeState

        runtime = RuntimeState()
        runtime.last_reconcile_result = "ORPHAN_PENDING"
        runtime.active_anomaly_code = "PENDING_STATE_WITHOUT_ORDER"
        runtime.legacy_dynamic_field = True
        contracts.append(
            _contract(
                "runtime_state_legacy_slots_contract",
                runtime.last_reconcile_result == "ORPHAN_PENDING"
                and runtime.active_anomaly_code == "PENDING_STATE_WITHOUT_ORDER"
                and runtime.legacy_dynamic_field is True,
            )
        )
    except Exception as exc:
        contracts.append(_contract("runtime_state_legacy_slots_contract", False, str(exc)))
    try:
        from tradebot._production_hardening_compat import (
            acquire_runtime_lock,
            build_production_hardening_snapshot,
            canonical_evidence_commit_decision,
            evaluate_promotion_gate,
            release_runtime_lock,
        )

        with tempfile.TemporaryDirectory() as temp:
            lock_path = Path(temp) / "runtime.lock"
            handle = acquire_runtime_lock(lock_path, identity="h6-check")
            duplicate_blocked = False
            try:
                acquire_runtime_lock(lock_path, identity="h6-second")
            except RuntimeError as exc:
                duplicate_blocked = "RUNTIME_LOCK_ALREADY_HELD" in str(exc)
            finally:
                release_runtime_lock(handle)
        hardening = build_production_hardening_snapshot(object())
        gate = evaluate_promotion_gate(
            target="runtime_overlay_activation",
            hypothesis_payload={"matured_count": 30},
        )
        commit = canonical_evidence_commit_decision("tools/_patch_backup_x/file.py")
        contracts.append(
            _contract(
                "production_hardening_final_contract",
                duplicate_blocked
                and hardening.get("contract_version") == "4B.4.3.6.6.29A"
                and hardening.get("mutations", {}).get("trading_action_performed") is False
                and gate.get("approved_for_runtime_overlay_activation") is False
                and "HYPOTHESIS_PERFORMANCE_NOT_PRODUCTION_READINESS"
                in gate.get("reason_codes", [])
                and commit.get("canonical_evidence_commit_allowed") is False,
            )
        )
    except Exception as exc:
        contracts.append(_contract("production_hardening_final_contract", False, str(exc)))
    try:
        import tradebot.operator_cockpit_v2_read_only as cockpit

        version = cockpit.OPERATOR_COCKPIT_V2_RISK_SIZING_TELEMETRY_VERSION
        contracts.append(
            _contract(
                "operator_dual_telemetry_string_contract",
                isinstance(version, str)
                and version == "4B.4.3.6.6.27G"
                and "61-H4" in version
                and "Risk-Sizing Telemetry JSON Aç" in cockpit.DASHBOARD_HTML
                and "MAE / MFE verisi henüz oluşmadı." in cockpit.DASHBOARD_HTML,
            )
        )
    except Exception as exc:
        contracts.append(_contract("operator_dual_telemetry_string_contract", False, str(exc)))
    ready_count = sum(1 for item in contracts if item["ok"])
    ok = ready_count == len(contracts)
    return {
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "ok": ok,
        "status": "READY" if ok else "BLOCKED",
        "decision": (
            "FINAL_FULL_REPO_CONTRACT_CLOSURE_READY_NO_PAPER_SUBMIT_NO_NETWORK_ORDER_NO_LIVE_NO_EXCHANGE_SUBMIT_LOCKED"
            if ok
            else "FINAL_FULL_REPO_CONTRACT_CLOSURE_BLOCKED"
        ),
        "contract_count": len(contracts),
        "contract_ready_count": ready_count,
        "contracts": contracts,
        **SAFETY,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once-json", action="store_true")
    parser.parse_args()
    report = build_report()
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
