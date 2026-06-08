from __future__ import annotations

import py_compile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

CHECKS: tuple[tuple[str, str], ...] = (
    ("src/tradebot/operator_cockpit_v2_desktop_wrapper.py", 'OPERATOR_COCKPIT_V2_DESKTOP_WRAPPER_VERSION = "4B.4.3.6.6.26D"'),
    ("src/tradebot/operator_cockpit_v2_desktop_wrapper.py", "OPERATOR_COCKPIT_V2_DESKTOP_LOCAL_ONLY = True"),
    ("src/tradebot/operator_cockpit_v2_desktop_wrapper.py", "OPERATOR_COCKPIT_V2_SINGLE_INSTANCE = True"),
    ("src/tradebot/operator_cockpit_v2_desktop_wrapper.py", "OPERATOR_COCKPIT_V2_BROWSER_FALLBACK_REQUIRES_EXPLICIT_FLAG = True"),
    ("src/tradebot/operator_cockpit_v2_desktop_wrapper.py", "def start_local_cockpit_server("),
    ("src/tradebot/operator_cockpit_v2_desktop_wrapper.py", "def launch_desktop_shell("),
    ("src/tradebot/operator_cockpit_v2_desktop_wrapper.py", "def run_headless_smoke("),
    ("src/tradebot/operator_cockpit_v2_desktop_wrapper.py", "NON_LOOPBACK_DESKTOP_BIND_BLOCKED"),
    ("src/tradebot/operator_cockpit_v2_desktop_wrapper.py", "OPERATOR_COCKPIT_DESKTOP_INSTANCE_ALREADY_RUNNING"),
    ("tools/run_operator_cockpit_v2_desktop_4B436626D.py", "--headless-smoke-json"),
    ("tools/start_operator_cockpit_v2_desktop_4B436626D.ps1", "run_operator_cockpit_v2_desktop_4B436626D.py"),
    ("tools/start_operator_cockpit_v2_desktop_4B436626D.cmd", "start_operator_cockpit_v2_desktop_4B436626D.ps1"),
    ("tools/install_operator_cockpit_v2_desktop_dependency_4B436626D.ps1", "python -m pip install pywebview"),
    ("tests/test_operator_cockpit_v2_desktop_wrapper_4B436626D.py", "test_26d_embedded_webview_lifecycle_owns_local_server_and_uses_dashboard_url"),
    ("docs/OPERATOR_COCKPIT_V2_DESKTOP_WRAPPER_4B436626D.md", "Operator Cockpit V2 — Desktop Wrapper / Single-Launch Local Application Shell"),
)

COMPILE_TARGETS: tuple[str, ...] = (
    "src/tradebot/operator_cockpit_v2_desktop_wrapper.py",
    "tools/run_operator_cockpit_v2_desktop_4B436626D.py",
    "tools/apply_4B436626D_operator_cockpit_v2_desktop_wrapper.py",
    "tests/test_operator_cockpit_v2_desktop_wrapper_4B436626D.py",
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
    print("4B.4.3.6.6.26D Operator Cockpit V2 desktop wrapper / single-launch local application shell applied")
    all_ok = True
    for name, ok in results:
        print(f" - {name}: {ok}")
        all_ok = all_ok and ok
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
