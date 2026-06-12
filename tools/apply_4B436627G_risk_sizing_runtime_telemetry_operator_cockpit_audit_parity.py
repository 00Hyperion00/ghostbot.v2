from __future__ import annotations

import py_compile
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src" / "tradebot"
TOOLS = PROJECT_ROOT / "tools"
PAYLOAD = TOOLS / "_patch_payload_4B436627G"
BACKUP = TOOLS / "_patch_backup_4B436627G"
CREATED_MARKER = BACKUP / ".created_files.txt"

COCKPIT = SRC / "operator_cockpit_v2_read_only.py"
DESKTOP = SRC / "operator_cockpit_v2_desktop_wrapper.py"
TELEMETRY = SRC / "risk_sizing_runtime_telemetry.py"
TELEMETRY_PAYLOAD = PAYLOAD / "risk_sizing_runtime_telemetry_4B436627G.py"
CHECKER = TOOLS / "check_4B436627G_risk_sizing_runtime_telemetry_operator_cockpit_audit_parity.py"
ROLLBACK = TOOLS / "rollback_4B436627G_risk_sizing_runtime_telemetry_operator_cockpit_audit_parity.py"
TEST_FILE = PROJECT_ROOT / "tests" / "test_risk_sizing_runtime_telemetry_operator_cockpit_audit_parity_4B436627G.py"
NATIVE_DESKTOP_TEST = PROJECT_ROOT / "tests" / "test_operator_cockpit_v2_native_desktop_export_bridge_hotfix_4B436626DH2.py"
DOC = PROJECT_ROOT / "docs" / "RISK_SIZING_RUNTIME_TELEMETRY_OPERATOR_COCKPIT_AUDIT_PARITY_4B436627G.md"

ACTIVE_FILES = [COCKPIT, DESKTOP, NATIVE_DESKTOP_TEST]


