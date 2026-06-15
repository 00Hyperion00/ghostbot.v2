from __future__ import annotations

import py_compile
import shutil
from pathlib import Path

CONTRACT_VERSION = "4B.4.3.6.6.28F-H1"
ROOT = Path(__file__).resolve().parents[1]
BACKUP_DIR = ROOT / "tools" / "_patch_backup_4B436628F_H1"
OPERATOR_FILE = ROOT / "src" / "tradebot" / "operator_cockpit_v2_read_only.py"

EXPECTED_FILES = [
    "src/tradebot/operator_cockpit_hyp006_binding.py",
    "tools/apply_4B436628F_H1_operator_cockpit_hyp006_binding.py",
    "tools/check_4B436628F_H1_operator_cockpit_hyp006_binding.py",
    "tools/rollback_4B436628F_H1_operator_cockpit_hyp006_binding.py",
    "tests/test_operator_cockpit_hyp006_binding_4B436628F_H1.py",
    "docs/HYP006_R1_OPERATOR_COCKPIT_BINDING_4B436628F_H1.md",
]

IMPORT_BLOCK = '''try:\n    from .operator_cockpit_hyp006_binding import (\n        OPERATOR_COCKPIT_HYP006_BINDING_VERSION,\n        apply_hyp006_operator_cockpit_binding,\n    )\nexcept Exception:  # pragma: no cover - fail-closed legacy fallback\n    OPERATOR_COCKPIT_HYP006_BINDING_VERSION = "UNAVAILABLE"\n\n    def apply_hyp006_operator_cockpit_binding(snapshot: Mapping[str, Any], project_root: Path) -> dict[str, Any]:\n        return dict(snapshot)\n\n'''


def _compile(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
        return True
    except py_compile.PyCompileError:
        return False


def patch_operator_file() -> dict[str, bool]:
    status: dict[str, bool] = {}
    if not OPERATOR_FILE.exists():
        status["operator_file_exists"] = False
        return status
    status["operator_file_exists"] = True
    text = OPERATOR_FILE.read_text(encoding="utf-8")
    original = text

    if "apply_hyp006_operator_cockpit_binding" not in text:
        marker = "OPERATOR_COCKPIT_V2_CONTRACT_VERSION ="
        if marker not in text:
            status["import_anchor_found"] = False
            return status
        text = text.replace(marker, IMPORT_BLOCK + marker, 1)
        status["import_inserted"] = True
    else:
        status["import_inserted"] = False
    status["import_anchor_found"] = True

    if "return apply_hyp006_operator_cockpit_binding(snapshot, root)" not in text:
        start = '    return {\n        "contract_version": OPERATOR_COCKPIT_V2_CONTRACT_VERSION,'
        if start not in text:
            status["return_anchor_found"] = False
            return status
        text = text.replace(start, '    snapshot = {\n        "contract_version": OPERATOR_COCKPIT_V2_CONTRACT_VERSION,', 1)
        end = '        "operator_guidance": "Müdahale gerekmez. No-order shadow collection otomatik devam ediyor." if sample_count < sample_target else "Shadow hedefi tamamlandı. Bir sonraki audit gate değerlendirilmelidir.",\n    }\n\n\nDASHBOARD_HTML ='
        if end not in text:
            status["return_end_anchor_found"] = False
            return status
        text = text.replace(
            end,
            '        "operator_guidance": "Müdahale gerekmez. No-order shadow collection otomatik devam ediyor." if sample_count < sample_target else "Shadow hedefi tamamlandı. Bir sonraki audit gate değerlendirilmelidir.",\n    }\n    return apply_hyp006_operator_cockpit_binding(snapshot, root)\n\n\nDASHBOARD_HTML =',
            1,
        )
        status["binding_call_inserted"] = True
    else:
        status["binding_call_inserted"] = False
    status["return_anchor_found"] = True
    status["return_end_anchor_found"] = True

    if text != original:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        backup_path = BACKUP_DIR / "operator_cockpit_v2_read_only.py"
        if not backup_path.exists():
            shutil.copy2(OPERATOR_FILE, backup_path)
        OPERATOR_FILE.write_text(text, encoding="utf-8")
        status["operator_file_patched"] = True
    else:
        status["operator_file_patched"] = False
    return status


def main() -> int:
    patch_status = patch_operator_file()
    checks: dict[str, bool] = {
        "config_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "scheduler_task_created": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "paper_live_order_enablement_present": False,
        **patch_status,
    }
    for relative in EXPECTED_FILES:
        path = ROOT / relative
        checks[f"{relative}_exists"] = path.exists()
        if path.suffix == ".py":
            checks[f"{relative}_py_compile_ok"] = path.exists() and _compile(path)
    checks["operator_file_py_compile_ok"] = OPERATOR_FILE.exists() and _compile(OPERATOR_FILE)
    checks["binding_import_present"] = OPERATOR_FILE.exists() and "operator_cockpit_hyp006_binding" in OPERATOR_FILE.read_text(encoding="utf-8")
    checks["binding_call_present"] = OPERATOR_FILE.exists() and "return apply_hyp006_operator_cockpit_binding(snapshot, root)" in OPERATOR_FILE.read_text(encoding="utf-8")
    print(f"{CONTRACT_VERSION} Operator Cockpit HYP-006 dashboard seed binding hotfix applied")
    for key, value in checks.items():
        print(f" - {key}: {value}")
    required_ok = all(value for key, value in checks.items() if key.endswith("_exists") or key.endswith("_py_compile_ok"))
    required_ok = required_ok and checks.get("operator_file_exists", False) and checks.get("import_anchor_found", False) and checks.get("return_anchor_found", False) and checks.get("return_end_anchor_found", False)
    required_ok = required_ok and checks["binding_import_present"] and checks["binding_call_present"] and checks["operator_file_py_compile_ok"]
    return 0 if required_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
