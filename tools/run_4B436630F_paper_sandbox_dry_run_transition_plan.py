from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _repo_root() -> Path:
    start = Path.cwd().resolve()
    for item in [start, *start.parents]:
        if (item / "src" / "tradebot").is_dir():
            return item
    return start


def main() -> int:
    root = _repo_root()
    if str(root / "src") not in sys.path:
        sys.path.insert(0, str(root / "src"))
    from tradebot.config import Settings
    from tradebot.paper_sandbox_dry_run_transition_plan import build_from_latest_30e_ready_report, write_report_bundle

    parser = argparse.ArgumentParser()
    parser.add_argument("--reports-dir", default="reports/production_hardening")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    payload = build_from_latest_30e_ready_report(Settings(), args.reports_dir)
    json_path, md_path = write_report_bundle(payload, args.reports_dir)
    if args.once_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"4B.4.3.6.6.30F Paper Sandbox Dry-run Transition Plan {payload.get('decision')}")
        for key in (
            "read_only",
            "approved_for_paper_sandbox_dry_run_transition_plan",
            "approved_for_paper_sandbox_dry_run_execution_plan",
            "approved_for_order_path_simulation_envelope",
            "approved_for_operator_final_go_no_go_checklist",
            "approved_for_paper_sandbox_dry_run_execution",
            "approved_for_paper_transition_candidate",
            "approved_for_paper_candidate",
            "approved_for_live_real",
            "paper_order_enablement_still_blocked",
            "training_performed",
            "reload_performed",
            "trading_action_performed",
        ):
            print(f" - {key}: {payload.get(key)}")
        print(f"report_json: {json_path}")
        print(f"report_md: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
