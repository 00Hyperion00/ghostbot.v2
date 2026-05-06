from __future__ import annotations

import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = [
    Path("tools/run_extended_demo_soak_4B436624C.py"),
    Path("tests/test_extended_demo_soak_4B436624C.py"),
    Path("docs/EXTENDED_DEMO_SOAK_RUNBOOK_4B436624C.md"),
]


def _contains(path: Path, needle: str) -> bool:
    try:
        return needle in path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return False


def _compile_ok(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
        return True
    except Exception:
        return False


def main() -> int:
    checks: dict[str, bool] = {}
    for rel in REQUIRED_FILES:
        path = ROOT / rel
        checks[f"{rel.as_posix()}_exists"] = path.exists()
        if rel.suffix == ".py":
            checks[f"{rel.as_posix()}_py_compile_ok"] = path.exists() and _compile_ok(path)

    tool = ROOT / "tools" / "run_extended_demo_soak_4B436624C.py"
    checks.update(
        {
            "phase_contract_present": _contains(tool, 'CONTRACT_VERSION = "4B.4.3.6.6.24C"'),
            "extended_soak_report_prefix_present": _contains(tool, 'REPORT_PREFIX = "4B436624C_extended_demo_soak"'),
            "model_gate_timeline_report_prefix_present": _contains(tool, 'TIMELINE_PREFIX = "4B436624C_model_gate_timeline"'),
            "pre_paper_readiness_report_prefix_present": _contains(tool, 'READINESS_PREFIX = "4B436624C_pre_paper_readiness"'),
            "get_only_contract_present": _contains(tool, 'method="GET"') and not _contains(tool, 'method="POST"'),
            "model_gate_block_guard_present": _contains(tool, 'MODEL_GATE_BLOCK'),
            "live_real_not_ready_contract_present": _contains(tool, '"ready_for_live_real": False'),
            "readiness_builder_present": _contains(tool, 'def build_pre_paper_readiness'),
        }
    )
    ok = all(checks.values())
    print("4B.4.3.6.6.24C extended demo soak + model gate reporting patch applied")
    for key, value in checks.items():
        print(f" - {key}: {value}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
