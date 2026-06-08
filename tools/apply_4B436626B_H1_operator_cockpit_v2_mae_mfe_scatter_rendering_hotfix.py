from __future__ import annotations

import py_compile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

CHECKS: tuple[tuple[str, str], ...] = (
    ("src/tradebot/operator_cockpit_v2_read_only.py", 'OPERATOR_COCKPIT_V2_MAE_MFE_SCATTER_HOTFIX_VERSION = "4B.4.3.6.6.26B-H1"'),
    ("src/tradebot/operator_cockpit_v2_read_only.py", "OPERATOR_COCKPIT_V2_SIGNED_MAE_MFE_DOMAIN = True"),
    ("src/tradebot/operator_cockpit_v2_read_only.py", "OPERATOR_COCKPIT_V2_ACCURATE_MAE_MFE_EMPTY_STATE = True"),
    ("src/tradebot/operator_cockpit_v2_read_only.py", "function signedDomain(values)"),
    ("src/tradebot/operator_cockpit_v2_read_only.py", "function scaleSigned(value,domain,start,end)"),
    ("src/tradebot/operator_cockpit_v2_read_only.py", "MAE / MFE verisi henüz oluşmadı."),
    ("src/tradebot/operator_cockpit_v2_read_only.py", "Final Edge ${fmt(record.forward_return_bps_final,2)}"),
    ("src/tradebot/operator_cockpit_v2_read_only.py", "READ_ONLY_DASHBOARD_MUTATION_BLOCKED"),
    ("tests/test_operator_cockpit_v2_mae_mfe_scatter_rendering_hotfix_4B436626BH1.py", "test_26bh1_node_scatter_renderer_keeps_signed_mae_points_inside_canvas"),
    ("docs/OPERATOR_COCKPIT_V2_MAE_MFE_SCATTER_RENDERING_HOTFIX_4B436626BH1.md", "Operator Cockpit V2 — MAE / MFE Scatter Rendering and Empty-State Accuracy Hotfix"),
)

COMPILE_TARGETS: tuple[str, ...] = (
    "src/tradebot/operator_cockpit_v2_read_only.py",
    "tools/apply_4B436626B_H1_operator_cockpit_v2_mae_mfe_scatter_rendering_hotfix.py",
    "tests/test_operator_cockpit_v2_mae_mfe_scatter_rendering_hotfix_4B436626BH1.py",
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
    print("4B.4.3.6.6.26B-H1 Operator Cockpit V2 MAE / MFE scatter rendering / empty-state accuracy hotfix applied")
    all_ok = True
    for name, ok in results:
        print(f" - {name}: {ok}")
        all_ok = all_ok and ok
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
