from __future__ import annotations

import py_compile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

CHECKS: tuple[tuple[str, str], ...] = (
    ("src/tradebot/operator_cockpit_v2_desktop_wrapper.py", 'OPERATOR_COCKPIT_V2_NATIVE_EXPORT_BRIDGE_HOTFIX_VERSION = "4B.4.3.6.6.26D-H2"'),
    ("src/tradebot/operator_cockpit_v2_desktop_wrapper.py", '"DOWNLOAD_MERGED_LEDGER_JSONL": NativeDesktopActionSpec'),
    ("src/tradebot/operator_cockpit_v2_desktop_wrapper.py", '"/api/operator-cockpit-v2/export/latest-ledger"'),
    ("tests/test_operator_cockpit_v2_native_desktop_export_bridge_hotfix_4B436626DH2.py", "def _seed_minimal_isolated_r1_ledger(project_root: Path) -> Path:"),
    ("tests/test_operator_cockpit_v2_native_desktop_export_bridge_hotfix_4B436626DH2.py", "_seed_minimal_isolated_r1_ledger(tmp_path)"),
    ("tests/test_operator_cockpit_v2_native_export_fixture_ledger_seed_hotfix_4B436626DH2H1.py", 'NATIVE_EXPORT_FIXTURE_HOTFIX_VERSION = "4B.4.3.6.6.26D-H2-H1"'),
    ("tests/test_operator_cockpit_v2_native_export_fixture_ledger_seed_hotfix_4B436626DH2H1.py", "test_26dh2h1_seeded_fixture_returns_latest_ledger_200_and_contains_btcusdt"),
    ("tests/test_operator_cockpit_v2_native_export_fixture_ledger_seed_hotfix_4B436626DH2H1.py", "test_26dh2h1_missing_ledger_contract_is_deterministic_404"),
    ("tests/test_operator_cockpit_v2_native_export_fixture_ledger_seed_hotfix_4B436626DH2H1.py", "test_26dh2h1_evidence_pack_size_limit_remains_deterministic_with_seeded_ledger"),
    ("docs/OPERATOR_COCKPIT_V2_NATIVE_EXPORT_FIXTURE_LEDGER_SEED_HOTFIX_4B436626DH2H1.md", "Operator Cockpit V2 — Native Export Integration Test Fixture Ledger Seed / Deterministic 404 Contract Hotfix"),
)

COMPILE_TARGETS: tuple[str, ...] = (
    "src/tradebot/operator_cockpit_v2_desktop_wrapper.py",
    "tools/apply_4B436626D_H2_H1_operator_cockpit_v2_native_export_fixture_ledger_seed_hotfix.py",
    "tests/test_operator_cockpit_v2_native_desktop_export_bridge_hotfix_4B436626DH2.py",
    "tests/test_operator_cockpit_v2_native_export_fixture_ledger_seed_hotfix_4B436626DH2H1.py",
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
    print("4B.4.3.6.6.26D-H2-H1 Operator Cockpit V2 native export integration fixture ledger seed / deterministic 404 contract hotfix applied")
    print(" - production_source_mutation_performed: False")
    print(" - config_mutation_performed: False")
    print(" - scheduler_mutation_performed: False")
    print(" - trading_action_performed: False")
    all_ok = True
    for name, ok in results:
        print(f" - {name}: {ok}")
        all_ok = all_ok and ok
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
