from __future__ import annotations

import py_compile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

CHECKS: tuple[tuple[str, str], ...] = (
    ("src/tradebot/operator_cockpit_v2_desktop_wrapper.py", 'OPERATOR_COCKPIT_V2_WINDOWS_SAFE_PID_LOCK_HOTFIX_VERSION = "4B.4.3.6.6.26D-H1"'),
    ("src/tradebot/operator_cockpit_v2_desktop_wrapper.py", "OPERATOR_COCKPIT_V2_WINDOWS_SAFE_PID_LIVENESS_PROBE = True"),
    ("src/tradebot/operator_cockpit_v2_desktop_wrapper.py", "OPERATOR_COCKPIT_V2_DETERMINISTIC_SINGLE_INSTANCE_LOCK = True"),
    ("src/tradebot/operator_cockpit_v2_desktop_wrapper.py", "OPERATOR_COCKPIT_V2_WINDOWS_OS_KILL_ZERO_DISABLED = True"),
    ("src/tradebot/operator_cockpit_v2_desktop_wrapper.py", "def _windows_pid_is_running("),
    ("src/tradebot/operator_cockpit_v2_desktop_wrapper.py", "def _posix_pid_is_running(pid: int) -> bool:"),
    ("src/tradebot/operator_cockpit_v2_desktop_wrapper.py", "api.OpenProcess(desired_access, False, pid)"),
    ("src/tradebot/operator_cockpit_v2_desktop_wrapper.py", "api.WaitForSingleObject(handle, 0)"),
    ("src/tradebot/operator_cockpit_v2_desktop_wrapper.py", "api.CloseHandle(handle)"),
    ("src/tradebot/operator_cockpit_v2_desktop_wrapper.py", "lock_id=uuid.uuid4().hex"),
    ("tests/test_operator_cockpit_v2_windows_safe_pid_lock_hotfix_4B436626DH1.py", "test_26dh1_windows_branch_uses_winapi_and_never_calls_os_kill"),
    ("tests/test_operator_cockpit_v2_windows_safe_pid_lock_hotfix_4B436626DH1.py", "test_26dh1_release_does_not_delete_lock_owned_by_another_instance"),
    ("docs/OPERATOR_COCKPIT_V2_WINDOWS_SAFE_PID_LOCK_HOTFIX_4B436626DH1.md", "Operator Cockpit V2 — Windows Safe PID Liveness Probe / Deterministic Single-Instance Lock Hotfix"),
)

COMPILE_TARGETS: tuple[str, ...] = (
    "src/tradebot/operator_cockpit_v2_desktop_wrapper.py",
    "tools/apply_4B436626D_H1_operator_cockpit_v2_windows_safe_pid_lock_hotfix.py",
    "tests/test_operator_cockpit_v2_windows_safe_pid_lock_hotfix_4B436626DH1.py",
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
    print("4B.4.3.6.6.26D-H1 Operator Cockpit V2 Windows safe PID liveness probe / deterministic single-instance lock hotfix applied")
    all_ok = True
    for name, ok in results:
        print(f" - {name}: {ok}")
        all_ok = all_ok and ok
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
