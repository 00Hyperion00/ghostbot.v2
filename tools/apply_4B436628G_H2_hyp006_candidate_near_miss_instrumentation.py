from __future__ import annotations

import py_compile
from pathlib import Path

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
NO_MUTATION_FLAGS = {
    "config_mutation_performed": False,
    "scheduler_mutation_performed": False,
    "scheduler_task_created": False,
    "training_performed": False,
    "reload_performed": False,
    "trading_action_performed": False,
    "paper_live_order_enablement_present": False,
}


def compile_ok(path: Path) -> bool:
    if path.suffix != ".py":
        return True
    try:
        py_compile.compile(str(path), doraise=True)
        return True
    except py_compile.PyCompileError:
        return False


def main() -> int:
    root = Path.cwd()
    results: dict[str, object] = {**NO_MUTATION_FLAGS}
    ok = True
    for rel in EXPECTED_FILES:
        path = root / rel
        exists = path.exists()
        compiled = compile_ok(path) if exists else False
        results[f"{rel}_exists"] = exists
        if rel.endswith(".py"):
            results[f"{rel}_py_compile_ok"] = compiled
        ok = ok and exists and compiled

    module = root / "src/tradebot/hyp006_candidate_near_miss_instrumentation.py"
    text = module.read_text(encoding="utf-8") if module.exists() else ""
    results["contract_version_present"] = CONTRACT_VERSION in text
    results["read_only_contract_present"] = "NO_MUTATION_FLAGS" in text and "trading_action_performed" in text
    results["candidate_instrumentation_present"] = "candidate_trigger_instrumentation" in text
    results["near_miss_counter_present"] = "near_miss_count" in text
    results["no_parameter_relaxation_present"] = "approved_for_parameter_relaxation_candidate" in text and "False" in text
    ok = ok and all(bool(results[key]) for key in (
        "contract_version_present",
        "read_only_contract_present",
        "candidate_instrumentation_present",
        "near_miss_counter_present",
        "no_parameter_relaxation_present",
    ))

    print(f"{CONTRACT_VERSION} HYP-006 candidate/near-miss instrumentation patch applied")
    for key, value in results.items():
        print(f" - {key}: {value}")
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
