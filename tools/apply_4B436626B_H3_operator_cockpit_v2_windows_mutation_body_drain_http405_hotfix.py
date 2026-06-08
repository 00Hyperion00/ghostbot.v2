from __future__ import annotations

import py_compile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

CHECKS: tuple[tuple[str, str], ...] = (
    ("src/tradebot/operator_cockpit_v2_read_only.py", 'OPERATOR_COCKPIT_V2_WINDOWS_MUTATION_BODY_DRAIN_HOTFIX_VERSION = "4B.4.3.6.6.26B-H3"'),
    ("src/tradebot/operator_cockpit_v2_read_only.py", "OPERATOR_COCKPIT_V2_MUTATION_REQUEST_BODY_DRAIN = True"),
    ("src/tradebot/operator_cockpit_v2_read_only.py", "OPERATOR_COCKPIT_V2_HTTP_405_CONTRACT_PRESERVATION = True"),
    ("src/tradebot/operator_cockpit_v2_read_only.py", "MAX_MUTATION_REQUEST_BODY_DRAIN_BYTES = 64 * 1024"),
    ("src/tradebot/operator_cockpit_v2_read_only.py", "def _parse_content_length(raw_value: str | None) -> int | None:"),
    ("src/tradebot/operator_cockpit_v2_read_only.py", "def _drain_mutation_request_body(self) -> int:"),
    ("src/tradebot/operator_cockpit_v2_read_only.py", "self._drain_mutation_request_body()"),
    ("src/tradebot/operator_cockpit_v2_read_only.py", "READ_ONLY_DASHBOARD_MUTATION_BLOCKED"),
    ("src/tradebot/operator_cockpit_v2_read_only.py", "26B-H3 · READ ONLY"),
    ("tests/test_operator_cockpit_v2_windows_mutation_body_drain_http405_hotfix_4B436626BH3.py", "test_26bh3_all_mutation_methods_return_stable_405_json_with_request_body"),
    ("docs/OPERATOR_COCKPIT_V2_WINDOWS_MUTATION_BODY_DRAIN_HTTP405_HOTFIX_4B436626BH3.md", "Operator Cockpit V2 — Windows Mutation Request Body Drain / HTTP 405 Contract Preservation Hotfix"),
)

COMPILE_TARGETS: tuple[str, ...] = (
    "src/tradebot/operator_cockpit_v2_read_only.py",
    "tools/apply_4B436626B_H3_operator_cockpit_v2_windows_mutation_body_drain_http405_hotfix.py",
    "tests/test_operator_cockpit_v2_windows_mutation_body_drain_http405_hotfix_4B436626BH3.py",
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
    print("4B.4.3.6.6.26B-H3 Operator Cockpit V2 Windows mutation request body drain / HTTP 405 contract preservation hotfix applied")
    all_ok = True
    for name, ok in results:
        print(f" - {name}: {ok}")
        all_ok = all_ok and ok
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
