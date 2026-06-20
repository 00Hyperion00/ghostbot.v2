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
    from tradebot.paper_transition_review_rerun import (
        build_from_latest_30d_ready_report,
        build_paper_transition_review_rerun_snapshot,
        load_json,
        write_report_bundle,
    )
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports-dir", default="reports/production_hardening")
    parser.add_argument("--source-30d-report", default="")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    if args.source_30d_report:
        source_path = Path(args.source_30d_report)
        payload = build_paper_transition_review_rerun_snapshot(
            load_json(source_path),
            source_report_path=source_path.as_posix(),
        )
    else:
        payload = build_from_latest_30d_ready_report(args.reports_dir)
    json_path, md_path = write_report_bundle(payload, args.reports_dir)
    if args.once_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"4B.4.3.6.6.30E Paper Transition Review Re-run {payload.get('decision')}")
        for key in (
            "read_only",
            "approved_for_paper_transition_review_rerun",
            "approved_for_paper_transition_candidate_review",
            "approved_for_paper_transition_candidate",
            "approved_for_paper_candidate",
            "approved_for_live_real",
            "source_30d_ready_evidence_verified",
            "source_30c_review_rerun_verified",
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
