from __future__ import annotations

import py_compile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

CHECKS: tuple[tuple[str, str], ...] = (
    ("src/tradebot/operator_cockpit_v2_read_only.py", 'OPERATOR_COCKPIT_V2_SAFE_ACTIONS_VERSION = "4B.4.3.6.6.26C"'),
    ("src/tradebot/operator_cockpit_v2_read_only.py", "OPERATOR_COCKPIT_V2_SAFE_OPERATOR_ACTIONS = True"),
    ("src/tradebot/operator_cockpit_v2_read_only.py", "OPERATOR_COCKPIT_V2_GET_ONLY_ACTIONS = True"),
    ("src/tradebot/operator_cockpit_v2_read_only.py", "OPERATOR_COCKPIT_V2_IN_MEMORY_EXPORTS_ONLY = True"),
    ("src/tradebot/operator_cockpit_v2_read_only.py", "MAX_OPERATOR_COCKPIT_EXPORT_FILE_BYTES = 5 * 1024 * 1024"),
    ("src/tradebot/operator_cockpit_v2_read_only.py", "MAX_OPERATOR_COCKPIT_EVIDENCE_PACK_BYTES = 12 * 1024 * 1024"),
    ("src/tradebot/operator_cockpit_v2_read_only.py", "def _safe_latest_export_source(project_root: Path, kind: str) -> Path | None:"),
    ("src/tradebot/operator_cockpit_v2_read_only.py", "def _build_in_memory_evidence_pack("),
    ("src/tradebot/operator_cockpit_v2_read_only.py", 'if path == "/api/operator-cockpit-v2/actions/backend-probe":'),
    ("src/tradebot/operator_cockpit_v2_read_only.py", 'if path == "/api/operator-cockpit-v2/export/evidence-pack.zip":'),
    ("src/tradebot/operator_cockpit_v2_read_only.py", "Güvenli Operatör Aksiyonları"),
    ("src/tradebot/operator_cockpit_v2_read_only.py", "26C · GET ONLY"),
    ("src/tradebot/operator_cockpit_v2_read_only.py", "READ_ONLY_DASHBOARD_MUTATION_BLOCKED"),
    ("tools/run_operator_cockpit_v2_4B436626C.py", "Operator Cockpit V2 safe operator actions"),
    ("tools/start_operator_cockpit_v2_4B436626C.ps1", "run_operator_cockpit_v2_4B436626C.py"),
    ("tests/test_operator_cockpit_v2_safe_operator_actions_4B436626C.py", "test_26c_all_mutation_methods_remain_stable_405_on_safe_action_routes"),
    ("docs/OPERATOR_COCKPIT_V2_SAFE_OPERATOR_ACTIONS_4B436626C.md", "Operator Cockpit V2 — Safe Operator Actions"),
)

COMPILE_TARGETS: tuple[str, ...] = (
    "src/tradebot/operator_cockpit_v2_read_only.py",
    "tools/apply_4B436626C_operator_cockpit_v2_safe_operator_actions.py",
    "tools/run_operator_cockpit_v2_4B436626C.py",
    "tests/test_operator_cockpit_v2_safe_operator_actions_4B436626C.py",
)


def main() -> int:
    results: list[tuple[str, bool]] = []
    for rel_path in COMPILE_TARGETS:
        path = PROJECT_ROOT / rel_path
        exists = path.exists()
        results.append((f"{rel_path}_exists", exists))
        if exists:
            try:
                py_compile.compile(str(path), doraise=True)
                results.append((f"{rel_path}_py_compile_ok", True))
            except py_compile.PyCompileError:
                results.append((f"{rel_path}_py_compile_ok", False))
    for rel_path, marker in CHECKS:
        path = PROJECT_ROOT / rel_path
        present = path.exists() and marker in path.read_text(encoding="utf-8")
        safe = marker.replace(" ", "_").replace("/", "_").replace(chr(92), "_")
        results.append((f"{safe}_present", present))
    print("4B.4.3.6.6.26C Operator Cockpit V2 safe operator actions applied")
    all_ok = True
    for name, ok in results:
        print(f" - {name}: {ok}")
        all_ok = all_ok and ok
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
