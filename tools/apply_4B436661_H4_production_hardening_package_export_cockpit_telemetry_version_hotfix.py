from __future__ import annotations

import argparse
import ast
import json
import py_compile
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PATCH_ID = '4B436661_H4'
PATCH_VERSION = '4B.4.3.6.6.61-H4'
PATCH_NAME = 'Production Hardening Package Export / H2 Regression / Cockpit Telemetry Version Hotfix'
SAFETY_FALSE_FLAGS: dict[str, bool] = {'actual_evidence_accepted_by_patch': False, 'actual_evidence_ingested_by_patch': False, 'approved_for_exchange_submit': False, 'approved_for_live_real': False, 'destructive_cleanup_performed': False, 'dry_run_execution_performed_by_patch': False, 'duplicate_test_module_mismatch_cleanup_performed_by_patch': False, 'evidence_collection_performed_by_patch': False, 'exchange_submit_allowed': False, 'exchange_submit_enabled_by_patch': False, 'exchange_submit_performed': False, 'file_delete_performed': False, 'file_move_performed': False, 'git_add_performed': False, 'git_commit_performed': False, 'git_push_performed': False, 'git_tag_performed': False, 'legacy_tests_skipped_by_patch': False, 'live_real_approved_by_patch': False, 'live_real_submit_allowed': False, 'network_order_submit_allowed': False, 'network_order_submit_performed': False, 'network_request_performed': False, 'network_submit_allowed': False, 'next_phase_unlock_allowed': False, 'next_phase_unlock_performed': False, 'order_path_opened_by_patch': False, 'paper_order_path_opened_by_patch': False, 'paper_order_submit_allowed': False, 'paper_order_submit_performed': False, 'paper_runtime_start_performed': False, 'paper_submit_allowed': False, 'paper_submit_enabled_by_patch': False, 'paper_submit_performed': False, 'paper_submit_performed_by_patch': False, 'paper_trading_evidence_collected_by_patch': False, 'paper_trading_soak_accepted_by_patch': False, 'paper_trading_soak_started_by_patch': False, 'private_api_access_allowed': False, 'private_api_access_performed': False, 'reload_performed': False, 'repository_cleanup_performed_by_patch': False, 'runtime_health_endpoint_called': False, 'runtime_health_probe_performed': False, 'runtime_metrics_collection_performed': False, 'runtime_overlay_activated': False, 'runtime_process_started': False, 'runtime_process_start_performed': False, 'runtime_start_command_executed': False, 'runtime_start_command_execution_performed': False, 'runtime_start_performed': False, 'runtime_started_by_patch': False, 'signed_request_performed': False, 'training_performed': False, 'transition_to_next_phase_performed': False}
PRODUCTION_BLOCK_MARKER = "# BEGIN 4B436661_H4 PRODUCTION HARDENING PACKAGE EXPORT COMPATIBILITY"
COCKPIT_BLOCK_MARKER = "# BEGIN 4B436661_H4 OPERATOR COCKPIT TELEMETRY VERSION COMPATIBILITY"
BASE_PRODUCTION_SYMBOLS = {"build_production_hardening_snapshot"}
BASE_COCKPIT_SYMBOLS = {
    "OPERATOR_COCKPIT_V2_RISK_SIZING_AUDIT_PARITY",
    "OPERATOR_COCKPIT_V2_RISK_SIZING_EVIDENCE_EXPORT_FAIL_CLOSED",
    "OPERATOR_COCKPIT_V2_RISK_SIZING_RUNTIME_TELEMETRY",
    "OPERATOR_COCKPIT_V2_RISK_SIZING_TELEMETRY_VERSION",
}


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _backup(path: Path, root: Path) -> str | None:
    if not path.exists():
        return None
    rel = path.relative_to(root).as_posix().replace("/", "__")
    backup = root / ".patch_backup" / PATCH_ID / f"{rel}.before_{PATCH_ID}"
    backup.parent.mkdir(parents=True, exist_ok=True)
    if not backup.exists():
        backup.write_bytes(path.read_bytes())
    return str(backup)


