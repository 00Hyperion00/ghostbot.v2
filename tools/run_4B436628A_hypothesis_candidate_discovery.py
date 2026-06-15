from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradebot.hypothesis_candidate_discovery import (  # noqa: E402
    CONTRACT_VERSION,
    build_hypothesis_candidate_discovery_report,
    load_json,
    load_jsonl,
    write_report_bundle,
)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.28A no-order new hypothesis candidate discovery")
    parser.add_argument("--ledger-jsonl", required=True)
    parser.add_argument("--h3-diagnostics-json")
    parser.add_argument("--h4-sensitivity-json")
    parser.add_argument("--h5-closure-json")
    parser.add_argument("--operator-snapshot-json")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--review-ok", action="store_true", help="Required explicit operator acknowledgement for research-only report generation")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.review_ok:
        raise SystemExit("REVIEW_OK_REQUIRED_FOR_28A_RESEARCH_SELECTION_PACK")
    ledger_rows = load_jsonl(args.ledger_jsonl)
    payload = build_hypothesis_candidate_discovery_report(
        ledger_rows=ledger_rows,
        h3_diagnostics=load_json(args.h3_diagnostics_json) if args.h3_diagnostics_json else None,
        h4_sensitivity=load_json(args.h4_sensitivity_json) if args.h4_sensitivity_json else None,
        h5_closure=load_json(args.h5_closure_json) if args.h5_closure_json else None,
        operator_snapshot=load_json(args.operator_snapshot_json) if args.operator_snapshot_json else None,
        source_paths={
            "ledger_jsonl": str(Path(args.ledger_jsonl).resolve()),
            "h3_diagnostics_json": str(Path(args.h3_diagnostics_json).resolve()) if args.h3_diagnostics_json else None,
            "h4_sensitivity_json": str(Path(args.h4_sensitivity_json).resolve()) if args.h4_sensitivity_json else None,
            "h5_closure_json": str(Path(args.h5_closure_json).resolve()) if args.h5_closure_json else None,
            "operator_snapshot_json": str(Path(args.operator_snapshot_json).resolve()) if args.operator_snapshot_json else None,
        },
    )
    json_path, md_path = write_report_bundle(payload, args.out_dir)
    selected = payload.get("selected_research_candidate") or {}
    print(f"{CONTRACT_VERSION} new hypothesis candidate discovery {payload['decision']}")
    print(f" - read_only: {payload['read_only']}")
    print(f" - no_order_research_branch_selection_only: {payload['no_order_research_branch_selection_only']}")
    print(f" - failed_branch_closure_status: {payload['failed_branch_lessons']['closure_status']}")
    print(f" - selected_candidate_id: {selected.get('candidate_id')}")
    print(f" - selected_candidate_branch: {selected.get('branch_name')}")
    print(f" - selected_candidate_score: {selected.get('score')}")
    print(f" - candidate_spec_generation_required_next: {payload['candidate_spec_generation_required_next']}")
    print(f" - branch_state_mutation_performed: {payload['branch_state_mutation_performed']}")
    print(f" - strategy_parameter_mutation_performed: {payload['strategy_parameter_mutation_performed']}")
    print(f" - approved_for_shadow_collection: {payload['approved_for_shadow_collection']}")
    print(f" - approved_for_paper_candidate: {payload['approved_for_paper_candidate']}")
    print(f" - approved_for_live_real: {payload['approved_for_live_real']}")
    print(f"report_json: {json_path}")
    print(f"report_md: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
