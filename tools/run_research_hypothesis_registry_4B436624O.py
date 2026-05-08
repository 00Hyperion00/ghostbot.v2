from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradebot.research_hypothesis_registry import (  # noqa: E402
    RESEARCH_HYPOTHESIS_REGISTRY_CONTRACT_VERSION,
    build_research_hypothesis_registry,
    default_research_hypotheses,
    load_hypotheses_json,
    write_default_registry_files,
    write_report,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.24O research hypothesis registry")
    parser.add_argument("--hypotheses-json", default=None, help="Optional hypothesis registry JSON file")
    parser.add_argument("--out-dir", default="reports", help="Report output directory")
    parser.add_argument("--config-dir", default="config", help="Config output directory for default registry files")
    parser.add_argument("--write-default-registry", action="store_true", help="Write default JSON/YAML registry files")
    parser.add_argument("--previous-decision", default="RESEARCH_STOP_NO_GO")
    parser.add_argument("--review-ok", action="store_true", help="Required operator acknowledgement")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.review_ok:
        print("ERROR: --review-ok is required; this is an explicit research governance step.")
        return 2

    registry_files = None
    if args.write_default_registry:
        registry_files = write_default_registry_files(args.config_dir)

    if args.hypotheses_json:
        hypotheses = load_hypotheses_json(args.hypotheses_json)
        source = f"json:{args.hypotheses_json}"
    else:
        hypotheses = default_research_hypotheses()
        source = "default_24O_registry"

    report = build_research_hypothesis_registry(
        hypotheses,
        source=source,
        previous_decision=args.previous_decision,
    )
    if registry_files:
        report["registry_files_written"] = registry_files
    paths = write_report(report, args.out_dir)

    print(f"{RESEARCH_HYPOTHESIS_REGISTRY_CONTRACT_VERSION} research hypothesis registry {report['decision']}")
    print(f" - hypotheses: {report['hypothesis_count']}")
    print(f" - valid_hypotheses: {report['valid_hypothesis_count']}")
    print(f" - selected_next_hypothesis_id: {report['selected_next_hypothesis_id']}")
    print(f" - approved_for_research_candidate: {report['approved_for_research_candidate']}")
    print(f" - approved_for_training_candidate: {report['approved_for_training_candidate']}")
    print(f" - approved_for_paper_candidate: {report['approved_for_paper_candidate']}")
    print(f" - approved_for_live_real: {report['approved_for_live_real']}")
    print(f" - reason_codes: {report['reason_codes']}")
    print(f" - recommendation: {report['recommendation']}")
    if registry_files:
        print(f"registry_json: {registry_files['json']}")
        print(f"registry_yaml: {registry_files['yaml']}")
    print(f"report_json: {paths['json']}")
    print(f"report_md: {paths['md']}")
    return 0 if report["decision"] == "REGISTRY_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
