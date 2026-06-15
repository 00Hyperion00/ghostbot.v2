from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradebot.hyp006_candidate_spec_registration import (  # noqa: E402
    CONTRACT_VERSION,
    build_hyp006_registration_gate_report,
    load_json,
    write_report_bundle,
)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.28B HYP-006-R1 no-order candidate spec registration gate")
    parser.add_argument("--discovery-json", required=True, help="Latest 4B436628A discovery JSON")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--review-ok", action="store_true", help="Required explicit operator acknowledgement for draft generation")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.review_ok:
        raise SystemExit("REVIEW_OK_REQUIRED_FOR_28B_CANDIDATE_SPEC_DRAFT")
    discovery_path = Path(args.discovery_json).resolve()
    payload = build_hyp006_registration_gate_report(
        discovery_report=load_json(discovery_path),
        source_paths={"discovery_json": str(discovery_path)},
    )
    report_json, candidate_spec_json, report_md = write_report_bundle(payload, args.out_dir)
    print(f"{CONTRACT_VERSION} HYP-006-R1 candidate spec registration gate {payload['decision']}")
    print(f" - read_only: {payload['read_only']}")
    print(f" - no_order_candidate_spec_draft_only: {payload['no_order_candidate_spec_draft_only']}")
    print(f" - selected_candidate_id: {payload['selected_candidate_id']}")
    print(f" - candidate_spec_draft_ready: {payload['candidate_spec_draft_ready']}")
    print(f" - no_order_shadow_registration_gate_ready: {payload['no_order_shadow_registration_gate_ready']}")
    print(f" - approved_for_no_order_shadow_registration_candidate: {payload['approved_for_no_order_shadow_registration_candidate']}")
    print(f" - approved_for_shadow_collection: {payload['approved_for_shadow_collection']}")
    print(f" - approved_for_paper_candidate: {payload['approved_for_paper_candidate']}")
    print(f" - approved_for_live_real: {payload['approved_for_live_real']}")
    print(f" - next_required_gate: {payload['next_required_gate']}")
    print(f" - strategy_parameter_mutation_performed: {payload['strategy_parameter_mutation_performed']}")
    print(f" - scheduler_mutation_performed: {payload['scheduler_mutation_performed']}")
    print(f"report_json: {report_json}")
    print(f"candidate_spec_json: {candidate_spec_json}")
    print(f"report_md: {report_md}")
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
