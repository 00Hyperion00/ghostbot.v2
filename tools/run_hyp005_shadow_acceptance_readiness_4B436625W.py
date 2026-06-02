from __future__ import annotations

# CLI_MARKERS_25W: __ledger_json __ledger_jsonl __input_json __collection_report_json __reports_dir __include_all __strict_explicit_chain __review_ok paper_transition_ready paper_transition_readiness_only no_order_shadow_only
import argparse
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

HYP005_R1_STRICT_EXPLICIT_CHAIN_HOTFIX_VERSION = "4B.4.3.6.6.25AE-H3"

from tradebot.research_hyp005_shadow_acceptance_readiness import (  # noqa: E402
    HYP005_SHADOW_ACCEPTANCE_CONTRACT_VERSION,
    REPORT_PREFIX,
    SUMMARY_PREFIX,
    build_hyp005_shadow_acceptance_report,
    load_json,
    load_observations_from_paths,
    report_to_markdown,
    write_json,
)


def latest_report(reports_dir: Path, prefix: str) -> Path | None:
    matches = sorted(reports_dir.glob(f"{prefix}_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return matches[0] if matches else None



def _ensure_scoped_inputs(reports_dir: Path, paths: list[Path], *, label: str) -> None:
    scope = reports_dir.resolve()
    for path in paths:
        resolved = path.resolve()
        try:
            resolved.relative_to(scope)
        except ValueError as exc:
            raise SystemExit(f"{label} must remain inside scoped reports-dir: {resolved}") from exc


def discover_input_paths(args: argparse.Namespace) -> list[Path]:
    paths: list[Path] = []
    for raw in args.ledger_json or []:
        paths.append(Path(raw))
    for raw in args.ledger_jsonl or []:
        paths.append(Path(raw))
    for raw in args.input_json or []:
        paths.append(Path(raw))
    for raw in args.collection_report_json or []:
        paths.append(Path(raw))
    if args.include_all or not paths:
        reports_dir = Path(args.reports_dir)
        for prefix in (
            "4B436625V_hyp005_shadow_observation_logger",
            "4B436625V_hyp005_shadow_observation_ledger",
        ):
            path = latest_report(reports_dir, prefix)
            if path is not None and path not in paths:
                paths.append(path)
    return paths


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.25W HYP-005 shadow observation acceptance / paper-transition readiness gate")
    parser.add_argument("--ledger-json", action="append", default=None, help="25V shadow observation ledger JSON. Can be supplied multiple times.")
    parser.add_argument("--ledger-jsonl", action="append", default=None, help="25V shadow observation ledger JSONL. Can be supplied multiple times.")
    parser.add_argument("--input-json", action="append", default=None, help="25V report or ledger JSON. Can be supplied multiple times.")
    parser.add_argument("--collection-report-json", action="append", default=None, help="Explicit scoped 25X collection report JSON. Can be supplied multiple times.")
    parser.add_argument("--reports-dir", default="reports", help="Directory used to discover latest 25V report/ledger if explicit inputs are omitted.")
    parser.add_argument("--include-all", action="store_true", help="Compatibility flag; latest 25V report/ledger is selected from reports-dir.")
    parser.add_argument("--strict-explicit-chain", action="store_true", help="Require scoped explicit 25X collection report and merged ledger; disable discovery fallback.")
    parser.add_argument("--manual-reviewers", type=int, default=1, help="Number of manual reviewers attesting that this is readiness-only, not paper enablement.")
    parser.add_argument("--out-dir", default="reports")
    parser.add_argument("--review-ok", action="store_true", help="Required acknowledgement that 25W is readiness-only and does not start paper/live trading.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.review_ok:
        print("ERROR: --review-ok is required. 25W is readiness-only and cannot start paper/live trading.", file=sys.stderr)
        return 2
    input_paths = discover_input_paths(args)
    if args.strict_explicit_chain:
        collection_paths = [Path(raw) for raw in args.collection_report_json or []]
        ledger_paths = [Path(raw) for raw in (args.ledger_json or []) + (args.ledger_jsonl or [])]
        if not collection_paths or not ledger_paths:
            raise SystemExit("--strict-explicit-chain requires --collection-report-json and --ledger-json/--ledger-jsonl")
        _ensure_scoped_inputs(Path(args.reports_dir), collection_paths + ledger_paths, label="25W explicit input")
    observations, source_ledgers = load_observations_from_paths(input_paths)
    report = build_hyp005_shadow_acceptance_report(
        observations=observations,
        source_ledgers=source_ledgers,
        manual_reviewers=args.manual_reviewers,
    )
    report["input_paths"] = [str(path) for path in input_paths]
    report["collection_report_paths"] = [str(path) for path in (args.collection_report_json or [])]
    report["strict_explicit_chain"] = bool(args.strict_explicit_chain)
    out_dir = Path(args.out_dir)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = out_dir / f"{REPORT_PREFIX}_{stamp}.json"
    md_path = out_dir / f"{REPORT_PREFIX}_{stamp}.md"
    summary_path = out_dir / f"{SUMMARY_PREFIX}_{stamp}.json"
    write_json(json_path, report)
    write_json(summary_path, report.get("shadow_acceptance_summary", {}))
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(report_to_markdown(report), encoding="utf-8")
    summary = report.get("shadow_acceptance_summary") if isinstance(report.get("shadow_acceptance_summary"), dict) else {}
    print(f"{HYP005_SHADOW_ACCEPTANCE_CONTRACT_VERSION} HYP-005 shadow acceptance/readiness {report['decision']}")
    print(f" - source_ledgers: {len(source_ledgers)}")
    print(f" - hypothesis_id: {report.get('hypothesis_id')}")
    print(f" - branch_name: {report.get('branch_name')}")
    print(f" - selected_strategy_family: {report.get('selected_strategy_family')}")
    print(f" - shadow_observation_count: {summary.get('shadow_observation_count')}")
    print(f" - shadow_days_observed: {summary.get('shadow_days_observed')}")
    print(f" - shadow_mean_forward_edge_bps: {summary.get('shadow_mean_forward_edge_bps')}")
    print(f" - shadow_median_forward_edge_bps: {summary.get('shadow_median_forward_edge_bps')}")
    print(f" - shadow_profit_factor: {summary.get('shadow_profit_factor')}")
    print(f" - shadow_oos_edge_bps: {summary.get('shadow_oos_edge_bps')}")
    print(f" - shadow_walk_forward_positive_rate_pct: {summary.get('shadow_walk_forward_positive_rate_pct')}")
    print(f" - paper_transition_ready: {report.get('paper_transition_ready')}")
    print(f" - approved_for_paper_transition_candidate: {report.get('approved_for_paper_transition_candidate')}")
    print(f" - approved_for_training_candidate: {report.get('approved_for_training_candidate')}")
    print(f" - approved_for_paper_candidate: {report.get('approved_for_paper_candidate')}")
    print(f" - approved_for_live_real: {report.get('approved_for_live_real')}")
    print(f" - reason_codes: {report.get('reason_codes')}")
    print(f" - warnings: {report.get('warnings')}")
    print(f" - recommendation: {report.get('recommendation')}")
    print(f"report_json: {json_path}")
    print(f"report_md: {md_path}")
    print(f"summary_json: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