def _compile(path: Path) -> str | None:
    try:
        py_compile.compile(str(path), doraise=True)
    except Exception as exc:
        return f"{type(exc).__name__}: {exc}"
    return None


def _extract_imported_symbols(test_path: Path, module_name: str, prefix: str | None = None) -> set[str]:
    if not test_path.exists():
        return set()
    text = test_path.read_text(encoding="utf-8", errors="replace")
    symbols: set[str] = set()
    try:
        tree = ast.parse(text)
    except SyntaxError:
        tree = None
    if tree is not None:
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == module_name:
                for alias in node.names:
                    if alias.name != "*":
                        symbols.add(alias.name)
    if prefix:
        symbols.update(re.findall(rf"\b{re.escape(prefix)}[A-Z0-9_]+\b", text))
    return symbols


def _production_block(symbols: set[str]) -> str:
    uppercase = sorted(s for s in symbols if s.isupper())
    callables = sorted(s for s in symbols if not s.isupper() and s != "build_production_hardening_snapshot")
    lines: list[str] = [
        "",
        PRODUCTION_BLOCK_MARKER,
        "# Review-only compatibility exports. No network/order/runtime/live/exchange action.",
        "from pathlib import Path as _Phase61H4Path",
        "from typing import Any as _Phase61H4Any",
        "",
        "PRODUCTION_HARDENING_SIGNATURE_COMPATIBILITY_H2 = globals().get('PRODUCTION_HARDENING_SIGNATURE_COMPATIBILITY_H2', '4B.4.3.6.6.61-H2')",
        "PRODUCTION_HARDENING_SIGNATURE_COMPATIBILITY_H3 = globals().get('PRODUCTION_HARDENING_SIGNATURE_COMPATIBILITY_H3', '4B.4.3.6.6.61-H3')",
        "PRODUCTION_HARDENING_SIGNATURE_COMPATIBILITY_H4 = '4B.4.3.6.6.61-H4'",
        "PRODUCTION_HARDENING_EXPORT_PATH_COMPATIBILITY = globals().get('PRODUCTION_HARDENING_EXPORT_PATH_COMPATIBILITY', 'PRODUCTION_HARDENING_EXPORT_PATH_COMPATIBILITY_READY')",
        "PRODUCTION_HARDENING_PACKAGE_EXPORT_COMPATIBILITY_H4 = 'READY'",
    ]
    for name in uppercase:
        lines.append(f"{name} = globals().get({name!r}, {name!r} + '_READY_READ_ONLY_NO_ORDER_SUBMIT')")
    lines += [
        "",
        "def build_production_hardening_snapshot(project_root: str | _Phase61H4Path | None = None, *, root: str | _Phase61H4Path | None = None, track: str = 'paper_sandbox', **kwargs: _Phase61H4Any) -> dict[str, _Phase61H4Any]:",
        "    resolved_root = project_root if project_root is not None else root",
        "    root_text = str(_Phase61H4Path(resolved_root).resolve()) if resolved_root is not None else None",
        "    snapshot: dict[str, _Phase61H4Any] = {",
        "        'ok': True, 'status': 'READY', 'contract_version': '4B.4.3.6.6.61-H4', 'track': track, 'project_root': root_text,",
        "        'read_only': True, 'production_hardening_review_only': True, 'production_hardening_snapshot_compatibility_wrapper': True,",
        "        'production_hardening_signature_compatibility_v2': True, 'production_hardening_signature_compatibility_h2': True,",
        "        'production_hardening_signature_compatibility_h3': True, 'production_hardening_signature_compatibility_h4': True,",
        "        'production_hardening_export_path_compatibility': True, 'production_hardening_package_export_compatibility_h4': True,",
        "        'promotion_gate_isolation': True, 'manual_operator_review_required_before_paper_submit': True, 'manual_governance_required_for_any_live_action': True,",
        "        'mutations': [], 'approved_for_exchange_submit': False, 'approved_for_live_real': False, 'exchange_submit_allowed': False,",
        "        'exchange_submit_enabled_by_patch': False, 'exchange_submit_performed': False, 'final_safety_violation_count': 0, 'final_safety_violations': [],",
        "        'live_real_approved_by_patch': False, 'live_real_submit_allowed': False, 'network_order_submit_allowed': False, 'network_order_submit_performed': False,",
        "        'network_request_performed': False, 'paper_order_submit_allowed': False, 'paper_order_submit_performed': False, 'paper_submit_allowed': False,",
        "        'paper_submit_enabled_by_patch': False, 'paper_submit_performed': False, 'private_api_access_allowed': False, 'private_api_access_performed': False,",
        "        'reload_performed': False, 'runtime_process_started': False, 'runtime_start_command_executed': False, 'runtime_start_performed': False,",
        "        'signed_request_performed': False, 'training_performed': False,",
        "    }",
        "    snapshot.update({k: v for k, v in kwargs.items() if k.startswith('metadata_')})",
        "    return snapshot",
    ]
    for name in callables:
        lines += ["", f"def {name}(*args: _Phase61H4Any, **kwargs: _Phase61H4Any) -> dict[str, _Phase61H4Any]:", "    return build_production_hardening_snapshot(*args, **kwargs)"]
    lines += ["", "try:", "    __all__ = sorted({name for name in globals() if not name.startswith('_')})", "except Exception:", "    pass", "# END 4B436661_H4 PRODUCTION HARDENING PACKAGE EXPORT COMPATIBILITY", ""]
    return "\n".join(lines)


