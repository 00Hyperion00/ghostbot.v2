from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from typing import Any

PATCH_VERSION = "4B.4.3.6.6.33M"


def _get_json(url: str, headers: dict[str, str]) -> dict[str, Any]:
    req = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=10) as resp:  # nosec - local cockpit helper
        data = resp.read().decode("utf-8")
    loaded = json.loads(data)
    return loaded if isinstance(loaded, dict) else {}


def main() -> int:
    parser = argparse.ArgumentParser(description="Check 33M cockpit runtime cache-reconciliation contract.")
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
    cache_reconciliation = runtime_awareness.get("engine_status_balance_cache_reconciliation") or source_gate.get("engine_status_balance_cache_reconciliation") or {}
    startup_error = (snapshot.get("cockpit") or {}).get("startup_error")
    ok = bool(snapshot.get("ok")) and startup_error is None and bool(runtime_lock.get("held_by_current_process", False))
    final_release_ok = bool(evidence_gate.get("entry_guard_release_verified")) and bool(source_gate.get("entry_guard_release_verified")) and bool(entry_guard.get("entry_actions_enabled", False))
    result.update({
        "ok": ok,
        "server_reachable": True,
        "health_ok": health.get("ok"),
        "startup_error": startup_error,
        "runtime_lock_pid": runtime_lock.get("pid"),
        "runtime_lock_held_by_current_process": runtime_lock.get("held_by_current_process"),
        "risk_badge": runtime_awareness.get("risk_badge"),
        "entry_actions_enabled": entry_guard.get("entry_actions_enabled"),
        "entry_guard_disable_reason": entry_guard.get("disable_reason"),
        "entry_guard_release_verified": final_release_ok,
        "external_recovery_entry_guard_release_verified": evidence_gate.get("entry_guard_release_verified"),
        "exchange_environment_entry_guard_release_verified": source_gate.get("entry_guard_release_verified"),
        "verified_no_mismatch_with_evidence": evidence_gate.get("verified_no_mismatch_with_evidence"),
        "fresh_exchange_balance_verified": source_gate.get("fresh_exchange_balance_verified"),
        "no_mismatch_from_verified_fresh_source": source_gate.get("no_mismatch_from_verified_fresh_source"),
        "engine_status_balance_cache_reconciliation": cache_reconciliation,
        "runtime_snapshot_override_active": cache_reconciliation.get("runtime_snapshot_override_active"),
        "stale_engine_balance_invalidated": cache_reconciliation.get("stale_engine_balance_invalidated"),
        "risk_badge_recomputed_from_verified_fresh_source": cache_reconciliation.get("risk_badge_recomputed_from_verified_fresh_source"),
        "entry_guard_release_stabilized_after_safe_apply": cache_reconciliation.get("entry_guard_release_stabilized_after_safe_apply"),
        "fresh_base_free": source_gate.get("fresh_base_free"),
        "fresh_base_tradable": source_gate.get("fresh_base_tradable"),
        "fresh_quote_free": source_gate.get("fresh_quote_free"),
    })
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
