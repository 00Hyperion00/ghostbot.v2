from __future__ import annotations

import argparse
import json
import py_compile
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.32B-H1"
REQUIRED_FILES = [
    "src/tradebot/operator_cockpit_unified.py",
    "tools/run_operator_cockpit_unified.py",
    "start_tradebot_v2_operator_cockpit.bat",
    "TradeBot V2 Operator Cockpit.bat",
    "run_dashboard.bat",
    "start_dashboard.bat",
    "start_tradebot.bat",
]
REQUIRED_MARKERS = [
    "SECOND_MICRO_CANDIDATE_ONLY",
    "LIVE SUBMIT LOCKED",
    "approved_for_second_micro_order",
    "candidate_notional_usdt",
    "shadow_collection_active",
    "no_live_order_lock",
    "32C is required",
]
FORBIDDEN_MARKERS = [
    "create_order(",
    "futures_create_order(",
    "new_order(",
    "client.order_market",
    "approved_for_live_real_order=True",
    "approved_for_second_micro_order=True",
]

def _ok_file(path: Path) -> bool:
    return path.exists() and path.is_file() and path.stat().st_size > 0

def check(root: Path) -> dict[str, Any]:
    checks: dict[str, Any] = {}
    for rel in REQUIRED_FILES:
        checks[f"{rel}_exists"] = _ok_file(root / rel)
    module_path = root / "src/tradebot/operator_cockpit_unified.py"
    text = module_path.read_text(encoding="utf-8", errors="ignore") if module_path.exists() else ""
    checks["required_markers_present"] = {marker: marker in text for marker in REQUIRED_MARKERS}
    checks["forbidden_submit_markers_absent"] = {marker: marker not in text for marker in FORBIDDEN_MARKERS}
    checks["old_launchers_redirect_to_unified"] = {}
    for rel in ("run_dashboard.bat", "start_dashboard.bat", "start_tradebot.bat"):
        launcher_text = (root / rel).read_text(encoding="utf-8", errors="ignore") if (root / rel).exists() else ""
        checks["old_launchers_redirect_to_unified"][rel] = "start_tradebot_v2_operator_cockpit.bat" in launcher_text
    compile_results: dict[str, str] = {}
    for rel in ("src/tradebot/operator_cockpit_unified.py", "tools/run_operator_cockpit_unified.py"):
        try:
            py_compile.compile(str(root / rel), doraise=True)
            compile_results[rel] = "ok"
        except Exception as exc:
            compile_results[rel] = str(exc)
    checks["py_compile"] = compile_results
    try:
        import sys
        sys.path.insert(0, str(root / "src"))
        from tradebot.operator_cockpit_unified import build_cockpit_snapshot
        snapshot = build_cockpit_snapshot(root, include_status_endpoint=False).to_dict()
        checks["snapshot_build_ok"] = True
        checks["snapshot_no_live_order_lock"] = snapshot.get("no_live_order_lock") is True
        checks["snapshot_patch_network_submit_false"] = snapshot.get("second_micro_candidate", {}).get("network_submit_allowed") is False
        checks["snapshot_exchange_submit_false"] = snapshot.get("second_micro_candidate", {}).get("exchange_submit_allowed") is False
        checks["latest_accepted_phase"] = snapshot.get("latest_accepted_phase")
    except Exception as exc:
        checks["snapshot_build_ok"] = False
        checks["snapshot_error"] = str(exc)
    ok = (
        all(v for k, v in checks.items() if k.endswith("_exists"))
        and all(checks["required_markers_present"].values())
        and all(checks["forbidden_submit_markers_absent"].values())
        and all(checks["old_launchers_redirect_to_unified"].values())
        and all(value == "ok" for value in checks["py_compile"].values())
        and checks.get("snapshot_build_ok") is True
        and checks.get("snapshot_no_live_order_lock") is True
        and checks.get("snapshot_patch_network_submit_false") is True
        and checks.get("snapshot_exchange_submit_false") is True
    )
    return {
        "ok": ok,
        "contract_version": CONTRACT_VERSION,
        "checks": checks,
        "approved_for_live_real_order": False,
        "approved_for_second_micro_order": False,
        "patch_network_submit_attempted": False,
        "exchange_submit_performed": False,
    }

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    result = check(Path.cwd())
    if args.once_json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"{CONTRACT_VERSION} Operator Cockpit unified sync check ok={result['ok']}")
    return 0 if result["ok"] else 2

if __name__ == "__main__":
    raise SystemExit(main())