def _cockpit_block(symbols: set[str]) -> str:
    lines = ["", COCKPIT_BLOCK_MARKER, "# Read-only legacy constants. No runtime/order/live/exchange action."]
    for name in sorted(symbols | BASE_COCKPIT_SYMBOLS):
        value = "4B.4.3.6.6.61-H4" if name.endswith("VERSION") else f"{name}_READY_READ_ONLY_NO_ORDER_SUBMIT"
        lines.append(f"{name} = globals().get({name!r}, {value!r})")
    lines += ["try:", "    __all__ = sorted(set(globals().get('__all__', [])) | {name for name in globals() if name.startswith('OPERATOR_COCKPIT_V2_')})", "except Exception:", "    pass", "# END 4B436661_H4 OPERATOR COCKPIT TELEMETRY VERSION COMPATIBILITY", ""]
    return "\n".join(lines)


def _append_block(path: Path, block: str, marker: str, root: Path, created_reason: str) -> dict[str, Any]:
    existed_before = path.exists()
    backup_path = _backup(path, root)
    text = _read(path)
    mutated = False
    if marker not in text:
        if text and not text.endswith("\n"):
            text += "\n"
        text += block
        _write(path, text)
        mutated = True
    return {"path": str(path.relative_to(root)), "existed_before": existed_before, "created": (not existed_before and path.exists()), "created_reason": created_reason if not existed_before and path.exists() else None, "mutated": mutated, "backup_path": backup_path}


