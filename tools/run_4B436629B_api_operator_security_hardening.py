from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from check_4B436629B_api_operator_security_hardening import CONTRACT_VERSION, build_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate 4B.4.3.6.6.29B API operator security hardening decision report")
    parser.add_argument("--reports-dir", default="reports/production_hardening")
    args = parser.parse_args()
    root = Path.cwd()
    report = build_report(root)
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    payload = {
        "ok": bool(report.get("ok")),
        "contract_version": CONTRACT_VERSION,
        "decision": "API_OPERATOR_SECURITY_HARDENING_READY_LIVE_REAL_STILL_BLOCKED" if report.get("ok") else "API_OPERATOR_SECURITY_HARDENING_NOT_READY",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "read_only": True,
        "api_operator_security_hardening": True,
        "approved_for_destructive_endpoint_typed_confirmation_baseline": bool(report["checks"].get("typed_confirmation_guard_present")),
        "approved_for_token_ttl_baseline": bool(report["checks"].get("token_ttl_guard_present")),
        "approved_for_live_arm_ttl_baseline": bool(report["checks"].get("live_arm_ttl_guard_present")),
        "approved_for_operator_audit_baseline": bool(report["checks"].get("operator_audit_baseline_present")),
        "approved_for_local_only_binding_baseline": bool(report["checks"].get("local_only_guard_present")),
        "approved_for_runtime_overlay_activation_candidate": False,
        "approved_for_parameter_relaxation_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "runtime_overlay_activation_performed": False,
        "strategy_parameter_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "paper_live_order_enablement_present": False,
        "checks": report["checks"],
        "recommendation": "Keep live-real, paper/live, runtime overlay activation and order actions blocked. Continue production hardening with persistence/audit ledger upgrades before any paper/live gate.",
    }
    reports_dir = Path(args.reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    json_path = reports_dir / f"4B436629B_api_operator_security_hardening_decision_{now}.json"
    md_path = json_path.with_suffix(".md")
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8", newline="\n")
    md_path.write_text(
        "# 4B.4.3.6.6.29B API / Operator Security Hardening Decision Report\n\n"
        f"- decision: `{payload['decision']}`\n"
        f"- read_only: `{payload['read_only']}`\n"
        f"- approved_for_token_ttl_baseline: `{payload['approved_for_token_ttl_baseline']}`\n"
        f"- approved_for_live_arm_ttl_baseline: `{payload['approved_for_live_arm_ttl_baseline']}`\n"
        f"- approved_for_live_real: `{payload['approved_for_live_real']}`\n"
        f"- approved_for_paper_candidate: `{payload['approved_for_paper_candidate']}`\n"
        f"- trading_action_performed: `{payload['trading_action_performed']}`\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"{CONTRACT_VERSION} API / Operator Security Hardening {payload['decision']}")
    for key in (
        "read_only",
        "approved_for_destructive_endpoint_typed_confirmation_baseline",
        "approved_for_token_ttl_baseline",
        "approved_for_live_arm_ttl_baseline",
        "approved_for_operator_audit_baseline",
        "approved_for_local_only_binding_baseline",
        "approved_for_runtime_overlay_activation_candidate",
        "approved_for_parameter_relaxation_candidate",
        "approved_for_paper_candidate",
        "approved_for_live_real",
        "training_performed",
        "reload_performed",
        "trading_action_performed",
    ):
        print(f" - {key}: {payload[key]}")
    print(f"report_json: {json_path}")
    print(f"report_md: {md_path}")
    return 0 if payload["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
