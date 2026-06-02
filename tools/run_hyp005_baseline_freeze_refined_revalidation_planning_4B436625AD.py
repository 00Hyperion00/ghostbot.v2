from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradebot.research_hyp005_baseline_freeze_refined_revalidation_planning import (  # noqa: E402
    HYP005_BASELINE_FREEZE_REVALIDATION_PLANNING_CONTRACT_VERSION,
    Hyp005RefinedCandidateRevalidationPlanningLimits,
    build_hyp005_baseline_freeze_refined_revalidation_planning_report,
    write_hyp005_baseline_freeze_refined_revalidation_planning_artifacts,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="4B.4.3.6.6.25AD HYP-005 baseline evidence freeze / refined candidate revalidation planning no-order gate."
    )
    parser.add_argument("--reports-dir", default="reports")
    parser.add_argument("--input-json", default=None, help="Optional explicit 25AC report JSON.")
    parser.add_argument("--out-dir", default="reports")
    parser.add_argument("--revalidation-sample-target", type=int, default=30)
    parser.add_argument("--review-ok", action="store_true", help="Operator reviewed that this gate is planning-only and no-order.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    limits = Hyp005RefinedCandidateRevalidationPlanningLimits(
        revalidation_sample_target=args.revalidation_sample_target,
    )
    report = build_hyp005_baseline_freeze_refined_revalidation_planning_report(
        Path(args.reports_dir),
        input_json=Path(args.input_json) if args.input_json else None,
        review_ok=bool(args.review_ok),
        limits=limits,
    )
    artifacts = write_hyp005_baseline_freeze_refined_revalidation_planning_artifacts(report, Path(args.out_dir))
    spec = report.get("refined_candidate_spec") or {}
    print(f"{HYP005_BASELINE_FREEZE_REVALIDATION_PLANNING_CONTRACT_VERSION} HYP-005 baseline freeze / refined revalidation planning {report['decision']}")
    print(f" - source_25ac_decision: {report.get('source_25ac_decision')}")
    print(f" - baseline_evidence_frozen: {report.get('baseline_evidence_frozen')}")
    print(f" - refined_branch_id: {report.get('refined_branch_id')}")
    print(f" - fresh_ledger_namespace: {report.get('fresh_ledger_namespace')}")
    print(f" - starting_unique_shadow_observation_count: {report.get('starting_unique_shadow_observation_count')}")
    print(f" - shadow_sample_target: {spec.get('shadow_sample_target')}")
    print(f" - recommended_pruned_symbols: {','.join(report.get('recommended_pruned_symbols') or [])}")
    print(f" - recommended_refined_symbols_arg: {report.get('recommended_refined_symbols_arg')}")
    print(f" - approved_for_next_scheduler_pack_patch: {report.get('approved_for_next_scheduler_pack_patch')}")
    print(f" - approved_for_scheduler_regeneration: {report.get('approved_for_scheduler_regeneration')}")
    print(f" - approved_for_paper_candidate: {report.get('approved_for_paper_candidate')}")
    print(f" - approved_for_live_real: {report.get('approved_for_live_real')}")
    print(f" - reason_codes: {report.get('reason_codes')}")
    print(f" - blockers: {report.get('blockers')}")
    print(f" - recommendation: {report.get('recommendation')}")
    for name, path in artifacts.items():
        print(f"{name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
