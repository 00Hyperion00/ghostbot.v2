from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

PATCH_VERSION = "4B.4.3.6.6.33I-H1"


def _request_json(url: str, token: str, operator: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={
            "X-TradeBot-Auth": token,
            "X-TradeBot-Operator": operator,
        },
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=5) as response:  # noqa: S310 - local operator helper
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Check 33I-H1 cockpit runtime snapshot health.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8787")
    parser.add_argument("--token", required=True)
    parser.add_argument("--operator", required=True)
    args = parser.parse_args()

    result: dict = {"patch_version": PATCH_VERSION}
    try:
        health = _request_json(f"{args.base_url.rstrip('/')}/api/cockpit/health", args.token, args.operator)
        snapshot = _request_json(f"{args.base_url.rstrip('/')}/api/cockpit/snapshot", args.token, args.operator)
    except urllib.error.URLError as exc:
        result.update({
            "ok": False,
            "server_reachable": False,
            "error": str(exc),
            "hint": "Start cockpit first in a separate PowerShell window.",
        })
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 1
    except Exception as exc:
        result.update({
            "ok": False,
            "server_reachable": True,
            "error": repr(exc),
            "hint": "Snapshot request failed; check cockpit terminal for traceback.",
        })
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 1

    runtime_lock = snapshot.get("runtime_lock") or {}
    runtime_awareness = snapshot.get("runtime_awareness") or {}
    recovery_gate = snapshot.get("engine_position_recovery_gate") or snapshot.get("runtime_awareness", {}).get("engine_position_recovery_gate") or {}
    reconciliation_decision_apply = snapshot.get("reconciliation_decision_apply") or runtime_awareness.get("reconciliation_decision_apply") or {}

    startup_error = (snapshot.get("cockpit") or {}).get("startup_error")
    ok = bool(snapshot.get("ok")) and startup_error is None
    result.update({
        "ok": ok,
        "server_reachable": True,
        "health_ok": health.get("ok"),
        "startup_error": startup_error,
        "runtime_lock_pid": runtime_lock.get("pid"),
        "runtime_lock_held_by_current_process": runtime_lock.get("held_by_current_process"),
        "risk_badge": runtime_awareness.get("risk_badge"),
        "entry_guard_disable_reason": (runtime_awareness.get("entry_guard") or {}).get("disable_reason"),
        "reconciliation_decision_apply": reconciliation_decision_apply,
        "engine_position_recovery_gate": recovery_gate,
    })
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
