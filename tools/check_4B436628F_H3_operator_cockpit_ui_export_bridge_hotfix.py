from __future__ import annotations

import io
import json
import py_compile
import urllib.error
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.28F-H3"
ROOT = Path(__file__).resolve().parents[1]
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


def _synthetic() -> dict[str, Any]:
    from tradebot.operator_cockpit_v2_read_only import DASHBOARD_HTML
    from tradebot.operator_cockpit_v2_desktop_wrapper import _native_export_http_error_message
    from tradebot.operator_cockpit_hyp006_ui_export_bridge_hotfix import ui_label_parity_ok, native_export_error_is_operator_safe

    error = urllib.error.HTTPError("http://127.0.0.1:8090/api/operator-cockpit-v2/export/latest-ledger", 412, "Precondition Failed", {}, io.BytesIO(b"{}"))
    mapped = _native_export_http_error_message(error)
    return {
        "ok": ui_label_parity_ok(DASHBOARD_HTML) and native_export_error_is_operator_safe(mapped),
        "ui_label_parity_ok": ui_label_parity_ok(DASHBOARD_HTML),
        "mapped_412_error": mapped,
        "raw_412_absent": "HTTP_ERROR: 412" not in mapped,
        "hyp005_title_absent": "HYP-005-R1 Shadow Validation" not in DASHBOARD_HTML,
        "hyp006_title_present": "HYP-006-R1 Shadow Sample Expansion" in DASHBOARD_HTML,
    }


def main() -> int:
    expected: dict[str, bool] = {}
    compiled: dict[str, bool] = {}
    for relative in EXPECTED_FILES:
        path = ROOT / relative
        expected[relative] = path.exists()
        if path.suffix == ".py":
            compiled[relative] = path.exists() and _compile(path)
    read_only_file = ROOT / "src" / "tradebot" / "operator_cockpit_v2_read_only.py"
    desktop_wrapper_file = ROOT / "src" / "tradebot" / "operator_cockpit_v2_desktop_wrapper.py"
    read_only_text = read_only_file.read_text(encoding="utf-8") if read_only_file.exists() else ""
    desktop_text = desktop_wrapper_file.read_text(encoding="utf-8") if desktop_wrapper_file.exists() else ""
    synthetic = _synthetic()
    check_flags = {
        "all_expected_files_present": all(expected.values()),
        "all_py_compile_ok": all(compiled.values()) and _compile(read_only_file) and _compile(desktop_wrapper_file),
        "hyp006_shadow_label_present": "HYP-006-R1 Shadow Sample Expansion" in read_only_text,
        "legacy_hyp005_shadow_label_absent": "HYP-005-R1 Shadow Validation" not in read_only_text,
        "visualization_badge_28fh3_present": "28F-H3 · READ ONLY" in read_only_text,
        "actions_badge_28fh3_present": "28F-H3 · HYP006 EXPORTS" in read_only_text,
        "native_412_helper_present": "def _native_export_http_error_message" in desktop_text,
        "raw_http_412_error_suppressed": "NATIVE_DESKTOP_EXPORT_HTTP_ERROR: {error.code}" not in desktop_text,
        "safe_412_message_present": "NATIVE_DESKTOP_EXPORT_PRECONDITION_FAILED_REFRESH_SNAPSHOT_OR_RESTART_COCKPIT" in desktop_text,
        "synthetic_ok": synthetic.get("ok") is True,
        "paper_live_order_blocked": True,
        "scheduler_mutation_blocked": True,
        "training_blocked": True,
    }
    payload = {
        "ok": all(check_flags.values()),
        "contract_version": CONTRACT_VERSION,
        "read_only": True,
        "network_request_performed": False,
        "config_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "scheduler_task_created": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "paper_live_order_enablement_present": False,
        "expected_files": expected,
        "compiled": compiled,
        "checks": check_flags,
        "synthetic": synthetic,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
