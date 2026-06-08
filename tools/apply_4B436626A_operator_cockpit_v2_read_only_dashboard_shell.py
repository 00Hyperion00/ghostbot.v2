from __future__ import annotations

import py_compile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

CHECKS: tuple[tuple[str, str], ...] = (
    ("src/tradebot/operator_cockpit_v2_read_only.py", "OPERATOR_COCKPIT_V2_CONTRACT_VERSION"),
    ("src/tradebot/operator_cockpit_v2_read_only.py", "4B.4.3.6.6.26A"),
    ("src/tradebot/operator_cockpit_v2_read_only.py", "OPERATOR_COCKPIT_V2_READ_ONLY = True"),
    ("src/tradebot/operator_cockpit_v2_read_only.py", "OPERATOR_COCKPIT_V2_NO_CONFIG_MUTATION = True"),
    ("src/tradebot/operator_cockpit_v2_read_only.py", "OPERATOR_COCKPIT_V2_NO_SCHEDULER_MUTATION = True"),
    ("src/tradebot/operator_cockpit_v2_read_only.py", "OPERATOR_COCKPIT_V2_NO_TRADING_ACTION = True"),
    ("src/tradebot/operator_cockpit_v2_read_only.py", "READ_ONLY_DASHBOARD_MUTATION_BLOCKED"),
    ("src/tradebot/operator_cockpit_v2_read_only.py", "HYP-005-R1 Shadow Validation"),
    ("src/tradebot/operator_cockpit_v2_read_only.py", "Risk Merkezi"),
    ("tools/run_operator_cockpit_v2_4B436626A.py", "--once-json"),
    ("tools/start_operator_cockpit_v2_4B436626A.ps1", "--open-browser"),
    ("tests/test_operator_cockpit_v2_read_only_dashboard_shell_4B436626A.py", "test_26a_http_server_blocks_all_mutation_methods"),
    ("docs/OPERATOR_COCKPIT_V2_READ_ONLY_DASHBOARD_SHELL_4B436626A.md", "Operator Cockpit V2 — Visual UX Foundation / Read-Only Dashboard Shell"),
)

COMPILE_TARGETS: tuple[str, ...] = (
    "src/tradebot/operator_cockpit_v2_read_only.py",
    "tools/run_operator_cockpit_v2_4B436626A.py",
    "tests/test_operator_cockpit_v2_read_only_dashboard_shell_4B436626A.py",
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
        safe = marker.replace(" ", "_").replace("/", "_").replace("\\", "_")
        results.append((f"{safe}_present", present))
    print("4B.4.3.6.6.26A Operator Cockpit V2 visual UX foundation / read-only dashboard shell applied")
    all_ok = True
    for name, ok in results:
        print(f" - {name}: {ok}")
        all_ok = all_ok and ok
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
