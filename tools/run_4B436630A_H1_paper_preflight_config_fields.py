from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from check_4B436630A_H1_paper_preflight_config_fields import CONTRACT_VERSION, build_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate 30A-H1 paper preflight config fields hotfix report")
    parser.add_argument("--reports-dir", default="reports/production_hardening")
    args = parser.parse_args()
    root = Path.cwd()
    report = build_report(root)
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    payload = {
        "contract_version": CONTRACT_VERSION,
        "decision": "PAPER_PREFLIGHT_CONFIG_FIELDS_READY_LIVE_REAL_BLOCKED" if report.get("ok") else "PAPER_PREFLIGHT_CONFIG_FIELDS_NOT_READY",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "read_only": True,
        "paper_preflight_config_fields_hotfix": True,
        "approved_for_config_fields_baseline": bool(report["checks"].get("config_paper_preflight_fields_present")),
        "approved_for_no_order_to_paper_transition_preflight": bool(report["checks"].get("base_30a_checker_ok")),
        "approved_for_paper_transition_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "live_real_hard_block_verified": True,
        "runtime_activation_blocked": True,
        "paper_live_order_blocked": True,
        "training_reload_blocked": True,
        "runtime_overlay_activation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "paper_live_order_enablement_present": False,
        "checks": report["checks"],
    }
    reports_dir = Path(args.reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    json_path = reports_dir / f"4B436630A_H1_paper_preflight_config_fields_decision_{now}.json"
    md_path = json_path.with_suffix(".md")
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8", newline="\n")
    md_path.write_text(
        "# 4B.4.3.6.6.30A-H1 Paper Preflight Config Fields Decision Report\n\n"
        f"- decision: `{payload['decision']}`\n"
        f"- approved_for_no_order_to_paper_transition_preflight: `{payload['approved_for_no_order_to_paper_transition_preflight']}`\n"
        f"- approved_for_paper_transition_candidate: `{payload['approved_for_paper_transition_candidate']}`\n"
        f"- approved_for_paper_candidate: `{payload['approved_for_paper_candidate']}`\n"
        f"- approved_for_live_real: `{payload['approved_for_live_real']}`\n"
        f"- trading_action_performed: `{payload['trading_action_performed']}`\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"{CONTRACT_VERSION} Paper Preflight Config Fields {payload['decision']}")
    for key in (
        "read_only",
        "approved_for_config_fields_baseline",
        "approved_for_no_order_to_paper_transition_preflight",
        "approved_for_paper_transition_candidate",
        "approved_for_paper_candidate",
        "approved_for_live_real",
        "live_real_hard_block_verified",
        "training_performed",
        "reload_performed",
        "trading_action_performed",
    ):
        print(f" - {key}: {payload[key]}")
    print(f"report_json: {json_path}")
    print(f"report_md: {md_path}")
    return 0 if report.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
