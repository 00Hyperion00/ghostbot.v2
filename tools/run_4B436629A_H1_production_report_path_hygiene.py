from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from check_4B436629A_H1_production_report_path_hygiene import CONTRACT_VERSION, build_report

CANONICAL_REPORTS_DIR = Path("reports") / "production_hardening"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate 4B.4.3.6.6.29A-H1 report path hygiene decision report")
    parser.add_argument("--reports-dir", default=CANONICAL_REPORTS_DIR.as_posix())
    args = parser.parse_args()
    root = Path.cwd()
    reports_dir = Path(args.reports_dir)
    resolved = reports_dir.resolve() if reports_dir.is_absolute() else (root / reports_dir).resolve()
    canonical = (root / CANONICAL_REPORTS_DIR).resolve()
    if resolved != canonical:
        raise SystemExit("REPORTS_DIR_NOT_CANONICAL_PRODUCTION_HARDENING")
    report = build_report(root)
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    payload = {
        "ok": bool(report.get("ok")),
        "contract_version": CONTRACT_VERSION,
        "decision": "PRODUCTION_REPORT_PATH_HYGIENE_READY" if report.get("ok") else "PRODUCTION_REPORT_PATH_HYGIENE_NOT_READY",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "read_only": True,
        "report_path_hygiene_hotfix": True,
        "bad_report_path_removed": bool(report["checks"].get("bad_report_path_not_tracked")) and bool(report["checks"].get("bad_report_path_removed_from_worktree")),
        "canonical_production_hardening_report_preserved": bool(report["checks"].get("canonical_production_hardening_report_preserved")),
        "run_tool_canonical_guard_present": bool(report["checks"].get("run_tool_canonical_guard_present")),
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
        "recommendation": "Keep only canonical reports/production_hardening evidence. Reject typo/shell-contaminated production hardening report paths fail-closed.",
    }
    reports_dir.mkdir(parents=True, exist_ok=True)
    json_path = reports_dir / f"4B436629A_H1_production_report_path_hygiene_decision_{now}.json"
    md_path = json_path.with_suffix(".md")
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8", newline="\n")
    md_path.write_text(
        "# 4B.4.3.6.6.29A-H1 Production Report Path Hygiene Decision Report\n\n"
        f"- decision: `{payload['decision']}`\n"
        f"- bad_report_path_removed: `{payload['bad_report_path_removed']}`\n"
        f"- canonical_production_hardening_report_preserved: `{payload['canonical_production_hardening_report_preserved']}`\n"
        f"- approved_for_live_real: `{payload['approved_for_live_real']}`\n"
        f"- trading_action_performed: `{payload['trading_action_performed']}`\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"{CONTRACT_VERSION} Production report path hygiene {payload['decision']}")
    for key in (
        "read_only",
        "bad_report_path_removed",
        "canonical_production_hardening_report_preserved",
        "run_tool_canonical_guard_present",
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
