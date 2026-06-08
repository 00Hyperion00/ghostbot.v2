from __future__ import annotations

import py_compile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

CHECKS: tuple[tuple[str, str], ...] = (
    ("tools/run_operator_cockpit_v2_4B436626C.py", 'OPERATOR_COCKPIT_V2_WINDOWS_UTF8_ONCE_JSON_RUNNER_HOTFIX_VERSION = "4B.4.3.6.6.26C-H1"'),
    ("tools/run_operator_cockpit_v2_4B436626C.py", "OPERATOR_COCKPIT_V2_ONCE_JSON_UTF8_STDOUT_CONTRACT = True"),
    ("tools/run_operator_cockpit_v2_4B436626C.py", "def _write_utf8_json_stdout(payload: Any) -> None:"),
    ("tools/run_operator_cockpit_v2_4B436626C.py", 'stdout_buffer.write(encoded)'),
    ("tools/run_operator_cockpit_v2_4B436626C.py", '.encode("utf-8")'),
    ("tests/test_operator_cockpit_v2_windows_utf8_once_json_runner_hotfix_4B436626CH1.py", "test_26ch1_once_json_emits_utf8_bytes_independent_of_console_locale"),
    ("docs/OPERATOR_COCKPIT_V2_WINDOWS_UTF8_ONCE_JSON_RUNNER_HOTFIX_4B436626CH1.md", "Operator Cockpit V2 — Windows UTF-8 Once-JSON Runner Output Contract Hotfix"),
)

COMPILE_TARGETS: tuple[str, ...] = (
    "tools/run_operator_cockpit_v2_4B436626C.py",
    "tools/apply_4B436626C_H1_operator_cockpit_v2_windows_utf8_once_json_runner_hotfix.py",
    "tests/test_operator_cockpit_v2_windows_utf8_once_json_runner_hotfix_4B436626CH1.py",
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
    print("4B.4.3.6.6.26C-H1 Operator Cockpit V2 Windows UTF-8 once-JSON runner output contract hotfix applied")
    all_ok = True
    for name, ok in results:
        print(f" - {name}: {ok}")
        all_ok = all_ok and ok
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
