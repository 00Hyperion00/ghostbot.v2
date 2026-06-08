from __future__ import annotations

import py_compile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

CHECKS: tuple[tuple[str, str], ...] = (
    ("src/tradebot/operator_cockpit_v2_desktop_wrapper.py", 'OPERATOR_COCKPIT_V2_EVIDENCE_PACK_TIMEOUT_HOTFIX_VERSION = "4B.4.3.6.6.26D-H2-H2"'),
    ("src/tradebot/operator_cockpit_v2_desktop_wrapper.py", "OPERATOR_COCKPIT_V2_NATIVE_EXPORT_RESPONSE_PREFLIGHT = True"),
    ("src/tradebot/operator_cockpit_v2_desktop_wrapper.py", "OPERATOR_COCKPIT_V2_NATIVE_EXPORT_TIMEOUT_CONTRACT = True"),
    ("src/tradebot/operator_cockpit_v2_desktop_wrapper.py", "DEFAULT_NATIVE_EVIDENCE_PACK_TIMEOUT_SECONDS = 30.0"),
    ("src/tradebot/operator_cockpit_v2_desktop_wrapper.py", "def _native_export_response_preflight(headers: Mapping[str, str], max_bytes: int) -> int | None:"),
    ("src/tradebot/operator_cockpit_v2_desktop_wrapper.py", "def _is_native_export_timeout(error: BaseException) -> bool:"),
    ("src/tradebot/operator_cockpit_v2_desktop_wrapper.py", 'raise DesktopWrapperError("NATIVE_DESKTOP_EXPORT_TIMEOUT") from error'),
    ("src/tradebot/operator_cockpit_v2_desktop_wrapper.py", "return self._fetcher(self.base_url, spec.endpoint, spec.max_bytes, spec.timeout_seconds)"),
    ("tools/run_operator_cockpit_v2_desktop_4B436626D.py", "evidence_pack_timeout_hotfix_version"),
    ("tests/test_operator_cockpit_v2_native_desktop_export_bridge_hotfix_4B436626DH2.py", '_native_export_response_preflight({"Content-Length": "3"}, 2)'),
    ("tests/test_operator_cockpit_v2_native_export_fixture_ledger_seed_hotfix_4B436626DH2H1.py", '_native_export_response_preflight({"Content-Length": "3"}, 2)'),
    ("tests/test_operator_cockpit_v2_evidence_pack_preflight_timeout_hotfix_4B436626DH2H2.py", "test_26dh2h2_slow_header_is_mapped_to_deterministic_timeout_contract"),
    ("docs/OPERATOR_COCKPIT_V2_EVIDENCE_PACK_PREFLIGHT_TIMEOUT_HOTFIX_4B436626DH2H2.md", "Operator Cockpit V2 — Evidence-Pack Response Preflight / Deterministic Native Export Timeout Contract Hotfix"),
)

COMPILE_TARGETS: tuple[str, ...] = (
    "src/tradebot/operator_cockpit_v2_desktop_wrapper.py",
    "tools/run_operator_cockpit_v2_desktop_4B436626D.py",
    "tools/apply_4B436626D_H2_H2_operator_cockpit_v2_evidence_pack_preflight_timeout_hotfix.py",
    "tests/test_operator_cockpit_v2_native_desktop_export_bridge_hotfix_4B436626DH2.py",
    "tests/test_operator_cockpit_v2_native_export_fixture_ledger_seed_hotfix_4B436626DH2H1.py",
    "tests/test_operator_cockpit_v2_evidence_pack_preflight_timeout_hotfix_4B436626DH2H2.py",
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
    print("4B.4.3.6.6.26D-H2-H2 Operator Cockpit V2 evidence-pack response preflight / deterministic native export timeout contract hotfix applied")
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
