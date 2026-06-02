from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradebot.research_hyp005_symbol_risk_pruning_decision import (  # noqa: E402
    HYP005_SYMBOL_RISK_PRUNING_CONTRACT_VERSION,
    Hyp005SymbolRiskPruningLimits,
    build_hyp005_symbol_risk_pruning_decision_report,
    write_hyp005_symbol_risk_pruning_decision_report,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="4B.4.3.6.6.25AC HYP-005 symbol risk pruning / candidate continuation no-order decision gate."
    )
    parser.add_argument("--reports-dir", default="reports")
    parser.add_argument("--input-json", default=None, help="Optional latest 25AB-H2 quality audit JSON.")
    parser.add_argument("--out-dir", default="reports")
    parser.add_argument("--include-all", action="store_true", help="Read all available 25V ledgers and canonical-dedupe them.")
    parser.add_argument("--review-ok", action="store_true", help="Operator reviewed that this is a no-order decision gate only.")
    parser.add_argument("--max-slippage-proxy-bps", type=float, default=12.0)
    parser.add_argument("--max-true-missing-fields-pct", type=float, default=1.0)
    parser.add_argument("--min-unique-observations", type=int, default=30)
    parser.add_argument("--min-matured-observations", type=int, default=20)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    limits = Hyp005SymbolRiskPruningLimits(
        min_unique_observations=args.min_unique_observations,
        min_matured_observations=args.min_matured_observations,
        max_slippage_proxy_bps=args.max_slippage_proxy_bps,
        max_true_missing_fields_pct=args.max_true_missing_fields_pct,
    )
    report = build_hyp005_symbol_risk_pruning_decision_report(
        Path(args.reports_dir),
        input_json=Path(args.input_json) if args.input_json else None,
        include_all=bool(args.include_all),
        review_ok=bool(args.review_ok),
        limits=limits,
    )
    json_path, md_path = write_hyp005_symbol_risk_pruning_decision_report(report, Path(args.out_dir))
    baseline = report.get("baseline_scenario", {})
    selected = report.get("selected_scenario", {})
    dd = report.get("deduplication", {})
    print(f"{HYP005_SYMBOL_RISK_PRUNING_CONTRACT_VERSION} HYP-005 symbol risk pruning decision {report['decision']}")
    print(f" - canonical_unique_observation_count: {dd.get('unique_observation_count')}")
    print(f" - canonical_duplicate_removed_count: {dd.get('duplicate_removed_count')}")
    print(f" - baseline_matured_count: {baseline.get('matured_forward_return_count')}")
    print(f" - baseline_mean_forward_edge_bps: {baseline.get('mean_forward_edge_bps')}")
    print(f" - baseline_median_forward_edge_bps: {baseline.get('median_forward_edge_bps')}")
    print(f" - baseline_profit_factor: {baseline.get('profit_factor')}")
    print(f" - baseline_win_rate_pct: {baseline.get('win_rate_pct')}")
    print(f" - baseline_high_slippage_symbols: {','.join(baseline.get('high_slippage_symbols') or [])}")
    print(f" - selected_scenario: {selected.get('scenario_id')}")
    print(f" - recommended_pruned_symbols: {','.join(report.get('recommended_pruned_symbols') or [])}")
    print(f" - recommended_symbols_arg: {report.get('recommended_symbols_arg')}")
    print(f" - approved_for_scheduler_regeneration: {report.get('approved_for_scheduler_regeneration')}")
    print(f" - approved_for_paper_candidate: {report.get('approved_for_paper_candidate')}")
    print(f" - approved_for_live_real: {report.get('approved_for_live_real')}")
    print(f" - reason_codes: {report.get('reason_codes')}")
    print(f" - warnings: {report.get('warnings')}")
    print(f" - recommendation: {report.get('recommendation')}")
    print(f"report_json: {json_path}")
    print(f"report_md: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
