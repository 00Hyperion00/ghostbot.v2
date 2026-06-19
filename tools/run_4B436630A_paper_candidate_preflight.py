from __future__ import annotations

import argparse, json, sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from check_4B436630A_paper_candidate_preflight import CONTRACT_VERSION, build_report


def _load_preflight_snapshot(root: Path) -> dict[str, Any]:
    sys.path.insert(0, str(root / "src"))
    try:
        from tradebot.config import Settings
        from tradebot.paper_candidate_gate import build_paper_candidate_preflight_snapshot
        try:
            from tradebot.production_readiness_gate import build_consolidated_readiness_snapshot
            production = build_consolidated_readiness_snapshot(root / "reports" / "production_hardening")
        except Exception:
            production = {"decision": "PRODUCTION_READINESS_CONSOLIDATION_NOT_READY", "evidence_complete": False, "approved_for_paper_candidate_preflight": False}
        return build_paper_candidate_preflight_snapshot(Settings(), production)
    finally:
        try: sys.path.remove(str(root / "src"))
        except ValueError: pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate 4B.4.3.6.6.30A Paper Candidate Preflight decision report")
    parser.add_argument("--reports-dir", default="reports/production_hardening")
    args = parser.parse_args()
    root = Path.cwd()
    report = build_report(root)
    snapshot = _load_preflight_snapshot(root)
    ready = bool(report.get("ok")) and bool(snapshot.get("approved_for_no_order_to_paper_transition_preflight"))
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    payload = {
        "ok": bool(report.get("ok")),
        "contract_version": CONTRACT_VERSION,
        "decision": "PAPER_CANDIDATE_PREFLIGHT_READY_OPERATOR_APPROVAL_REQUIRED_LIVE_REAL_BLOCKED" if ready else "PAPER_CANDIDATE_PREFLIGHT_NOT_READY",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "read_only": True,
        "paper_candidate_preflight": True,
        "approved_for_no_order_to_paper_transition_preflight": bool(snapshot.get("approved_for_no_order_to_paper_transition_preflight", False)),
        "approved_for_paper_transition_candidate": bool(snapshot.get("approved_for_paper_transition_candidate", False)),
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "approved_for_runtime_overlay_activation_candidate": False,
        "approved_for_parameter_relaxation_candidate": False,
        "exchange_sandbox_isolated": bool(snapshot.get("exchange_sandbox_isolated", False)),
        "capital_cap_verified": bool(snapshot.get("capital_cap_verified", False)),
        "kill_switch_verified": bool(snapshot.get("kill_switch_verified", False)),
        "operator_approval_required": bool(snapshot.get("operator_approval_required", True)),
        "operator_approval_verified": bool(snapshot.get("operator_approval_verified", False)),
        "live_real_hard_block_verified": True,
        "runtime_activation_blocked": True,
        "paper_live_order_blocked": True,
        "training_reload_blocked": True,
        "runtime_overlay_activation_performed": False,
        "scheduler_mutation_performed": False,
        "strategy_parameter_mutation_performed": False,
        "hyp006_strategy_threshold_mutation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "paper_live_order_enablement_present": False,
        "snapshot": snapshot,
        "checks": report["checks"],
        "recommendation": "Do not enable paper orders yet. Proceed only to operator-approved paper transition candidate review if all preflight controls remain green.",
    }
    reports_dir = Path(args.reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    json_path = reports_dir / f"4B436630A_paper_candidate_preflight_decision_{now}.json"
    md_path = json_path.with_suffix(".md")
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8", newline="\n")
    md_path.write_text(
        "# 4B.4.3.6.6.30A Paper Candidate Preflight Decision Report\n\n"
        f"- decision: `{payload['decision']}`\n"
        f"- approved_for_no_order_to_paper_transition_preflight: `{payload['approved_for_no_order_to_paper_transition_preflight']}`\n"
        f"- approved_for_paper_transition_candidate: `{payload['approved_for_paper_transition_candidate']}`\n"
        f"- approved_for_paper_candidate: `{payload['approved_for_paper_candidate']}`\n"
        f"- approved_for_live_real: `{payload['approved_for_live_real']}`\n"
        f"- paper_live_order_blocked: `{payload['paper_live_order_blocked']}`\n",
        encoding="utf-8", newline="\n")
    print(f"{CONTRACT_VERSION} Paper Candidate Preflight {payload['decision']}")
    for key in ("read_only","approved_for_no_order_to_paper_transition_preflight","approved_for_paper_transition_candidate","approved_for_paper_candidate","approved_for_live_real","exchange_sandbox_isolated","capital_cap_verified","kill_switch_verified","operator_approval_required","operator_approval_verified","training_performed","reload_performed","trading_action_performed"):
        print(f" - {key}: {payload[key]}")
    print(f"report_json: {json_path}")
    print(f"report_md: {md_path}")
    return 0 if payload["ok"] else 2

if __name__ == "__main__":
    raise SystemExit(main())
