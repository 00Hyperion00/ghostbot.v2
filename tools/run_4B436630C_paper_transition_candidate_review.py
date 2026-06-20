from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path

from tradebot.config import Settings
from tradebot.paper_transition_candidate_review import (
    CONTRACT_VERSION,
    build_from_latest_report,
    write_report_bundle,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run 4B.4.3.6.6.30C paper transition candidate review.")
    parser.add_argument("--reports-dir", default="reports/production_hardening")
    parser.add_argument("--freeze-token", default=None)
    parser.add_argument("--operator-freeze", action="store_true", help="Mark sandbox runtime envelope as operator-frozen for this review run.")
    parser.add_argument("--final-risk-cap-verified", action="store_true", help="Mark final paper risk cap verification as operator-verified for this review run.")
    args = parser.parse_args()

    settings = Settings()
    if args.operator_freeze:
        settings = replace(settings, paper_transition_runtime_envelope_frozen=True)
    if args.freeze_token:
        settings = replace(settings, paper_transition_runtime_envelope_freeze_token=str(args.freeze_token))
    if args.final_risk_cap_verified:
        settings = replace(settings, paper_transition_final_risk_cap_verified=True)

    payload = build_from_latest_report(settings, args.reports_dir, supplied_freeze_token=args.freeze_token)
    json_path, md_path = write_report_bundle(payload, args.reports_dir)

    print(f"{CONTRACT_VERSION} Paper Transition Candidate Review {payload.get('decision')}")
    for key in (
        "read_only",
        "approved_for_paper_transition_candidate_review",
        "approved_for_paper_transition_candidate",
        "approved_for_paper_candidate",
        "approved_for_live_real",
        "operator_approval_evidence_verified",
        "sandbox_runtime_envelope_frozen",
        "paper_risk_cap_final_verified",
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
