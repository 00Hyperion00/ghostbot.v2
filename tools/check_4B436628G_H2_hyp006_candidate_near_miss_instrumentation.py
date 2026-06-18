from __future__ import annotations

import argparse
import json
import py_compile
from pathlib import Path
from typing import Sequence

CONTRACT_VERSION = "4B.4.3.6.6.28G-H2"
EXPECTED_FILES = [
    "src/tradebot/hyp006_candidate_near_miss_instrumentation.py",
    "tools/run_4B436628G_H2_hyp006_candidate_near_miss_instrumentation.py",
    "tools/apply_4B436628G_H2_hyp006_candidate_near_miss_instrumentation.py",
    "tools/check_4B436628G_H2_hyp006_candidate_near_miss_instrumentation.py",
    "tools/rollback_4B436628G_H2_hyp006_candidate_near_miss_instrumentation.py",
    "tests/test_hyp006_candidate_near_miss_instrumentation_4B436628G_H2.py",
    "docs/HYP006_R1_CANDIDATE_NEAR_MISS_INSTRUMENTATION_4B436628G_H2.md",
]


def compile_ok(path: Path) -> bool:
    if path.suffix != ".py":
        return True
    try:
        py_compile.compile(str(path), doraise=True)
        return True
    except py_compile.PyCompileError:
        return False


def build_status(root: Path) -> dict[str, object]:
    expected = {rel: (root / rel).exists() for rel in EXPECTED_FILES}
    compiled = {
        rel: compile_ok(root / rel) for rel in EXPECTED_FILES if rel.endswith(".py") and (root / rel).exists()
    }
    module = root / "src/tradebot/hyp006_candidate_near_miss_instrumentation.py"
    text = module.read_text(encoding="utf-8") if module.exists() else ""
    checks = {
        "all_expected_files_present": all(expected.values()),
        "all_py_compile_ok": len(compiled) == 6 and all(compiled.values()),
        "contract_version_ok": CONTRACT_VERSION in text,
        "read_only_flags_present": "NO_MUTATION_FLAGS" in text and "trading_action_performed" in text,
        "candidate_file_scanner_present": "find_candidate_scan_files" in text,
        "gate_block_counter_present": "gate_block_counter" in text,
        "near_miss_counter_present": "near_miss_count" in text,
        "paper_live_order_blocked": "approved_for_paper_candidate" in text and "approved_for_live_real" in text,
        "parameter_relaxation_blocked": "approved_for_parameter_relaxation_candidate" in text and "False" in text,
        "scheduler_mutation_blocked": "scheduler_mutation_performed" in text,
        "training_blocked": "training_performed" in text,
    }
    return {
        "ok": all(checks.values()),
        "contract_version": CONTRACT_VERSION,
        "read_only": True,
        "network_request_performed": False,
        "config_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "scheduler_task_created": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "paper_live_order_enablement_present": False,
        "expected_files": expected,
        "compiled": compiled,
        "checks": checks,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check 28G-H2 HYP-006 candidate/near-miss instrumentation patch.")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args(argv)
    payload = build_status(Path.cwd())
    if args.once_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"{CONTRACT_VERSION} check ok={payload['ok']}")
        for key, value in payload["checks"].items():
            print(f" - {key}: {value}")
    return 0 if payload["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
