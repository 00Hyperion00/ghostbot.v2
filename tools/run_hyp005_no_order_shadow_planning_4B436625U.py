from __future__ import annotations

# CLI_MARKERS_25U: __input_json __reports_dir __include_all __review_ok candidate_spec_json no_order_shadow_only
import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradebot.research_hyp005_no_order_shadow_planning import (  # noqa: E402
    HYP005_SHADOW_PLANNING_CONTRACT_VERSION,
    REPORT_PREFIX,
    SPEC_PREFIX,
    build_hyp005_no_order_shadow_planning_report,
    load_json,
    report_to_markdown,
    write_json,
)


def latest_report(reports_dir: Path, prefix: str) -> Path | None:
    matches = sorted(reports_dir.glob(f"{prefix}_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return matches[0] if matches else None


def resolve_inputs(input_jsons: list[str] | None, reports_dir: Path) -> tuple[dict[str, Any] | None, dict[str, Any] | None, list[str]]:
    loaded: list[tuple[str, dict[str, Any]]] = []
    for item in input_jsons or []:
        path = Path(item)
        payload = load_json(path)
        if isinstance(payload, dict):
            payload.setdefault("source_report", str(path))
            loaded.append((str(path), payload))
    if not loaded:
        for prefix in (
            "4B436625S_hyp005_liquidity_sweep_reversal_exploration",
            "4B436625T_hyp005_robustness_walkforward_confirmation",
        ):
            path = latest_report(reports_dir, prefix)
            payload = load_json(path) if path else None
            if isinstance(payload, dict):
                payload.setdefault("source_report", str(path))
                loaded.append((str(path), payload))
    exploration = next((payload for _, payload in loaded if payload.get("decision") == "HYP005_EXPLORATION_PASS"), None)
    robustness = next((payload for _, payload in loaded if payload.get("decision") == "HYP005_ROBUSTNESS_PASS"), None)
    return exploration, robustness, [path for path, _ in loaded]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.25U HYP-005 no-order shadow planning / candidate spec gate")
    parser.add_argument("--input-json", action="append", default=None, help="25S and/or 25T JSON report. Pass twice for explicit chain.")
    parser.add_argument("--reports-dir", default="reports", help="Directory used to discover latest 25S/25T reports if --input-json omitted.")
    parser.add_argument("--include-all", action="store_true", help="Compatibility flag; latest 25S/25T are selected from reports-dir.")
    parser.add_argument("--out-dir", default="reports")
    parser.add_argument("--review-ok", action="store_true", help="Required acknowledgement that this is no-order shadow planning only.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.review_ok:
        print("ERROR: --review-ok is required. 25U is no-order shadow planning only and cannot approve paper/live trading.", file=sys.stderr)
        return 2
    exploration, robustness, source_paths = resolve_inputs(args.input_json, Path(args.reports_dir))
    report = build_hyp005_no_order_shadow_planning_report(
        exploration_report=exploration,
        robustness_report=robustness,
    )
    report["source_reports"] = source_paths
    out_dir = Path(args.out_dir)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = out_dir / f"{REPORT_PREFIX}_{stamp}.json"
    md_path = out_dir / f"{REPORT_PREFIX}_{stamp}.md"
    spec_path = out_dir / f"{SPEC_PREFIX}_{stamp}.json"
    write_json(json_path, report)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(report_to_markdown(report), encoding="utf-8")
    spec_payload = report.get("candidate_spec")
    spec_written = False
    if isinstance(spec_payload, dict):
        write_json(spec_path, spec_payload)
        report["candidate_spec_json"] = str(spec_path)
        # Re-write report with the spec reference included.
        write_json(json_path, report)
        spec_written = True
    metrics = report.get("observed_robustness_metrics") if isinstance(report.get("observed_robustness_metrics"), dict) else {}
    print(f"{HYP005_SHADOW_PLANNING_CONTRACT_VERSION} HYP-005 no-order shadow planning {report['decision']}")
    print(f" - source_reports: {len(source_paths)}")
    print(f" - hypothesis_id: {report.get('hypothesis_id')}")
    print(f" - branch_name: {report.get('branch_name')}")
    print(f" - selected_strategy_family: {report.get('selected_strategy_family')}")
    print(f" - shadow_plan_ready: {report.get('shadow_plan_ready')}")
    print(f" - no_order_shadow_only: {report.get('no_order_shadow_only')}")
    print(f" - shadow_min_samples: {report.get('shadow_min_samples')}")
    print(f" - observed_signal_count: {metrics.get('signal_count')}")
    print(f" - observed_penalized_mean_net_edge_bps: {metrics.get('penalized_mean_net_edge_bps')}")
    print(f" - approved_for_research_candidate: {report.get('approved_for_research_candidate')}")
    print(f" - approved_for_shadow_candidate: {report.get('approved_for_shadow_candidate')}")
    print(f" - approved_for_training_candidate: {report.get('approved_for_training_candidate')}")
    print(f" - approved_for_paper_candidate: {report.get('approved_for_paper_candidate')}")
    print(f" - approved_for_live_real: {report.get('approved_for_live_real')}")
    print(f" - reason_codes: {report.get('reason_codes')}")
    print(f" - warnings: {report.get('warnings')}")
    print(f" - recommendation: {report.get('recommendation')}")
    print(f"report_json: {json_path}")
    print(f"report_md: {md_path}")
    if spec_written:
        print(f"candidate_spec_json: {spec_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