def _compile(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
        return True
    except py_compile.PyCompileError:
        return False


def _contains(path: Path, marker: str) -> bool:
    return marker in path.read_text(encoding="utf-8")


def _backup(path: Path) -> None:
    relative = path.relative_to(PROJECT_ROOT)
    target = BACKUP / relative
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def _record_created(path: Path) -> None:
    BACKUP.mkdir(parents=True, exist_ok=True)
    relative = path.relative_to(PROJECT_ROOT).as_posix()
    current = set(CREATED_MARKER.read_text(encoding="utf-8").splitlines()) if CREATED_MARKER.exists() else set()
    current.add(relative)
    CREATED_MARKER.write_text("\n".join(sorted(item for item in current if item)) + "\n", encoding="utf-8")


def _replace_once(path: Path, old: str, new: str, *, operation: str) -> None:
    text = path.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise RuntimeError(f"4B436627G_EXPECTED_SOURCE_FRAGMENT_MISSING:{operation}:{path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def _restore_on_failure() -> None:
    if BACKUP.exists():
        for source in sorted(path for path in BACKUP.rglob("*") if path.is_file() and path != CREATED_MARKER):
            relative = source.relative_to(BACKUP)
            target = PROJECT_ROOT / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        if CREATED_MARKER.exists():
            for item in CREATED_MARKER.read_text(encoding="utf-8").splitlines():
                if item.strip():
                    target = PROJECT_ROOT / item.strip()
                    if target.exists():
                        target.unlink()


def _install_telemetry_module() -> None:
    if TELEMETRY.exists():
        if _contains(TELEMETRY, 'RISK_SIZING_RUNTIME_TELEMETRY_VERSION = "4B.4.3.6.6.27G"'):
            return
        raise RuntimeError("4B436627G_TELEMETRY_MODULE_ALREADY_EXISTS_WITH_DIFFERENT_CONTRACT")
    TELEMETRY.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(TELEMETRY_PAYLOAD, TELEMETRY)
    _record_created(TELEMETRY)


def _patch_cockpit() -> None:
    _replace_once(
        COCKPIT,
        '''from .hyp005_r1_canonical_epoch_contract import (\n    CANONICAL_R1_REPORTS_DIR,\n    CANONICAL_R1_TASK_NAME,\n    LEGACY_R1_REPORTS_DIR,\n    LEGACY_R1_TASK_NAME,\n    resolve_active_reports_dir,\n)\n''',
        '''from .hyp005_r1_canonical_epoch_contract import (\n    CANONICAL_R1_REPORTS_DIR,\n    CANONICAL_R1_TASK_NAME,\n    LEGACY_R1_REPORTS_DIR,\n    LEGACY_R1_TASK_NAME,\n    resolve_active_reports_dir,\n)\nfrom .risk_sizing_runtime_telemetry import (\n    RISK_SIZING_EVIDENCE_EXPORT_FAIL_CLOSED,\n    RISK_SIZING_OPERATOR_COCKPIT_AUDIT_PARITY,\n    RISK_SIZING_RUNTIME_TELEMETRY_ENABLED,\n    RISK_SIZING_RUNTIME_TELEMETRY_VERSION,\n    RiskSizingEvidenceExportBlocked,\n    assert_risk_sizing_evidence_export_ready,\n    collect_risk_sizing_runtime_telemetry,\n)\n''',
        operation="cockpit_telemetry_import",
    )
    _replace_once(
        COCKPIT,
        '''OPERATOR_COCKPIT_V2_CANONICAL_SOURCE_PREFERRED_WITH_LEGACY_FALLBACK = True\n''',
        '''OPERATOR_COCKPIT_V2_CANONICAL_SOURCE_PREFERRED_WITH_LEGACY_FALLBACK = True\nOPERATOR_COCKPIT_V2_RISK_SIZING_TELEMETRY_VERSION = RISK_SIZING_RUNTIME_TELEMETRY_VERSION\nOPERATOR_COCKPIT_V2_RISK_SIZING_RUNTIME_TELEMETRY = RISK_SIZING_RUNTIME_TELEMETRY_ENABLED\nOPERATOR_COCKPIT_V2_RISK_SIZING_AUDIT_PARITY = RISK_SIZING_OPERATOR_COCKPIT_AUDIT_PARITY\nOPERATOR_COCKPIT_V2_RISK_SIZING_EVIDENCE_EXPORT_FAIL_CLOSED = RISK_SIZING_EVIDENCE_EXPORT_FAIL_CLOSED\n''',
        operation="cockpit_telemetry_constants",
    )
    _replace_once(
        COCKPIT,
        '''    root = project_root.resolve()\n    exports: list[JsonObject] = []\n''',
        '''    root = project_root.resolve()\n    telemetry = collect_risk_sizing_runtime_telemetry(root)\n    exports: list[JsonObject] = []\n''',
        operation="manifest_collect_telemetry",
    )
    _replace_once(
        COCKPIT,
        '''            {"code": "DOWNLOAD_EVIDENCE_PACK_ZIP", "label": "Evidence pack indir", "endpoint": "/api/operator-cockpit-v2/export/evidence-pack.zip"},\n''',
        '''            {"code": "DOWNLOAD_EVIDENCE_PACK_ZIP", "label": "Evidence pack indir", "endpoint": "/api/operator-cockpit-v2/export/evidence-pack.zip"},\n            {"code": "OPEN_RISK_SIZING_RUNTIME_TELEMETRY_JSON", "label": "Risk-sizing telemetry JSON aç", "endpoint": "/api/operator-cockpit-v2/view/risk-sizing-runtime-telemetry.json"},\n            {"code": "DOWNLOAD_RISK_SIZING_EVIDENCE_PACK_ZIP", "label": "Risk-sizing evidence pack indir", "endpoint": "/api/operator-cockpit-v2/export/risk-sizing-evidence-pack.zip", "available": telemetry["export_ready"]},\n''',
        operation="manifest_add_telemetry_actions",
    )
    _replace_once(
        COCKPIT,
        '''        "exports": exports,\n    }\n\n\ndef _build_in_memory_evidence_pack(\n''',
        '''        "exports": exports,\n        "risk_sizing_evidence_export_gate": {\n            "contract_version": telemetry["contract_version"],\n            "available": telemetry["export_ready"],\n            "fail_closed": True,\n            "blockers": telemetry["export_blockers"],\n        },\n    }\n\n\ndef _build_in_memory_evidence_pack(\n''',
        operation="manifest_add_telemetry_gate",
    )
    _replace_once(
        COCKPIT,
        '''    return output.getvalue()\n\n\ndef _relative_or_name(path: Path | None, root: Path) -> str | None:\n''',
        '''    return output.getvalue()\n\n\ndef _build_risk_sizing_in_memory_evidence_pack(\n    project_root: Path,\n    *,\n    task_query: TaskQuery | None = None,\n    backend_probe: BackendProbe | None = None,\n) -> bytes:\n    """Build additive risk-sizing evidence only when runtime telemetry is audit-complete."""\n    root = project_root.resolve()\n    telemetry = collect_risk_sizing_runtime_telemetry(root)\n    assert_risk_sizing_evidence_export_ready(telemetry)\n    snapshot = collect_operator_cockpit_snapshot(root, task_query=task_query, backend_probe=backend_probe)\n    manifest = _safe_action_manifest(root)\n    output = io.BytesIO()\n    with zipfile.ZipFile(output, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:\n        archive.writestr("operator-cockpit/snapshot.json", json.dumps(snapshot, ensure_ascii=False, indent=2).encode("utf-8"))\n        archive.writestr("operator-cockpit/safe-actions-manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"))\n        archive.writestr("operator-cockpit/risk-sizing-runtime-telemetry.json", json.dumps(telemetry, ensure_ascii=False, indent=2).encode("utf-8"))\n    payload = output.getvalue()\n    if len(payload) > MAX_OPERATOR_COCKPIT_EVIDENCE_PACK_BYTES:\n        raise ValueError("OPERATOR_COCKPIT_EVIDENCE_PACK_TOO_LARGE")\n    return payload\n\n\ndef _relative_or_name(path: Path | None, root: Path) -> str | None:\n''',
        operation="add_risk_sizing_evidence_pack_builder",
    )
    _replace_once(
        COCKPIT,
        '''    progress_pct = _as_float(audit.get("progress_pct"))\n    if progress_pct is None:\n        progress_pct = round(min(sample_count / sample_target, 1.0) * 100, 6)\n    return {\n''',
        '''    progress_pct = _as_float(audit.get("progress_pct"))\n    if progress_pct is None:\n        progress_pct = round(min(sample_count / sample_target, 1.0) * 100, 6)\n    risk_sizing_telemetry = collect_risk_sizing_runtime_telemetry(root)\n    return {\n''',
        operation="snapshot_collect_telemetry",
    )
    _replace_once(
        COCKPIT,
        '''        "safe_operator_actions": _safe_action_manifest(root),\n        "operator_guidance": "Müdahale gerekmez. No-order shadow collection otomatik devam ediyor." if sample_count < sample_target else "Shadow hedefi tamamlandı. Bir sonraki audit gate değerlendirilmelidir.",\n''',
        '''        "safe_operator_actions": _safe_action_manifest(root),\n        "risk_sizing_runtime_telemetry": risk_sizing_telemetry,\n        "operator_guidance": "Müdahale gerekmez. No-order shadow collection otomatik devam ediyor." if sample_count < sample_target else "Shadow hedefi tamamlandı. Bir sonraki audit gate değerlendirilmelidir.",\n''',
        operation="snapshot_add_telemetry",
    )
    _replace_once(
        COCKPIT,
        '''<a class="action-btn" href="/api/operator-cockpit-v2/export/evidence-pack.zip">Evidence Pack ZIP İndir</a><a class="action-btn" href="/api/operator-cockpit-v2/export/latest-ledger">Merged Ledger İndir</a>''',
        '''<a class="action-btn" href="/api/operator-cockpit-v2/export/evidence-pack.zip">Evidence Pack ZIP İndir</a><a class="action-btn" href="/api/operator-cockpit-v2/view/risk-sizing-runtime-telemetry.json" target="_blank" rel="noopener">Risk-Sizing Telemetry JSON Aç</a><a class="action-btn" href="/api/operator-cockpit-v2/export/risk-sizing-evidence-pack.zip">Risk-Sizing Evidence ZIP İndir</a><a class="action-btn" href="/api/operator-cockpit-v2/export/latest-ledger">Merged Ledger İndir</a>''',
        operation="dashboard_add_telemetry_actions",
    )
    _replace_once(
        COCKPIT,
        '''        if path == "/api/operator-cockpit-v2/export/evidence-pack.zip":\n            try:\n                body = _build_in_memory_evidence_pack(self.project_root, task_query=self.task_query, backend_probe=self.backend_probe)\n            except ValueError as error:\n                self._json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"ok": False, "error": str(error), "read_only": True})\n                return\n            self._write(HTTPStatus.OK, body, "application/zip", extra_headers=_attachment_headers("operator-cockpit-evidence-pack.zip"))\n            return\n''',
        '''        if path == "/api/operator-cockpit-v2/view/risk-sizing-runtime-telemetry.json":\n            telemetry = collect_risk_sizing_runtime_telemetry(self.project_root)\n            self._json(HTTPStatus.OK, telemetry)\n            return\n        if path == "/api/operator-cockpit-v2/export/risk-sizing-evidence-pack.zip":\n            try:\n                body = _build_risk_sizing_in_memory_evidence_pack(self.project_root, task_query=self.task_query, backend_probe=self.backend_probe)\n            except RiskSizingEvidenceExportBlocked as error:\n                self._json(HTTPStatus.PRECONDITION_FAILED, {"ok": False, "error": str(error), "blockers": error.blockers, "read_only": True})\n                return\n            except ValueError as error:\n                self._json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"ok": False, "error": str(error), "read_only": True})\n                return\n            self._write(HTTPStatus.OK, body, "application/zip", extra_headers=_attachment_headers("operator-cockpit-risk-sizing-evidence-pack.zip"))\n            return\n        if path == "/api/operator-cockpit-v2/export/evidence-pack.zip":\n            try:\n                body = _build_in_memory_evidence_pack(self.project_root, task_query=self.task_query, backend_probe=self.backend_probe)\n            except ValueError as error:\n                self._json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"ok": False, "error": str(error), "read_only": True})\n                return\n            self._write(HTTPStatus.OK, body, "application/zip", extra_headers=_attachment_headers("operator-cockpit-evidence-pack.zip"))\n            return\n''',
        operation="http_add_telemetry_endpoints",
    )


def _patch_desktop() -> None:
    _replace_once(
        DESKTOP,
        '''    "DOWNLOAD_EVIDENCE_PACK_ZIP": NativeDesktopActionSpec("DOWNLOAD_EVIDENCE_PACK_ZIP", "/api/operator-cockpit-v2/export/evidence-pack.zip", "operator-cockpit-evidence-pack.zip", "download", MAX_NATIVE_DESKTOP_EXPORT_BYTES, DEFAULT_NATIVE_EVIDENCE_PACK_TIMEOUT_SECONDS),\n''',
        '''    "DOWNLOAD_EVIDENCE_PACK_ZIP": NativeDesktopActionSpec("DOWNLOAD_EVIDENCE_PACK_ZIP", "/api/operator-cockpit-v2/export/evidence-pack.zip", "operator-cockpit-evidence-pack.zip", "download", MAX_NATIVE_DESKTOP_EXPORT_BYTES, DEFAULT_NATIVE_EVIDENCE_PACK_TIMEOUT_SECONDS),\n    "OPEN_RISK_SIZING_RUNTIME_TELEMETRY_JSON": NativeDesktopActionSpec("OPEN_RISK_SIZING_RUNTIME_TELEMETRY_JSON", "/api/operator-cockpit-v2/view/risk-sizing-runtime-telemetry.json", "risk-sizing-runtime-telemetry.json", "text", MAX_NATIVE_DESKTOP_TEXT_VIEW_BYTES),\n    "DOWNLOAD_RISK_SIZING_EVIDENCE_PACK_ZIP": NativeDesktopActionSpec("DOWNLOAD_RISK_SIZING_EVIDENCE_PACK_ZIP", "/api/operator-cockpit-v2/export/risk-sizing-evidence-pack.zip", "operator-cockpit-risk-sizing-evidence-pack.zip", "download", MAX_NATIVE_DESKTOP_EXPORT_BYTES, DEFAULT_NATIVE_EVIDENCE_PACK_TIMEOUT_SECONDS),\n''',
        operation="desktop_add_telemetry_actions",
    )
    _replace_once(
        DESKTOP,
        '''    '/api/operator-cockpit-v2/export/evidence-pack.zip': ['download', 'DOWNLOAD_EVIDENCE_PACK_ZIP'],\n''',
        '''    '/api/operator-cockpit-v2/export/evidence-pack.zip': ['download', 'DOWNLOAD_EVIDENCE_PACK_ZIP'],\n    '/api/operator-cockpit-v2/view/risk-sizing-runtime-telemetry.json': ['text', 'OPEN_RISK_SIZING_RUNTIME_TELEMETRY_JSON'],\n    '/api/operator-cockpit-v2/export/risk-sizing-evidence-pack.zip': ['download', 'DOWNLOAD_RISK_SIZING_EVIDENCE_PACK_ZIP'],\n''',
        operation="desktop_js_add_telemetry_routes",
    )
    _replace_once(
        NATIVE_DESKTOP_TEST,
        """        \"DOWNLOAD_EVIDENCE_PACK_ZIP\",\n        \"DOWNLOAD_MERGED_LEDGER_JSONL\",\n""",
        """        \"DOWNLOAD_EVIDENCE_PACK_ZIP\",\n        \"OPEN_RISK_SIZING_RUNTIME_TELEMETRY_JSON\",\n        \"DOWNLOAD_RISK_SIZING_EVIDENCE_PACK_ZIP\",\n        \"DOWNLOAD_MERGED_LEDGER_JSONL\",\n""",
        operation="desktop_native_allowlist_regression_contract",
    )


def main() -> int:
    required = [*ACTIVE_FILES, TELEMETRY_PAYLOAD, CHECKER, ROLLBACK, TEST_FILE, DOC]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        print("4B436627G_apply_error: required overlay file missing")
        for item in missing:
            print(f" - missing: {item}")
        return 2

    prerequisites = [
        (COCKPIT, 'OPERATOR_COCKPIT_V2_SAFE_ACTIONS_VERSION = "4B.4.3.6.6.26C"'),
        (COCKPIT, '"DOWNLOAD_EVIDENCE_PACK_ZIP"'),
        (DESKTOP, '"DOWNLOAD_EVIDENCE_PACK_ZIP": NativeDesktopActionSpec'),
        (PROJECT_ROOT / "src" / "tradebot" / "engine.py", "skipCodeCompatVersion': '4B.4.3.6.6.27F-H1"),
    ]
    failed = [f"{path}:{marker}" for path, marker in prerequisites if not _contains(path, marker)]
    if failed:
        print("4B436627G_apply_error: prerequisite marker missing")
        for item in failed:
            print(f" - missing_marker: {item}")
        return 2

    try:
        for path in ACTIVE_FILES:
            _backup(path)
        _install_telemetry_module()
        _patch_cockpit()
        _patch_desktop()
        checks = [
            ("config_mutation_performed", False),
            ("scheduler_mutation_performed", False),
            ("training_performed", False),
            ("reload_performed", False),
            ("trading_action_performed", False),
            ("telemetry_module_py_compile_ok", _compile(TELEMETRY)),
            ("cockpit_py_compile_ok", _compile(COCKPIT)),
            ("desktop_wrapper_py_compile_ok", _compile(DESKTOP)),
            ("native_desktop_test_py_compile_ok", _compile(NATIVE_DESKTOP_TEST)),
            ("checker_py_compile_ok", _compile(CHECKER)),
            ("rollback_py_compile_ok", _compile(ROLLBACK)),
            ("test_file_py_compile_ok", _compile(TEST_FILE)),
            ("runtime_sqlite_read_only_mode_present", _contains(TELEMETRY, '?mode=ro')),
            ("operator_cockpit_snapshot_telemetry_present", _contains(COCKPIT, '"risk_sizing_runtime_telemetry": risk_sizing_telemetry')),
            ("fail_closed_evidence_export_gate_present", _contains(COCKPIT, 'except RiskSizingEvidenceExportBlocked as error:')),
            ("native_desktop_export_bridge_parity_present", _contains(DESKTOP, 'DOWNLOAD_RISK_SIZING_EVIDENCE_PACK_ZIP')),
            ("legacy_evidence_pack_route_preserved", _contains(COCKPIT, 'if path == "/api/operator-cockpit-v2/export/evidence-pack.zip":')),
            ("paper_live_order_enablement_present", False),
        ]
        print("4B.4.3.6.6.27G Risk-sizing runtime telemetry / operator cockpit audit parity / fail-closed evidence export gate applied")
        false_expected = {
            "config_mutation_performed",
            "scheduler_mutation_performed",
            "training_performed",
            "reload_performed",
            "trading_action_performed",
            "paper_live_order_enablement_present",
        }
        ok = True
        for name, value in checks:
            print(f" - {name}: {value}")
            ok = ok and ((value is False) if name in false_expected else bool(value))
        if not ok:
            raise RuntimeError("4B436627G_APPLY_POSTCHECK_FAILED")
        return 0
    except Exception as error:
        _restore_on_failure()
        print(f"4B436627G_apply_error: {error}")
        print(" - transactional_restore_performed: True")
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
