from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tradebot.research_stop_evidence_pack import (
    REPORT_PREFIX,
    build_research_stop_evidence_pack,
    discover_report_paths,
    load_reports_from_paths,
    select_latest_report_per_phase,
    write_report_files,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="4B.4.3.6.6.24N research stop / no-edge evidence pack generator"
    )
    parser.add_argument("--reports-dir", default="reports", help="Directory containing prior 24A-24M JSON reports")
    parser.add_argument("--out-dir", default="reports", help="Directory where 24N reports will be written")
    parser.add_argument(
        "--input-json",
        action="append",
        default=[],
        help="Explicit source report JSON path. May be passed multiple times. If omitted, latest report per phase is discovered.",
    )
    parser.add_argument("--include-all", action="store_true", help="Include all discovered reports instead of latest report per phase")
    parser.add_argument("--review-ok", action="store_true", help="Required acknowledgement that this is an observation-only no-go report")
    return parser.parse_args(argv)


def resolve_source_paths(args: argparse.Namespace) -> list[Path]:
    if args.input_json:
        return [Path(item) for item in args.input_json]

    reports_dir = Path(args.reports_dir)
    discovered = discover_report_paths(reports_dir)
    if args.include_all:
        return discovered
    return list(select_latest_report_per_phase(discovered).values())


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.review_ok:
        print("ERROR: --review-ok is required. This tool is observation-only and must not be used to justify trading.", file=sys.stderr)
        return 2

    paths = resolve_source_paths(args)
    if not paths:
        print("ERROR: no source reports found. Provide --input-json or populate --reports-dir.", file=sys.stderr)
        return 2

    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        print(f"ERROR: missing source report(s): {missing}", file=sys.stderr)
        return 2

    loaded = load_reports_from_paths(paths)
    report = build_research_stop_evidence_pack(loaded)
    json_path, md_path = write_report_files(report, Path(args.out_dir))

    summary = report.get("summary", {})
    print(f"4B.4.3.6.6.24N research stop evidence pack {report['decision']}")
    print(f" - source_reports: {summary.get('source_report_count')}")
    print(f" - terminal_no_go_block_count: {summary.get('terminal_no_go_block_count')}")
    print(f" - approved_for_research_candidate: {report['approved_for_research_candidate']}")
    print(f" - approved_for_training_candidate: {report['approved_for_training_candidate']}")
    print(f" - approved_for_paper_candidate: {report['approved_for_paper_candidate']}")
    print(f" - approved_for_live_real: {report['approved_for_live_real']}")
    print(f" - reason_codes: {report['reason_codes']}")
    print(f" - recommendation: {report['recommendation']}")
    print(f"report_json: {json_path.as_posix()}")
    print(f"report_md: {md_path.as_posix()}")
    return 0 if report["decision"] == "RESEARCH_STOP_NO_GO" else 1


if __name__ == "__main__":
    raise SystemExit(main())
