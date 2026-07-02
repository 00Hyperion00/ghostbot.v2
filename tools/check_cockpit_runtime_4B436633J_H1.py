from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from typing import Any

PATCH_VERSION = "4B.4.3.6.6.33J-H1"


def _request_json(url: str, token: str, operator: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"X-TradeBot-Auth": token, "X-TradeBot-Operator": operator})
    with urllib.request.urlopen(request, timeout=5.0) as response:
        payload = response.read().decode("utf-8")
    data = json.loads(payload)
    return data if isinstance(data, dict) else {"raw": data}


def main() -> int:
    parser = argparse.ArgumentParser(description="Check 33J-H1 recovery plan route hotfix runtime state.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8787")
    parser.add_argument("--token", required=True)
    parser.add_argument("--operator", required=True)
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    result: dict[str, Any] = {"patch_version": PATCH_VERSION}
    try:
        health = _request_json(f"{base}/api/cockpit/health", args.token, args.operator)
        snapshot = _request_json(f"{base}/api/cockpit/snapshot", args.token, args.operator)
    except urllib.error.URLError as exc:
        result.update({"ok": False, "server_reachable": False, "error": str(exc), "hint": "Start cockpit first in a separate PowerShell window."})
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
        return 1
    except Exception as exc:
        result.update({"ok": False, "server_reachable": True, "error": repr(exc), "hint": "Snapshot request failed; check cockpit terminal for traceback."})
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
        return 1
    runtime_awareness = snapshot.get("runtime_awareness") or {}
    runtime_lock = snapshot.get("runtime_lock") or {}
    recovery_gate = snapshot.get("engine_position_recovery_gate") or runtime_awareness.get("engine_position_recovery_gate") or {}
    apply_gate = snapshot.get("recovery_plan_apply_verification_gate") or recovery_gate.get("recovery_plan_apply_verification_gate") or {}
    startup_error = (snapshot.get("cockpit") or {}).get("startup_error")
    ok = bool(snapshot.get("ok")) and startup_error is None and bool(runtime_lock.get("held_by_current_process", False))
    result.update({
        "ok": ok,
        "server_reachable": True,
        "health_ok": health.get("ok"),
        "startup_error": startup_error,
        "runtime_lock_pid": runtime_lock.get("pid"),
        "runtime_lock_held_by_current_process": runtime_lock.get("held_by_current_process"),
        "risk_badge": runtime_awareness.get("risk_badge"),
        "recovery_status": recovery_gate.get("status"),
        "plan_present": recovery_gate.get("plan_present"),
        "plan_confirmed": recovery_gate.get("plan_confirmed"),
        "manual_external_recovery_confirmed": recovery_gate.get("manual_external_recovery_confirmed"),
        "verified_no_mismatch": recovery_gate.get("verified_no_mismatch"),
        "entry_guard_release_verified": recovery_gate.get("entry_guard_release_verified"),
        "recovery_plan_apply_verification_gate": apply_gate,
    })
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
