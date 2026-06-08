from __future__ import annotations

import py_compile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

CHECKS: tuple[tuple[str, str], ...] = (
    ("src/tradebot/operator_cockpit_v2_read_only.py", 'OPERATOR_COCKPIT_V2_VISUALIZATION_PACK_VERSION = "4B.4.3.6.6.26B"'),
    ("src/tradebot/operator_cockpit_v2_read_only.py", "OPERATOR_COCKPIT_V2_SHADOW_AUDIT_VISUALIZATION_PACK = True"),
    ("src/tradebot/operator_cockpit_v2_read_only.py", "OPERATOR_COCKPIT_V2_SELF_CONTAINED_CHARTS = True"),
    ("src/tradebot/operator_cockpit_v2_read_only.py", "def _visualizations("),
    ("src/tradebot/operator_cockpit_v2_read_only.py", "sample_timeline"),
    ("src/tradebot/operator_cockpit_v2_read_only.py", "return_distribution"),
    ("src/tradebot/operator_cockpit_v2_read_only.py", "symbol_performance"),
    ("src/tradebot/operator_cockpit_v2_read_only.py", "timestamp_clusters"),
    ("src/tradebot/operator_cockpit_v2_read_only.py", "slippage_observations"),
    ("src/tradebot/operator_cockpit_v2_read_only.py", "mae_mfe_scatter"),
    ("src/tradebot/operator_cockpit_v2_read_only.py", "performance_comparison"),
    ("src/tradebot/operator_cockpit_v2_read_only.py", "Shadow Audit Visualization"),
    ("src/tradebot/operator_cockpit_v2_read_only.py", "Quant Görseller"),
    ("src/tradebot/operator_cockpit_v2_read_only.py", "READ_ONLY_DASHBOARD_MUTATION_BLOCKED"),
    ("tests/test_operator_cockpit_v2_shadow_audit_visualization_pack_4B436626B.py", "test_26b_http_snapshot_exposes_visualizations_and_mutation_remains_blocked"),
    ("tools/run_operator_cockpit_v2_4B436626B.py", "--once-json"),
    ("tools/start_operator_cockpit_v2_4B436626B.ps1", "--open-browser"),
    ("docs/OPERATOR_COCKPIT_V2_SHADOW_AUDIT_VISUALIZATION_PACK_4B436626B.md", "Operator Cockpit V2 — Shadow Audit Visualization Pack"),
)

COMPILE_TARGETS: tuple[str, ...] = (
    "src/tradebot/operator_cockpit_v2_read_only.py",
    "tools/apply_4B436626B_operator_cockpit_v2_shadow_audit_visualization_pack.py",
    "tools/run_operator_cockpit_v2_4B436626B.py",
    "tests/test_operator_cockpit_v2_shadow_audit_visualization_pack_4B436626B.py",
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
    print("4B.4.3.6.6.26B Operator Cockpit V2 shadow audit visualization pack applied")
    all_ok = True
    for name, ok in results:
        print(f" - {name}: {ok}")
        all_ok = all_ok and ok
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
