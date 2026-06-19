from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from check_4B436629E_H1_production_readiness_evidence_refresh import CONTRACT_VERSION, build_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate 4B.4.3.6.6.29E-H1 evidence refresh decision report")
    parser.add_argument("--reports-dir", default="reports/production_hardening")
    args = parser.parse_args()
    root = Path.cwd()
    report = build_report(root)
    snapshot = dict(report.get("snapshot") or {})
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    payload = {
        "ok": bool(report.get("ok")),
        "contract_version": CONTRACT_VERSION,
        "decision": "PRODUCTION_READINESS_EVIDENCE_REFRESH_READY_LIVE_REAL_STILL_BLOCKED" if report.get("ok") else "PRODUCTION_READINESS_EVIDENCE_REFRESH_NOT_READY",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "read_only": True,
        "production_readiness_evidence_refresh": True,
        "evidence_complete": bool(snapshot.get("evidence_complete", False)),
        "approved_for_evidence_merge_baseline": bool(snapshot.get("approved_for_evidence_merge_baseline", False)),
        "approved_for_paper_candidate_preflight": bool(snapshot.get("approved_for_paper_candidate_preflight", False)),
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "live_real_hard_block_verified": bool(snapshot.get("live_real_hard_block_verified", True)),
        "approved_for_runtime_overlay_activation_candidate": False,
        "approved_for_parameter_relaxation_candidate": False,
        "runtime_activation_blocked": True,
        "paper_live_order_blocked": True,
        "training_reload_blocked": True,
        "runtime_overlay_activation_performed": False,
        "scheduler_mutation_performed": False,
        "strategy_parameter_mutation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "paper_live_order_enablement_present": False,
        "checks": report.get("checks", {}),
        "snapshot": snapshot,
    }
    reports_dir = Path(args.reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    json_path = reports_dir / f"4B436629E_H1_production_readiness_evidence_refresh_decision_{now}.json"
    md_path = json_path.with_suffix(".md")
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8", newline="\n")
    md_path.write_text(
        "# 4B.4.3.6.6.29E-H1 Production Readiness Evidence Refresh\n\n"
        f"- decision: `{payload['decision']}`\n"
        f"- evidence_complete: `{payload['evidence_complete']}`\n"
        f"- approved_for_paper_candidate_preflight: `{payload['approved_for_paper_candidate_preflight']}`\n"
        f"- approved_for_paper_candidate: `{payload['approved_for_paper_candidate']}`\n"
        f"- approved_for_live_real: `{payload['approved_for_live_real']}`\n"
        f"- live_real_hard_block_verified: `{payload['live_real_hard_block_verified']}`\n"
        f"- trading_action_performed: `{payload['trading_action_performed']}`\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"{CONTRACT_VERSION} Production Readiness Evidence Refresh {payload['decision']}")
    for key in (
        "read_only",
        "evidence_complete",
        "approved_for_evidence_merge_baseline",
        "approved_for_paper_candidate_preflight",
        "approved_for_paper_candidate",
        "approved_for_live_real",
        "live_real_hard_block_verified",
        "approved_for_runtime_overlay_activation_candidate",
        "approved_for_parameter_relaxation_candidate",
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
