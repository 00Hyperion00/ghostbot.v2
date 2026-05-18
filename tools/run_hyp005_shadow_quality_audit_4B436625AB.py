from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradebot.research_hyp005_shadow_quality_audit import (  # noqa: E402
    HYP005_SHADOW_QUALITY_CONTRACT_VERSION,
    HYP005_SHADOW_QUALITY_HOTFIX_VERSION,
    Hyp005ShadowQualityLimits,
    build_hyp005_shadow_quality_audit_report,
    write_hyp005_shadow_quality_audit_report,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="4B.4.3.6.6.25AB-H2 HYP-005 shadow quality audit recommendation message consistency hotfix."
    )
    parser.add_argument("--reports-dir", default="reports")
    parser.add_argument("--out-dir", default="reports")
    parser.add_argument("--include-all", action="store_true", help="Read all available 25V ledgers instead of latest only.")
    parser.add_argument("--review-ok", action="store_true", help="Operator reviewed that this is no-order audit only.")
    parser.add_argument("--max-slippage-proxy-bps", type=float, default=12.0)
    parser.add_argument("--max-symbol-dominance-pct", type=float, default=50.0)
    parser.add_argument("--max-true-missing-fields-pct", type=float, default=1.0)
    parser.add_argument("--max-maturity-pending-pct-for-ready", type=float, default=35.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    limits = Hyp005ShadowQualityLimits(
        max_slippage_proxy_bps=args.max_slippage_proxy_bps,
        max_symbol_dominance_pct=args.max_symbol_dominance_pct,
        max_true_missing_fields_pct=args.max_true_missing_fields_pct,
        max_maturity_pending_pct_for_ready=args.max_maturity_pending_pct_for_ready,
    )
    report = build_hyp005_shadow_quality_audit_report(
        Path(args.reports_dir),
        include_all=bool(args.include_all),
        limits=limits,
        review_ok=bool(args.review_ok),
    )
    json_path, md_path = write_hyp005_shadow_quality_audit_report(report, Path(args.out_dir))
    qs = report.get("quality_summary", {})
    dd = report.get("deduplication", {})
    print(f"{HYP005_SHADOW_QUALITY_CONTRACT_VERSION} HYP-005 shadow quality/slippage audit {report['decision']}")
    print(f" - hotfix_version: {HYP005_SHADOW_QUALITY_HOTFIX_VERSION}")
    print(" - backward_compatible_report_globs: 25AB-H1,25AB")
    print(f" - raw_observation_count: {dd.get('raw_observation_count')}")
    print(f" - unique_observation_count: {dd.get('unique_observation_count')}")
    print(f" - duplicate_removed_count: {dd.get('duplicate_removed_count')}")
    print(f" - shadow_observation_count: {qs.get('shadow_observation_count')}")
    print(f" - shadow_sample_target: {qs.get('shadow_sample_target')}")
    print(f" - progress_pct: {qs.get('progress_pct')}")
    print(f" - matured_forward_return_count: {qs.get('matured_forward_return_count')}")
    print(f" - maturity_pending_count: {qs.get('maturity_pending_count')}")
    print(f" - true_missing_required_fields_pct: {qs.get('true_missing_required_fields_pct')}")
    print(f" - symbols_observed: {','.join(qs.get('symbols_observed') or [])}")
    print(f" - dominant_symbol: {qs.get('dominant_symbol')} pct={qs.get('dominant_symbol_pct')}")
    print(f" - mean_forward_edge_bps: {qs.get('mean_forward_edge_bps')}")
    print(f" - median_forward_edge_bps: {qs.get('median_forward_edge_bps')}")
    print(f" - profit_factor: {qs.get('profit_factor')}")
    print(f" - win_rate_pct: {qs.get('win_rate_pct')}")
    print(f" - high_slippage_count: {qs.get('high_slippage_count')}")
    print(f" - high_slippage_symbols: {','.join(qs.get('high_slippage_symbols') or [])}")
    print(f" - approved_for_paper_candidate: {report.get('approved_for_paper_candidate')}")
    print(f" - approved_for_live_real: {report.get('approved_for_live_real')}")
    print(f" - reason_codes: {report.get('reason_codes')}")
    print(f" - recommendation_consistency: {report.get('recommendation_consistency')}")
    print(f" - warnings: {report.get('warnings')}")
    print(f" - recommendation: {report.get('recommendation')}")
    print(f"report_json: {json_path}")
    print(f"report_md: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