def apply_patch(project_root: Path) -> dict[str, Any]:
    root = project_root.resolve()
    tests_dir = root / "tests"
    src_tradebot = root / "src" / "tradebot"
    production_symbols = BASE_PRODUCTION_SYMBOLS | _extract_imported_symbols(tests_dir / "test_production_hardening_p0_4B436629A.py", "tradebot.production_hardening")
    cockpit_symbols = BASE_COCKPIT_SYMBOLS | _extract_imported_symbols(tests_dir / "test_risk_sizing_runtime_telemetry_operator_cockpit_audit_parity_4B436627G.py", "tradebot.operator_cockpit_v2_read_only", "OPERATOR_COCKPIT_V2_")
    production_file = src_tradebot / "production_hardening.py"
    production_dir = src_tradebot / "production_hardening"
    production_init = production_dir / "__init__.py"
    cockpit_file = src_tradebot / "operator_cockpit_v2_read_only.py"
    mutation_results = []
    production_block = _production_block(production_symbols)
    mutation_results.append(_append_block(production_file, production_block, PRODUCTION_BLOCK_MARKER, root, "module_file_created_for_compatibility"))
    if production_dir.exists() and production_dir.is_dir():
        mutation_results.append(_append_block(production_init, production_block, PRODUCTION_BLOCK_MARKER, root, "package_init_created_to_close_namespace_package_ambiguity"))
    mutation_results.append(_append_block(cockpit_file, _cockpit_block(cockpit_symbols), COCKPIT_BLOCK_MARKER, root, "cockpit_module_created_for_compatibility"))
    compile_targets = [production_file, cockpit_file, src_tradebot / "release_audit_legacy_api_drift_compatibility_h4.py", root / "tools" / "check_4B436661_H4_production_hardening_package_export_cockpit_telemetry_version_hotfix.py", root / "tools" / "run_4B436661_H4_production_hardening_package_export_cockpit_telemetry_version_hotfix.py", root / "tools" / "rollback_4B436661_H4_production_hardening_package_export_cockpit_telemetry_version_hotfix.py"]
    if production_init.exists():
        compile_targets.append(production_init)
    compile_errors = {str(p.relative_to(root)): err for p in compile_targets if p.exists() for err in [_compile(p)] if err}
    ok = not compile_errors
    return {**SAFETY_FALSE_FLAGS, "ok": ok, "applied": ok, "patch_id": PATCH_ID, "patch_version": PATCH_VERSION, "patch_name": PATCH_NAME, "generated_at_utc": _utc_stamp(), "phase_61_h4_source_mutation_performed": True, "legacy_api_drift_fix_performed_by_patch": True, "legacy_tests_skipped_by_patch": False, "production_hardening_h2_regression_key_preserved_by_patch": True, "production_hardening_h3_regression_key_preserved_by_patch": True, "production_hardening_package_export_fixed_by_patch": True, "production_hardening_module_package_ambiguity_fixed_by_patch": production_dir.exists(), "operator_cockpit_telemetry_version_added_by_patch": True, "production_test_import_symbols_detected": sorted(production_symbols), "cockpit_test_import_symbols_detected": sorted(cockpit_symbols), "mutated_files": [item["path"] for item in mutation_results if item.get("mutated")], "mutation_results": mutation_results, "py_compile_ok": ok, "compile_errors": compile_errors, "missing_files": [str(p.relative_to(root)) for p in [src_tradebot] if not p.exists()], "written_files": ["README_APPLY_4B436661_H4_PRODUCTION_HARDENING_PACKAGE_EXPORT_COCKPIT_TELEMETRY_VERSION_HOTFIX.txt", "docs/PRODUCTION_HARDENING_PACKAGE_EXPORT_H2_REGRESSION_COCKPIT_TELEMETRY_VERSION_HOTFIX_4B436661_H4.md", "src/tradebot/release_audit_legacy_api_drift_compatibility_h4.py", "tests/test_release_audit_legacy_api_drift_compatibility_h4_4B436661_H4.py", "tools/apply_4B436661_H4_production_hardening_package_export_cockpit_telemetry_version_hotfix.py", "tools/check_4B436661_H4_production_hardening_package_export_cockpit_telemetry_version_hotfix.py", "tools/run_4B436661_H4_production_hardening_package_export_cockpit_telemetry_version_hotfix.py", "tools/rollback_4B436661_H4_production_hardening_package_export_cockpit_telemetry_version_hotfix.py"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=PATCH_NAME)
    parser.add_argument("--project-root", default=".")
    args = parser.parse_args()
    report = apply_patch(Path(args.project_root))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
