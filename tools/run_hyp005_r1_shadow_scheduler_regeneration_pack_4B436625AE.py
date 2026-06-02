from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradebot.research_hyp005_r1_shadow_scheduler_regeneration_pack import (  # noqa: E402
    HYP005_R1_SHADOW_SCHEDULER_REGENERATION_CONTRACT_VERSION,
    HYP005_R1_RUNTIME_CHAIN_HOTFIX_VERSION,
    DEFAULT_R1_REPORTS_SUBDIR,
    Hyp005R1SchedulerPackRequest,
    build_hyp005_r1_shadow_scheduler_regeneration_pack_report,
    write_hyp005_r1_shadow_scheduler_regeneration_pack_report,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.25AE HYP-005-R1 eight-symbol no-order shadow scheduler regeneration pack")
    parser.add_argument("--input-json", type=Path, help="Optional explicit 25AD planning report JSON")
    parser.add_argument("--source-candidate-spec-json", type=Path, help="Optional explicit baseline 25U runtime candidate spec JSON")
    parser.add_argument("--reports-dir", type=Path, default=Path("reports"))
    parser.add_argument("--out-dir", type=Path, default=Path("reports"))
    parser.add_argument("--r1-reports-subdir", default=DEFAULT_R1_REPORTS_SUBDIR)
    parser.add_argument("--baseline-task-name", default="TradeBot_HYP005_NoOrderShadowCollection")
    parser.add_argument("--r1-task-name", default="TradeBot_HYP005_R1_NoOrderShadowCollection")
    parser.add_argument("--run-every-hours", type=int, default=4)
    parser.add_argument("--interval", default="4h")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--base-url", default="https://api.binance.com")
    parser.add_argument("--python-executable", default="python")
    parser.add_argument("--baseline-task-disabled", action="store_true", help="Required operator acknowledgement: baseline Windows task has been Disabled")
    parser.add_argument("--review-ok", action="store_true", help="Required no-order operator review acknowledgement")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    request = Hyp005R1SchedulerPackRequest(
        reports_dir=str(args.reports_dir),
        out_dir=str(args.out_dir),
        r1_reports_subdir=args.r1_reports_subdir,
        baseline_task_name=args.baseline_task_name,
        r1_task_name=args.r1_task_name,
        run_every_hours=args.run_every_hours,
        interval=args.interval,
        days=args.days,
        base_url=args.base_url,
        python_executable=args.python_executable,
    )
    report = build_hyp005_r1_shadow_scheduler_regeneration_pack_report(
        args.reports_dir,
        out_dir=args.out_dir,
        input_json=args.input_json,
        source_candidate_spec_json=args.source_candidate_spec_json,
        request=request,
        baseline_task_disabled_confirmed=args.baseline_task_disabled,
        review_ok=args.review_ok,
    )
    paths = write_hyp005_r1_shadow_scheduler_regeneration_pack_report(report, args.out_dir)
    print(f"{HYP005_R1_RUNTIME_CHAIN_HOTFIX_VERSION} HYP-005-R1 isolated eight-symbol scheduler regeneration pack {report['decision']}")
    print(f" - refined_branch_id: {report['refined_branch_id']}")
    print(f" - fresh_ledger_namespace: {report['fresh_ledger_namespace']}")
    print(f" - isolated_runtime_reports_dir: {report['isolated_runtime_reports_dir']}")
    print(f" - reports_dir_isolation_enforced: {report['reports_dir_isolation_enforced']}")
    print(f" - explicit_report_chaining_enforced: {report['explicit_report_chaining_enforced']}")
    print(f" - runtime_path_join_safety_enforced: {report['runtime_path_join_safety_enforced']}")
    print(f" - canonical_branch_compatibility_enforced: {report['canonical_branch_compatibility_enforced']}")
    print(f" - strict_explicit_report_chaining_enforced: {report['strict_explicit_report_chaining_enforced']}")
    print(f" - refined_symbols_arg: {report['refined_symbols_arg']}")
    print(f" - starting_unique_shadow_observation_count: {report['starting_unique_shadow_observation_count']}")
    print(f" - shadow_sample_target: {report['shadow_sample_target']}")
    print(f" - baseline_task_disabled_confirmed: {report['baseline_task_disabled_confirmed']}")
    print(f" - approved_for_scheduler_pack_generation: {report['approved_for_scheduler_pack_generation']}")
    print(f" - approved_for_scheduler_registration: {report['approved_for_scheduler_registration']}")
    print(f" - approved_for_paper_candidate: {report['approved_for_paper_candidate']}")
    print(f" - approved_for_live_real: {report['approved_for_live_real']}")
    print(f" - reason_codes: {report['reason_codes']}")
    print(f" - blockers: {report['blockers']}")
    print(f" - recommendation: {report['recommendation']}")
    print(f"report_json: {paths['report_json']}")
    print(f"report_md: {paths['report_md']}")
    artifacts = report.get("artifacts") or {}
    if artifacts:
        print(f"pack_dir: {artifacts.get('pack_dir')}")
        print(f"r1_runtime_candidate_spec_json: {artifacts.get('r1_runtime_candidate_spec_json')}")
        print(f"shadow_cycle_ps1: {artifacts.get('shadow_cycle_ps1')}")
        print(f"register_task_ps1: {artifacts.get('register_task_ps1')}")
        print(f"task_xml: {artifacts.get('task_xml')}")
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
