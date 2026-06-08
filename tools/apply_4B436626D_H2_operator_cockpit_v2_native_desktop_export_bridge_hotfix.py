from __future__ import annotations

import py_compile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

CHECKS: tuple[tuple[str, str], ...] = (
    ("src/tradebot/operator_cockpit_v2_desktop_wrapper.py", 'OPERATOR_COCKPIT_V2_NATIVE_EXPORT_BRIDGE_HOTFIX_VERSION = "4B.4.3.6.6.26D-H2"'),
    ("src/tradebot/operator_cockpit_v2_desktop_wrapper.py", "OPERATOR_COCKPIT_V2_NATIVE_DESKTOP_EXPORT_BRIDGE = True"),
    ("src/tradebot/operator_cockpit_v2_desktop_wrapper.py", "OPERATOR_COCKPIT_V2_NATIVE_SAVE_DIALOG_DOWNLOADS = True"),
    ("src/tradebot/operator_cockpit_v2_desktop_wrapper.py", "OPERATOR_COCKPIT_V2_NATIVE_EXPORT_ALLOWLIST_ONLY = True"),
    ("src/tradebot/operator_cockpit_v2_desktop_wrapper.py", "OPERATOR_COCKPIT_V2_NATIVE_EXPORT_LOOPBACK_ONLY = True"),
    ("src/tradebot/operator_cockpit_v2_desktop_wrapper.py", "class NativeDesktopExportBridge:"),
    ("src/tradebot/operator_cockpit_v2_desktop_wrapper.py", "def export_file(self, action_code: str) -> dict[str, Any]:"),
    ("src/tradebot/operator_cockpit_v2_desktop_wrapper.py", "def read_text(self, action_code: str) -> dict[str, Any]:"),
    ("src/tradebot/operator_cockpit_v2_desktop_wrapper.py", "create_file_dialog(save_dialog, save_filename=filename)"),
    ("src/tradebot/operator_cockpit_v2_desktop_wrapper.py", "NATIVE_DESKTOP_EXPORT_BRIDGE_JS = r\"\"\""),
    ("src/tradebot/operator_cockpit_v2_desktop_wrapper.py", "event.preventDefault()"),
    ("src/tradebot/operator_cockpit_v2_desktop_wrapper.py", "js_api=bridge"),
    ("tools/run_operator_cockpit_v2_desktop_4B436626D.py", "native_export_bridge_hotfix_version"),
    ("tests/test_operator_cockpit_v2_native_desktop_export_bridge_hotfix_4B436626DH2.py", "test_26dh2_native_snapshot_download_uses_save_dialog_allowlist_and_atomic_writer"),
    ("docs/OPERATOR_COCKPIT_V2_NATIVE_DESKTOP_EXPORT_BRIDGE_HOTFIX_4B436626DH2.md", "Operator Cockpit V2 — Native Desktop Export Bridge / Save-Dialog Download Hotfix"),
)

COMPILE_TARGETS: tuple[str, ...] = (
    "src/tradebot/operator_cockpit_v2_desktop_wrapper.py",
    "tools/run_operator_cockpit_v2_desktop_4B436626D.py",
    "tools/apply_4B436626D_H2_operator_cockpit_v2_native_desktop_export_bridge_hotfix.py",
    "tests/test_operator_cockpit_v2_native_desktop_export_bridge_hotfix_4B436626DH2.py",
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
    print("4B.4.3.6.6.26D-H2 Operator Cockpit V2 native desktop export bridge / save-dialog download hotfix applied")
    all_ok = True
    for name, ok in results:
        print(f" - {name}: {ok}")
        all_ok = all_ok and ok
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
