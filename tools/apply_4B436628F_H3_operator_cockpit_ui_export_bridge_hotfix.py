from __future__ import annotations

import py_compile
import shutil
from pathlib import Path

CONTRACT_VERSION = "4B.4.3.6.6.28F-H3"
ROOT = Path(__file__).resolve().parents[1]
BACKUP_DIR = ROOT / "tools" / "_patch_backup_4B436628F_H3"
READ_ONLY_FILE = ROOT / "src" / "tradebot" / "operator_cockpit_v2_read_only.py"
DESKTOP_WRAPPER_FILE = ROOT / "src" / "tradebot" / "operator_cockpit_v2_desktop_wrapper.py"

EXPECTED_FILES = [
    "src/tradebot/operator_cockpit_hyp006_ui_export_bridge_hotfix.py",
    "tools/apply_4B436628F_H3_operator_cockpit_ui_export_bridge_hotfix.py",
    "tools/check_4B436628F_H3_operator_cockpit_ui_export_bridge_hotfix.py",
    "tools/rollback_4B436628F_H3_operator_cockpit_ui_export_bridge_hotfix.py",
    "tests/test_operator_cockpit_ui_export_bridge_4B436628F_H3.py",
    "docs/HYP006_R1_OPERATOR_COCKPIT_UI_EXPORT_BRIDGE_4B436628F_H3.md",
]


