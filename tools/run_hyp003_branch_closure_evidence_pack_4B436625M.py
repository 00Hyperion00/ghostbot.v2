from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradebot.research_hyp003_branch_closure_evidence_pack import (  # noqa: E402
    HYP003_BRANCH_CLOSURE_CONTRACT_VERSION,
    build_hyp003_branch_closure_evidence_pack,
    load_json_report,
    write_report_bundle,
)


def _phase_from_name(path: Path) -> str:
    upper = path.name.upper()
    for phase in ("25J", "25K", "25L"):
        if phase in upper or f"4B4366{phase}" in upper:
            return phase
    return "UNKNOWN"


def discover_reports(reports_dir: Path, include_all: bool = False) -> list[Path]:
    if not reports_dir.exists():
        return []
    patterns = [
        "4B436625J_hyp003_regime_strategy_exploration_*.json",
        "4B436625K_hyp003_robustness_walkforward_confirmation_*.json",
        "4B436625L_hyp003_candidate_refinement_branch_decision_*.json",
    ]
    paths: list[Path] = []
    if include_all:
        for pattern in patterns:
            paths.extend(reports_dir.glob(pattern))
        return sorted(set(paths), key=lambda item: item.stat().st_mtime)

    latest_by_phase: dict[str, Path] = {}
    for pattern in patterns:
        for path in sorted(reports_dir.glob(pattern), key=lambda item: item.stat().st_mtime):
            latest_by_phase[_phase_from_name(path)] = path
    return [latest_by_phase[phase] for phase in ("25J", "25K", "25L") if phase in latest_by_phase]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.25M HYP-003 branch closure evidence pack")
    parser.add_argument("--input-json", action="append", default=[], help="Explicit 25J/25K/25L report JSON path. Can be repeated.")
    parser.add_argument("--reports-dir", default=None, help="Reports directory for automatic discovery.")
    parser.add_argument("--include-all", action="store_true", help="Include all matching reports instead of latest per phase.")
    parser.add_argument("--out-dir", default="reports")
    parser.add_argument("--hypothesis-id", default="HYP-003")
    parser.add_argument("--branch-name", default="regime_specific_strategy_family")
    parser.add_argument("--review-ok", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.review_ok:
        print("ERROR: --review-ok is required. This closure pack is observation-only and does not approve training/paper/live.", file=sys.stderr)
        return 2

    paths = [Path(item) for item in args.input_json]
    if args.reports_dir:
        paths.extend(discover_reports(Path(args.reports_dir), include_all=args.include_all))
    if not paths:
        print("ERROR: provide --input-json or --reports-dir", file=sys.stderr)
        return 2

    # Stable de-dup while preserving order.
    seen: set[Path] = set()
    unique_paths: list[Path] = []
    for path in paths:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique_paths.append(path)

    reports = [load_json_report(path) for path in unique_paths]
    report = build_hyp003_branch_closure_evidence_pack(
        reports,
        source_names=[str(path) for path in unique_paths],
        hypothesis_id=args.hypothesis_id,
        branch_name=args.branch_name,
    )
    report_json, report_md, snapshot_json = write_report_bundle(report, args.out_dir)

    selected = report.selected_candidate.key if report.selected_candidate else "UNKNOWN"
    print(f"{HYP003_BRANCH_CLOSURE_CONTRACT_VERSION} HYP-003 branch closure evidence pack {report.decision}")
    print(f" - source_reports: {report.source_reports}")
    print(f" - hypothesis_id: {report.hypothesis_id}")
    print(f" - branch_name: {report.branch_name}")
    print(f" - selected_candidate: {selected}")
    print(f" - final_25j_decision: {report.final_25j_decision}")
    print(f" - final_25k_decision: {report.final_25k_decision}")
    print(f" - final_25l_decision: {report.final_25l_decision}")
    print(f" - no_alternate_candidate_confirmed: {report.no_alternate_candidate_confirmed}")
    print(f" - approved_for_research_candidate: {report.approved_for_research_candidate}")
    print(f" - approved_for_training_candidate: {report.approved_for_training_candidate}")
    print(f" - approved_for_paper_candidate: {report.approved_for_paper_candidate}")
    print(f" - approved_for_live_real: {report.approved_for_live_real}")
    print(f" - reason_codes: {list(report.reason_codes)}")
    print(f" - recommendation: {report.recommendation}")
    print(f"report_json: {report_json}")
    print(f"report_md: {report_md}")
    print(f"registry_snapshot_json: {snapshot_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
