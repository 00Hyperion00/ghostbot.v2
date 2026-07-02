from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any

PATCH_VERSION = "4B.4.3.6.6.33G"


def _fetch_json(url: str, headers: dict[str, str]) -> dict[str, Any]:
    request = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(request, timeout=5) as response:  # nosec - local operator helper
        payload = response.read().decode("utf-8")
    data = json.loads(payload)
    return data if isinstance(data, dict) else {"raw": data}


def main() -> None:
    parser = argparse.ArgumentParser(description="TradeBot cockpit runtime snapshot check helper")
    parser.add_argument("--url", default="http://127.0.0.1:8787/api/cockpit/snapshot")
    parser.add_argument("--token", default=os.getenv("TRADEBOT_COCKPIT_AUTH_TOKEN", ""))
    parser.add_argument("--operator", default=os.getenv("TRADEBOT_COCKPIT_OPERATOR", "operator-local"))
    args = parser.parse_args()
    headers = {"X-TradeBot-Auth": args.token, "X-TradeBot-Operator": args.operator}
    result: dict[str, Any]
    try:
        snapshot = _fetch_json(args.url, headers)
        runtime_lock = snapshot.get("runtime_lock") or {}
        entry_guard = (snapshot.get("runtime_awareness") or {}).get("entry_guard") or snapshot.get("entry_guard") or {}
        result = {
            "patch_version": PATCH_VERSION,
            "ok": bool(snapshot.get("ok", False)),
            "server_reachable": True,
            "startup_error": (snapshot.get("cockpit") or {}).get("startup_error"),
            "runtime_lock_pid": runtime_lock.get("pid"),
            "runtime_lock_held_by_current_process": runtime_lock.get("held_by_current_process"),
            "risk_badge": (snapshot.get("runtime_awareness") or {}).get("risk_badge"),
            "entry_guard_disable_reason": entry_guard.get("disable_reason"),
            "reconciliation_execution": snapshot.get("reconciliation_execution") or (snapshot.get("runtime_awareness") or {}).get("reconciliation_execution") or {},
        }
    except urllib.error.URLError as exc:
        result = {"patch_version": PATCH_VERSION, "ok": False, "server_reachable": False, "error": str(exc), "hint": "Start cockpit first in a separate PowerShell window."}
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    if not result.get("server_reachable", False):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