def _compile(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
        return True
    except py_compile.PyCompileError:
        return False


def _backup_once(path: Path) -> None:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup = BACKUP_DIR / path.name
    if path.exists() and not backup.exists():
        shutil.copy2(path, backup)


def patch_read_only_dashboard() -> dict[str, bool]:
    if not READ_ONLY_FILE.exists():
        return {"read_only_file_exists": False}
    text = READ_ONLY_FILE.read_text(encoding="utf-8")
    original = text
    text = text.replace(
        '<h2>HYP-005-R1 Shadow Validation</h2><small>Fresh isolated ledger · 8 sembol · 4 saatlik tarama</small></div><span class="overview-badge" id="branch">HYP-005-R1</span>',
        '<h2>HYP-006-R1 Shadow Sample Expansion</h2><small>HYP-006 no-order shadow · 8 sembol · 4 saatlik tarama</small></div><span class="overview-badge" id="branch">HYP-006-R1</span>',
    )
    text = text.replace('<span class="overview-badge">26B-H3 · READ ONLY</span>', '<span class="overview-badge">28F-H3 · READ ONLY</span>')
    text = text.replace('<span class="overview-badge">26C · GET ONLY</span>', '<span class="overview-badge">28F-H3 · HYP006 EXPORTS</span>')
    marker = 'OPERATOR_COCKPIT_V2_LEGACY_HYP005_EXPORTS_SUPPRESSED = True\n'
    addition = (
        'OPERATOR_COCKPIT_V2_HYP006_UI_LABEL_PARITY_HOTFIX_VERSION = "4B.4.3.6.6.28F-H3"\n'
        'OPERATOR_COCKPIT_V2_HYP006_UI_LABEL_PARITY = True\n'
        'OPERATOR_COCKPIT_V2_NATIVE_EXPORT_412_HANDLING = True\n'
    )
    if marker in text and 'OPERATOR_COCKPIT_V2_HYP006_UI_LABEL_PARITY_HOTFIX_VERSION' not in text:
        text = text.replace(marker, marker + addition, 1)
    if text != original:
        _backup_once(READ_ONLY_FILE)
        READ_ONLY_FILE.write_text(text, encoding="utf-8")
    return {
        "read_only_file_exists": True,
        "legacy_hyp005_title_removed": "HYP-005-R1 Shadow Validation" not in text,
        "hyp006_title_present": "HYP-006-R1 Shadow Sample Expansion" in text,
        "hyp006_subtitle_present": "HYP-006 no-order shadow" in text,
        "visual_badge_updated": "28F-H3 · READ ONLY" in text,
        "actions_badge_updated": "28F-H3 · HYP006 EXPORTS" in text,
        "read_only_file_patched": text != original,
    }


def patch_desktop_wrapper() -> dict[str, bool]:
    if not DESKTOP_WRAPPER_FILE.exists():
        return {"desktop_wrapper_file_exists": False}
    text = DESKTOP_WRAPPER_FILE.read_text(encoding="utf-8")
    original = text
    marker = 'OPERATOR_COCKPIT_V2_NATIVE_EXPORT_TIMEOUT_CONTRACT = True\n'
    addition = (
        'OPERATOR_COCKPIT_V2_NATIVE_EXPORT_412_HANDLING_HOTFIX_VERSION = "4B.4.3.6.6.28F-H3"\n'
        'OPERATOR_COCKPIT_V2_NATIVE_EXPORT_PRECONDITION_SAFE_MESSAGE = True\n'
    )
    if marker in text and 'OPERATOR_COCKPIT_V2_NATIVE_EXPORT_412_HANDLING_HOTFIX_VERSION' not in text:
        text = text.replace(marker, marker + addition, 1)
    helper = '''def _native_export_http_error_message(error: urllib.error.HTTPError) -> str:\n    """Map local HTTP export failures to operator-safe, fail-closed messages."""\n    code = int(getattr(error, "code", 0) or 0)\n    if code == 412:\n        return "NATIVE_DESKTOP_EXPORT_PRECONDITION_FAILED_REFRESH_SNAPSHOT_OR_RESTART_COCKPIT"\n    if code == 404:\n        return "NATIVE_DESKTOP_EXPORT_SOURCE_NOT_FOUND_REFRESH_SNAPSHOT"\n    if code == 413:\n        return "NATIVE_DESKTOP_EXPORT_TOO_LARGE"\n    return f"NATIVE_DESKTOP_EXPORT_HTTP_ERROR_{code}"\n\n\n'''
    anchor = 'def _is_native_export_timeout(error: BaseException) -> bool:\n'
    if anchor in text and 'def _native_export_http_error_message' not in text:
        text = text.replace(anchor, helper + anchor, 1)
    text = text.replace(
        '    except urllib.error.HTTPError as error:\n        raise DesktopWrapperError(f"NATIVE_DESKTOP_EXPORT_HTTP_ERROR: {error.code}") from error\n',
        '    except urllib.error.HTTPError as error:\n        raise DesktopWrapperError(_native_export_http_error_message(error)) from error\n',
    )
    text = text.replace(
        "if (!result.ok) { feedback('İndirme başarısız: ' + (result.error || 'Bilinmeyen hata')); return; }",
        "if (!result.ok) { const e = result.error || 'Bilinmeyen hata'; feedback(e === 'NATIVE_DESKTOP_EXPORT_PRECONDITION_FAILED_REFRESH_SNAPSHOT_OR_RESTART_COCKPIT' ? 'İndirme hazırlığı başarısız: snapshot yenile veya cockpit’i yeniden başlat; sistem state değiştirilmedi.' : ('İndirme başarısız: ' + e)); return; }",
    )
    text = text.replace(
        "if (!result.ok) { feedback('JSON görünümü açılamadı: ' + (result.error || 'Bilinmeyen hata')); return; }",
        "if (!result.ok) { const e = result.error || 'Bilinmeyen hata'; feedback(e === 'NATIVE_DESKTOP_EXPORT_PRECONDITION_FAILED_REFRESH_SNAPSHOT_OR_RESTART_COCKPIT' ? 'JSON görünümü hazırlanamadı: snapshot yenile veya cockpit’i yeniden başlat; sistem state değiştirilmedi.' : ('JSON görünümü açılamadı: ' + e)); return; }",
    )
    if text != original:
        _backup_once(DESKTOP_WRAPPER_FILE)
        DESKTOP_WRAPPER_FILE.write_text(text, encoding="utf-8")
    return {
        "desktop_wrapper_file_exists": True,
        "native_412_helper_present": "def _native_export_http_error_message" in text,
        "raw_412_error_removed": 'NATIVE_DESKTOP_EXPORT_HTTP_ERROR: {error.code}' not in text,
        "safe_412_message_present": "NATIVE_DESKTOP_EXPORT_PRECONDITION_FAILED_REFRESH_SNAPSHOT_OR_RESTART_COCKPIT" in text,
        "friendly_feedback_present": "snapshot yenile veya cockpit’i yeniden başlat" in text,
        "desktop_wrapper_file_patched": text != original,
    }


def main() -> int:
    checks: dict[str, bool] = {
        "config_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "scheduler_task_created": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "paper_live_order_enablement_present": False,
        **patch_read_only_dashboard(),
        **patch_desktop_wrapper(),
    }
    for relative in EXPECTED_FILES:
        path = ROOT / relative
        checks[f"{relative}_exists"] = path.exists()
        if path.suffix == ".py":
            checks[f"{relative}_py_compile_ok"] = path.exists() and _compile(path)
    checks["read_only_file_py_compile_ok"] = READ_ONLY_FILE.exists() and _compile(READ_ONLY_FILE)
    checks["desktop_wrapper_file_py_compile_ok"] = DESKTOP_WRAPPER_FILE.exists() and _compile(DESKTOP_WRAPPER_FILE)
    print(f"{CONTRACT_VERSION} Operator Cockpit HYP-006 UI label/export bridge hotfix applied")
    for key, value in checks.items():
        print(f" - {key}: {value}")
    required = [
        checks.get("legacy_hyp005_title_removed", False),
        checks.get("hyp006_title_present", False),
        checks.get("visual_badge_updated", False),
        checks.get("actions_badge_updated", False),
        checks.get("native_412_helper_present", False),
        checks.get("raw_412_error_removed", False),
        checks.get("safe_412_message_present", False),
        checks.get("friendly_feedback_present", False),
        checks.get("read_only_file_py_compile_ok", False),
        checks.get("desktop_wrapper_file_py_compile_ok", False),
    ]
    file_checks = [value for key, value in checks.items() if key.endswith("_exists") or key.endswith("_py_compile_ok")]
    return 0 if all(required) and all(file_checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
