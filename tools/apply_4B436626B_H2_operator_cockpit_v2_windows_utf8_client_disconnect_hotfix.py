from __future__ import annotations

import py_compile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

CHECKS: tuple[tuple[str, str], ...] = (
    ("src/tradebot/operator_cockpit_v2_read_only.py", 'OPERATOR_COCKPIT_V2_WINDOWS_UTF8_CLIENT_DISCONNECT_HOTFIX_VERSION = "4B.4.3.6.6.26B-H2"'),
    ("src/tradebot/operator_cockpit_v2_read_only.py", "OPERATOR_COCKPIT_V2_WINDOWS_UTF8_EMPTY_STATE_ASSERTION = True"),
    ("src/tradebot/operator_cockpit_v2_read_only.py", "OPERATOR_COCKPIT_V2_CLIENT_DISCONNECT_NOISE_SUPPRESSION = True"),
    ("src/tradebot/operator_cockpit_v2_read_only.py", "def _is_client_disconnect_error(error: BaseException) -> bool:"),
    ("src/tradebot/operator_cockpit_v2_read_only.py", "except OSError as error:"),
    ("src/tradebot/operator_cockpit_v2_read_only.py", "MAE / MFE verisi henüz oluşmadı."),
    ("src/tradebot/operator_cockpit_v2_read_only.py", "26B-H2 · READ ONLY"),
    ("src/tradebot/operator_cockpit_v2_read_only.py", "READ_ONLY_DASHBOARD_MUTATION_BLOCKED"),
    ("tests/test_operator_cockpit_v2_mae_mfe_scatter_rendering_hotfix_4B436626BH1.py", 'encoding="utf-8"'),
    ("tests/test_operator_cockpit_v2_windows_utf8_client_disconnect_hotfix_4B436626BH2.py", "test_26bh2_write_suppresses_expected_client_disconnect_noise"),
    ("docs/OPERATOR_COCKPIT_V2_WINDOWS_UTF8_CLIENT_DISCONNECT_HOTFIX_4B436626BH2.md", "Operator Cockpit V2 — Windows UTF-8 Empty-State Assertion / Client Disconnect Noise Suppression Hotfix"),
)

COMPILE_TARGETS: tuple[str, ...] = (
    "src/tradebot/operator_cockpit_v2_read_only.py",
    "tools/apply_4B436626B_H2_operator_cockpit_v2_windows_utf8_client_disconnect_hotfix.py",
    "tests/test_operator_cockpit_v2_mae_mfe_scatter_rendering_hotfix_4B436626BH1.py",
    "tests/test_operator_cockpit_v2_windows_utf8_client_disconnect_hotfix_4B436626BH2.py",
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
    print("4B.4.3.6.6.26B-H2 Operator Cockpit V2 Windows UTF-8 empty-state assertion / client disconnect noise suppression hotfix applied")
    all_ok = True
    for name, ok in results:
        print(f" - {name}: {ok}")
        all_ok = all_ok and ok
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
