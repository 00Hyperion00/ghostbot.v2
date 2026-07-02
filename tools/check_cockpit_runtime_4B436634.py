from __future__ import annotations

import argparse
import json
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

PATCH_VERSION = "4B.4.3.6.6.34"


def _get_json(url: str, *, token: str, operator: str) -> dict[str, Any]:
    req = Request(url, headers={"X-TradeBot-Auth": token, "X-TradeBot-Operator": operator})
    with urlopen(req, timeout=5) as resp:  # noqa: S310 - local operator tool
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Check 34 demo entry execution controlled re-enablement runtime state.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8787")
    parser.add_argument("--token", required=True)
    parser.add_argument("--operator", required=True)
    args = parser.parse_args()
    try:
        health = _get_json(f"{args.base_url}/api/cockpit/health", token=args.token, operator=args.operator)
        snapshot = _get_json(f"{args.base_url}/api/cockpit/snapshot", token=args.token, operator=args.operator)
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        print(json.dumps({"patch_version": PATCH_VERSION, "ok": False, "server_reachable": False, "error": str(exc)}, indent=2))
        return 2
    cockpit = snapshot.get("cockpit", {}) if isinstance(snapshot, dict) else {}
    runtime_lock = snapshot.get("runtime_lock", {}) if isinstance(snapshot, dict) else {}
    entry_guard = snapshot.get("entry_guard", {}) if isinstance(snapshot, dict) else {}
    demo_gate = snapshot.get("demo_entry_execution_gate", {}) if isinstance(snapshot, dict) else {}
    cache = snapshot.get("engine_status_balance_cache_reconciliation", {}) if isinstance(snapshot, dict) else {}
    payload = {
        "patch_version": PATCH_VERSION,
        "ok": bool(snapshot.get("ok") and health.get("ok") and demo_gate.get("enabled") and cockpit.get("startup_error") is None),
        "server_reachable": True,
        "health_ok": bool(health.get("ok")),
        "startup_error": cockpit.get("startup_error"),
        "runtime_lock_pid": runtime_lock.get("pid"),
        "runtime_lock_held_by_current_process": bool(runtime_lock.get("held_by_current_process")),
        "risk_badge": snapshot.get("runtime_awareness", {}).get("risk_badge"),
        "entry_actions_enabled": bool(entry_guard.get("entry_actions_enabled")),
        "entry_guard_disable_reason": entry_guard.get("disable_reason"),
        "demo_entry_execution_gate": demo_gate,
        "demo_trade_enablement_ready": bool(demo_gate.get("demo_trade_enablement_ready")),
        "dry_run_passed": bool(demo_gate.get("dry_run_passed")),
        "filters_verified": bool(demo_gate.get("filters_verified")),
        "intent_recorded": bool(demo_gate.get("intent_recorded")),
        "demo_trade_authorization_valid": bool(demo_gate.get("demo_trade_authorization_valid")),
        "runtime_snapshot_override_active": bool(cache.get("runtime_snapshot_override_active")),
        "stale_engine_balance_invalidated": bool(cache.get("stale_engine_balance_invalidated")),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
