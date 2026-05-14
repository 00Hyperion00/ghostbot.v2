from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from tradebot.research_hyp005_symbol_coverage_expansion import (  # noqa: E402
    DEFAULT_HYP005_SYMBOLS_10,
    HYP005_SYMBOL_COVERAGE_CONTRACT_VERSION,
    build_hyp005_symbol_coverage_report,
    write_symbol_coverage_outputs,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="4B.4.3.6.6.25AA HYP-005 controlled 10-symbol coverage expansion gate."
    )
    parser.add_argument(
        "--symbols",
        default=",".join(DEFAULT_HYP005_SYMBOLS_10),
        help="Comma-separated symbols. Must resolve to exactly 10 USDT symbols.",
    )
    parser.add_argument("--input-json", type=Path, default=None, help="Optional explicit latest 25Y operator audit JSON.")
    parser.add_argument("--reports-dir", type=Path, default=Path("reports"), help="Reports directory used to find latest 25Y audit.")
    parser.add_argument("--config-dir", type=Path, default=Path("config"), help="Config output directory.")
    parser.add_argument("--out-dir", type=Path, default=Path("reports"), help="Report output directory.")
    parser.add_argument("--write-config", action="store_true", help="Write config/hyp005_shadow_symbols_4B436625AA.json/yaml.")
    parser.add_argument("--review-ok", action="store_true", help="Required human review acknowledgement.")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    report = build_hyp005_symbol_coverage_report(
        symbols=args.symbols,
        input_json=args.input_json,
        reports_dir=args.reports_dir,
        review_ok=args.review_ok,
    )
    outputs = write_symbol_coverage_outputs(
        report,
        out_dir=args.out_dir,
        config_dir=args.config_dir,
        write_config=args.write_config,
    )

    print(
        f"{HYP005_SYMBOL_COVERAGE_CONTRACT_VERSION} HYP-005 controlled symbol coverage {report.decision}"
    )
    print(f" - source_operator_audit: {report.source_operator_audit}")
    print(f" - hypothesis_id: {report.hypothesis_id}")
    print(f" - selected_strategy_family: {report.selected_strategy_family}")
    print(f" - approved_symbols: {','.join(report.approved_symbols) if report.approved_symbols else 'NONE'}")
    print(f" - requested_symbol_count: {len(report.requested_symbols)}")
    print(f" - approved_symbol_count: {report.symbol_count}")
    print(f" - baseline_symbol_count: {report.baseline_symbol_count}")
    print(f" - expansion_symbol_count: {report.expansion_symbol_count}")
    print(f" - shadow_observation_count: {report.source_shadow_observation_count}")
    print(f" - shadow_sample_target: {report.source_shadow_sample_target}")
    print(f" - approved_for_shadow_collection: {report.approved_for_shadow_collection}")
    print(f" - approved_for_scheduler_regeneration: {report.approved_for_scheduler_regeneration}")
    print(f" - approved_for_paper_candidate: {report.approved_for_paper_candidate}")
    print(f" - approved_for_live_real: {report.approved_for_live_real}")
    print(f" - reason_codes: {list(report.reason_codes)}")
    print(f" - warnings: {list(report.warnings)}")
    print(f" - recommendation: {report.recommendation}")
    print(f"report_json: {outputs['report_json']}")
    print(f"report_md: {outputs['report_md']}")
    if "config_json" in outputs:
        print(f"config_json: {outputs['config_json']}")
    if "config_yaml" in outputs:
        print(f"config_yaml: {outputs['config_yaml']}")
    print(f"symbols_arg: {report.next_scheduler_symbols_arg}")
    return 0 if report.ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
