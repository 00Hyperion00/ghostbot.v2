from __future__ import annotations

import argparse
import json
import py_compile
from pathlib import Path
from typing import Sequence

CONTRACT_VERSION = "4B.4.3.6.6.28G-H1"
EXPECTED_FILES = [
    "src/tradebot/hyp006_signal_frequency_stagnation_diagnostics.py",
    "tools/run_4B436628G_H1_hyp006_signal_frequency_stagnation_diagnostics.py",
    "tools/apply_4B436628G_H1_hyp006_signal_frequency_stagnation_diagnostics.py",
    "tools/check_4B436628G_H1_hyp006_signal_frequency_stagnation_diagnostics.py",
    "tools/rollback_4B436628G_H1_hyp006_signal_frequency_stagnation_diagnostics.py",
    "tests/test_hyp006_signal_frequency_stagnation_diagnostics_4B436628G_H1.py",
    "docs/HYP006_R1_SIGNAL_FREQUENCY_STAGNATION_DIAGNOSTICS_4B436628G_H1.md",
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
    module = root / "src/tradebot/hyp006_signal_frequency_stagnation_diagnostics.py"
    text = module.read_text(encoding="utf-8") if module.exists() else ""
    checks = {
        "all_expected_files_present": all(expected.values()),
        "all_py_compile_ok": len(compiled) == 6 and all(compiled.values()),
        "contract_version_ok": CONTRACT_VERSION in text,
        "read_only_flags_present": "NO_MUTATION_FLAGS" in text and "trading_action_performed" in text,
        "stagnation_hash_detector_present": "sha256_file" in text and "unchanged_payload_run_count" in text,
        "paper_live_order_blocked": "approved_for_paper_candidate\": False" in text or "approved_for_paper_candidate" in text,
        "scheduler_mutation_blocked": "scheduler_mutation_performed" in text,
        "training_blocked": "training_performed" in text,
    }
    ok = all(checks.values())
    return {
        "ok": ok,
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
    parser = argparse.ArgumentParser(description="Check 28G-H1 HYP-006 diagnostics patch.")
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
