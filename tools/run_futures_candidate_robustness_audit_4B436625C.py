from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradebot.futures_candidate_robustness_audit import (  # noqa: E402
    FUTURES_CANDIDATE_ROBUSTNESS_CONTRACT_VERSION,
    build_futures_candidate_robustness_audit,
    discover_25b_reports,
    load_json_reports,
    write_report_files,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.25C futures candidate robustness / data coverage audit")
    parser.add_argument("--input-json", action="append", default=[], help="Explicit 25B report JSON. Can be passed more than once.")
    parser.add_argument("--reports-dir", default=None, help="Directory to auto-discover 25B JSON reports.")
    parser.add_argument("--out-dir", default="reports", help="Output report directory.")
    parser.add_argument("--include-all", action="store_true", help="Use all discovered 25B reports instead of latest few.")
    parser.add_argument("--review-ok", action="store_true", help="Required acknowledgement that this audit is observation-only.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.review_ok:
        raise SystemExit("Refusing to run without --review-ok; this is an observation-only research audit.")
    paths = [Path(p) for p in args.input_json]
    if args.reports_dir:
        discovered = discover_25b_reports(args.reports_dir)
        if not args.include_all and discovered:
            discovered = discovered[-4:]
        paths.extend(discovered)
    # Deduplicate while preserving order.
    deduped: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        resolved = str(path)
        if resolved not in seen:
            seen.add(resolved)
            deduped.append(path)
    reports = load_json_reports(deduped)
    report = build_futures_candidate_robustness_audit(reports)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path, md_path = write_report_files(report, args.out_dir, timestamp)
    print(f"{FUTURES_CANDIDATE_ROBUSTNESS_CONTRACT_VERSION} futures candidate robustness audit {report.decision}")
    print(f" - source_reports: {report.source_reports}")
    print(f" - candidates: {report.candidate_count}")
    print(f" - approved_for_research_candidate: {report.approved_for_research_candidate}")
    print(f" - approved_for_training_candidate: {report.approved_for_training_candidate}")
    print(f" - approved_for_paper_candidate: {report.approved_for_paper_candidate}")
    print(f" - approved_for_live_real: {report.approved_for_live_real}")
    print(f" - selected: {report.selected_symbol} {report.selected_interval} {report.selected_strategy}")
    print(f" - selected_mean_net_edge_bps: {report.selected_mean_net_edge_bps}")
    print(f" - selected_profit_factor: {report.selected_profit_factor}")
    print(f" - selected_signal_count: {report.selected_signal_count}")
    print(f" - reason_codes: {report.reason_codes}")
    print(f" - recommendation: {report.recommendation}")
    print(f"report_json: {json_path}")
    print(f"report_md: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
