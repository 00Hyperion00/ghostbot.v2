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
    from tradebot.paper_transition_approval_evidence_capture import (
        build_from_operator_inputs,
        write_report_bundle,
    )
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports-dir", default="reports/production_hardening")
    parser.add_argument("--operator-id", default="")
    parser.add_argument("--confirmation-token", default="")
    parser.add_argument("--freeze-token", default="")
    parser.add_argument("--issue-approval", action="store_true")
    parser.add_argument("--freeze-runtime-envelope", action="store_true")
    parser.add_argument("--verify-final-risk-cap", action="store_true")
    parser.add_argument("--ttl-sec", type=int, default=None)
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    payload = build_from_operator_inputs(
        operator_id=args.operator_id,
        confirmation_token=args.confirmation_token,
        freeze_token=args.freeze_token,
        issue_approval=args.issue_approval,
        freeze_runtime_envelope=args.freeze_runtime_envelope,
        verify_final_risk_cap=args.verify_final_risk_cap,
        reports_dir=args.reports_dir,
        ttl_sec=args.ttl_sec,
    )
    json_path, md_path = write_report_bundle(payload, args.reports_dir)
    if args.once_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"4B.4.3.6.6.30D Operator Approval Evidence Capture {payload.get('decision')}")
        for key in (
            "read_only",
            "approved_for_operator_approval_evidence_capture",
            "approved_for_paper_transition_candidate_review",
            "approved_for_paper_transition_candidate",
            "approved_for_paper_candidate",
            "approved_for_live_real",
            "typed_approval_evidence_verified",
            "ttl_bound_approval_snapshot_verified",
            "runtime_envelope_freeze_token_verified",
            "final_risk_cap_verification_evidence_verified",
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
