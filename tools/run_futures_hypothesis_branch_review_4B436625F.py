from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradebot.futures_hypothesis_branch_review import (  # noqa: E402
    REPORT_PREFIX,
    build_futures_hypothesis_branch_review,
    load_json_report,
    write_report_json,
    write_report_markdown,
)


def _phase_from_name(path: Path) -> str:
    name = path.name.upper()
    for phase in ("25B", "25C", "25D", "25E"):
        if phase in name or f"4366{phase}" in name:
            return phase
    return "UNKNOWN"


def collect_report_paths(reports_dir: Path, include_all: bool) -> list[Path]:
    if not reports_dir.exists():
        return []
    patterns = [
        "4B436625B_futures_funding_open_interest_edge_exploration_*.json",
        "4B436625C_futures_candidate_robustness_audit_*.json",
        "4B436625D_futures_research_candidate_simulator_*.json",
        "4B436625E_futures_candidate_refinement_median_edge_recovery_*.json",
    ]
    paths: list[Path] = []
    for pattern in patterns:
        paths.extend(reports_dir.glob(pattern))
    paths = sorted(set(paths), key=lambda p: p.stat().st_mtime)
    if include_all:
        return paths
    latest_by_phase: dict[str, Path] = {}
    for path in paths:
        latest_by_phase[_phase_from_name(path)] = path
    return [latest_by_phase[key] for key in ("25B", "25C", "25D", "25E") if key in latest_by_phase]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.25F futures hypothesis branch review / closure decision")
    parser.add_argument("--input-json", action="append", default=[], help="Explicit 25B/25C/25D/25E JSON report path. May be repeated.")
    parser.add_argument("--reports-dir", default="reports", help="Directory to scan for latest 25B/25C/25D/25E reports.")
    parser.add_argument("--include-all", action="store_true", help="Use all matching reports in --reports-dir instead of latest per phase.")
    parser.add_argument("--out-dir", default="reports", help="Output report directory.")
    parser.add_argument("--primary-symbol", default="BTCUSDT", help="Primary branch symbol, default BTCUSDT.")
    parser.add_argument("--companion-symbols", default="ETHUSDT", help="Comma-separated companion symbols, default ETHUSDT.")
    parser.add_argument("--interval", default="4h", help="Branch interval, default 4h.")
    parser.add_argument("--strategy", default="funding_trend_exhaustion", help="Branch strategy, default funding_trend_exhaustion.")
    parser.add_argument("--review-ok", action="store_true", help="Required acknowledgement that this is research-only and no orders/reload/config mutation are performed.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.review_ok:
        print("ERROR: --review-ok is required. This tool is research-only and does not grant training/paper/live permission.", file=sys.stderr)
        return 2

    explicit_paths = [Path(path) for path in args.input_json]
    report_paths = explicit_paths if explicit_paths else collect_report_paths(Path(args.reports_dir), args.include_all)
    if not report_paths:
        print("ERROR: no input reports found. Provide --input-json or place 25B/25C/25D/25E reports in --reports-dir.", file=sys.stderr)
        return 2

    reports = []
    source_names = []
    for path in report_paths:
        reports.append(load_json_report(path))
        source_names.append(str(path))

    companion_symbols = tuple(symbol.strip().upper() for symbol in args.companion_symbols.split(",") if symbol.strip())
    report = build_futures_hypothesis_branch_review(
        reports,
        source_names=source_names,
        primary_symbol=args.primary_symbol.upper(),
        companion_symbols=companion_symbols,
        interval=args.interval,
        strategy=args.strategy,
    )

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.out_dir)
    json_path = out_dir / f"{REPORT_PREFIX}_{ts}.json"
    md_path = out_dir / f"{REPORT_PREFIX}_{ts}.md"
    write_report_json(report, json_path)
    write_report_markdown(report, md_path)

    print(f"4B.4.3.6.6.25F futures hypothesis branch review {report.decision}")
    print(f" - source_reports: {report.source_reports}")
    print(f" - primary: {report.primary_symbol} {report.interval} {report.strategy}")
    print(f" - companion_symbols: {','.join(report.companion_symbols)}")
    print(f" - approved_for_research_candidate: {report.approved_for_research_candidate}")
    print(f" - approved_for_training_candidate: {report.approved_for_training_candidate}")
    print(f" - approved_for_paper_candidate: {report.approved_for_paper_candidate}")
    print(f" - approved_for_live_real: {report.approved_for_live_real}")
    if report.primary_summary is not None:
        print(f" - primary_latest: {report.primary_summary.latest_decision} phase={report.primary_summary.best_phase} signals={report.primary_summary.best_signal_count}")
    if report.combined_summary is not None:
        print(f" - combined_signals: {report.combined_summary.signal_count}")
        print(f" - dry_run_or_refinement_confirmed_count: {report.combined_summary.dry_run_or_refinement_confirmed_count}")
    print(f" - reason_codes: {list(report.reason_codes)}")
    print(f" - recommendation: {report.recommendation}")
    print(f"report_json: {json_path}")
    print(f"report_md: {md_path}")
    return 0 if report.decision in {"BRANCH_RESEARCH_CONTINUE", "BRANCH_REVIEW_PENDING_COMPANION_AUDIT", "BRANCH_CLOSED_NO_GO", "BRANCH_REVIEW_INCONCLUSIVE"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
