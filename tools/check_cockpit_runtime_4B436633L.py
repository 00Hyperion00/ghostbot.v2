from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from typing import Any

PATCH_VERSION = "4B.4.3.6.6.33L"


def _get_json(url: str, headers: dict[str, str]) -> dict[str, Any]:
    req = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=10) as resp:  # nosec - local cockpit helper
        data = resp.read().decode("utf-8")
    loaded = json.loads(data)
    return loaded if isinstance(loaded, dict) else {}


def main() -> int:
    parser = argparse.ArgumentParser(description="Check 33L cockpit runtime source-gate contract.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8787")
    parser.add_argument("--token", required=True)
    parser.add_argument("--operator", default="operator-local")
    args = parser.parse_args()
    headers = {"X-TradeBot-Auth": args.token, "X-TradeBot-Operator": args.operator}
    result: dict[str, Any] = {"patch_version": PATCH_VERSION, "ok": False, "server_reachable": False}
    try:
        health = _get_json(f"{args.base_url.rstrip('/')}/api/cockpit/health", headers)
        snapshot = _get_json(f"{args.base_url.rstrip('/')}/api/cockpit/snapshot", headers)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        result.update({"error": str(exc), "hint": "Start cockpit first in a separate PowerShell window."})
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
        return 1
    runtime_awareness = snapshot.get("runtime_awareness") or {}
    runtime_lock = runtime_awareness.get("runtime_lock") or snapshot.get("runtime_lock") or {}
    entry_guard = runtime_awareness.get("entry_guard") or snapshot.get("entry_guard") or {}
    evidence_gate = snapshot.get("external_recovery_evidence_gate") or runtime_awareness.get("external_recovery_evidence_gate") or {}
    source_gate = snapshot.get("exchange_environment_source_gate") or runtime_awareness.get("exchange_environment_source_gate") or {}
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
        "entry_guard_disable_reason": entry_guard.get("disable_reason"),
        "external_recovery_evidence_gate": evidence_gate,
        "exchange_environment_source_gate": source_gate,
        "config_environment_consistent": (source_gate.get("config_audit") or {}).get("config_environment_consistent"),
        "balance_review_source": source_gate.get("balance_review_source"),
        "engine_status_balance_source_rejected": source_gate.get("engine_status_balance_source_rejected"),
        "fresh_exchange_balance_present": source_gate.get("fresh_exchange_balance_present"),
        "fresh_exchange_balance_fresh": source_gate.get("fresh_exchange_balance_fresh"),
        "fresh_exchange_balance_verified": source_gate.get("fresh_exchange_balance_verified"),
        "fresh_base_free": source_gate.get("fresh_base_free"),
        "fresh_base_tradable": source_gate.get("fresh_base_tradable"),
        "fresh_quote_free": source_gate.get("fresh_quote_free"),
        "no_mismatch_from_verified_fresh_source": source_gate.get("no_mismatch_from_verified_fresh_source"),
        "entry_guard_release_verified": bool(evidence_gate.get("entry_guard_release_verified")) and bool(source_gate.get("entry_guard_release_verified")),
    })
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
