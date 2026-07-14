
from __future__ import annotations
import argparse, json, py_compile
from pathlib import Path
PATCH_VERSION = "4B.4.3.6.6.62F-H5"
PATCH_ID = "4B436662F-H5"
SAFETY = {"approved_for_exchange_submit": False, "approved_for_live_real": False, "exchange_submit_performed": False, "live_real_approved_by_patch": False, "network_order_submit_performed": False, "network_request_performed": False, "order_actions_performed": False, "paper_order_submit_performed": False, "paper_submit_enabled_by_patch": False, "paper_submit_performed": False, "private_api_access_allowed": False, "reload_performed": False, "runtime_start_performed": False, "trading_action_performed": False, "training_performed": False}

def _compile(path: str) -> tuple[bool, str]:
    try:
        py_compile.compile(path, doraise=True); return True, ""
    except Exception as exc:
        return False, str(exc)

def build_report() -> dict[str, object]:
    contracts=[]
    for path in ("src/tradebot/api.py", "src/tradebot/config_safety.py", "src/tradebot/engine.py", "src/tradebot/ui/dashboard.py"):
        ok, detail = _compile(path); contracts.append({"name": f"py_compile_{path}", "ok": ok, "detail": detail})
    text = Path("src/tradebot/api.py").read_text(encoding="utf-8") if Path("src/tradebot/api.py").exists() else ""
    contracts.append({"name": "api_ok_contract_markers", "ok": "already_running" in text and "market_klines" in text and "events_audit" in text, "detail": ""})
    cfg = Path("src/tradebot/config_safety.py").read_text(encoding="utf-8") if Path("src/tradebot/config_safety.py").exists() else ""
    contracts.append({"name": "config_reason_codes_and_binance_ok", "ok": "LIVE_REAL_DOUBLE_CONFIRM_MISSING" in cfg and '"ok": ok' in cfg, "detail": ""})
    eng = Path("src/tradebot/engine.py").read_text(encoding="utf-8") if Path("src/tradebot/engine.py").exists() else ""
    contracts.append({"name": "engine_rehydration_markers", "ok": "recovered_balance" in eng and "TASK_CANCEL_TIMEOUT" in eng, "detail": ""})
    ready=sum(1 for c in contracts if c["ok"]); ok=ready==len(contracts)
    return {"patch_id": PATCH_ID, "patch_version": PATCH_VERSION, "ok": ok, "status": "READY" if ok else "BLOCKED", "decision": "API_CONFIG_ENGINE_REHYDRATION_STOP_CLEANUP_READY_NO_PAPER_SUBMIT_NO_NETWORK_ORDER_NO_LIVE_NO_EXCHANGE_SUBMIT_LOCKED" if ok else "API_CONFIG_ENGINE_REHYDRATION_STOP_CLEANUP_BLOCKED", "contract_count": len(contracts), "contract_ready_count": ready, "contracts": contracts, **SAFETY}

def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("--once-json", action="store_true"); parser.parse_args(); report=build_report(); print(json.dumps(report, ensure_ascii=False, sort_keys=True)); return 0 if report["ok"] else 1
if __name__ == "__main__":
    raise SystemExit(main())
