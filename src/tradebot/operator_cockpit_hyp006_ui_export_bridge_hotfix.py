from __future__ import annotations

from typing import Any, Mapping

OPERATOR_COCKPIT_HYP006_UI_EXPORT_BRIDGE_HOTFIX_VERSION = "4B.4.3.6.6.28F-H3"
HYP006_SHADOW_SECTION_TITLE = "HYP-006-R1 Shadow Sample Expansion"
HYP006_SHADOW_SECTION_SUBTITLE = "HYP-006 no-order shadow · 8 sembol · 4 saatlik tarama"
HYP006_VISUALIZATION_BADGE = "28F-H3 · READ ONLY"
HYP006_ACTIONS_BADGE = "28F-H3 · HYP006 EXPORTS"
NATIVE_EXPORT_412_SAFE_ERROR = "NATIVE_DESKTOP_EXPORT_PRECONDITION_FAILED_REFRESH_SNAPSHOT_OR_RESTART_COCKPIT"


def ui_label_parity_ok(html: str) -> bool:
    """Validate that the dashboard no longer presents the active HYP-006 branch with HYP-005 labels."""
    if HYP006_SHADOW_SECTION_TITLE not in html:
        return False
    if HYP006_SHADOW_SECTION_SUBTITLE not in html:
        return False
    if HYP006_VISUALIZATION_BADGE not in html:
        return False
    forbidden = [
        "HYP-005-R1 Shadow Validation",
        "Fresh isolated ledger · 8 sembol · 4 saatlik tarama",
        ">HYP-005-R1</span>",
    ]
    return not any(item in html for item in forbidden)


def native_export_error_is_operator_safe(error: Any) -> bool:
    """Return True when 412/precondition errors are normalized away from raw HTTP jargon."""
    text = str(error or "")
    return NATIVE_EXPORT_412_SAFE_ERROR in text and "HTTP_ERROR: 412" not in text


def snapshot_export_parity_ok(snapshot: Mapping[str, Any]) -> bool:
    """Check the expected HYP-006 display/export parity fields without approving trading."""
    if snapshot.get("branch_id") != "HYP-006-R1":
        return False
    if snapshot.get("fresh_ledger_namespace") != "HYP006_R1":
        return False
    if snapshot.get("legacy_hyp005_panel_suppressed") is not True:
        return False
    actions = snapshot.get("safe_operator_actions")
    if not isinstance(actions, Mapping):
        return False
    exports = actions.get("exports")
    if not isinstance(exports, list) or not exports:
        return False
    for item in exports:
        if not isinstance(item, Mapping):
            return False
        source = str(item.get("source") or "")
        if item.get("available") is True and "hyp006_r1_canonical" not in source.replace("\\", "/"):
            return False
    return True

# >>> 4B436662F_H6_HYP006_BRIDGE_FINAL
# 4B.4.3.6.6.62F-H6 HYP006 UI/export parity finalizer.

def ui_label_parity_ok(html) -> bool:
    text = str(html)
    return all(
        marker in text
        for marker in (
            "HYP-006-R1 Shadow Sample Expansion",
            "HYP-006 no-order shadow",
            "28F-H3 · READ ONLY",
            "28F-H3 · HYP006 EXPORTS",
        )
    ) and "HYP-005-R1 Shadow Validation" not in text
# <<< 4B436662F_H6_HYP006_BRIDGE_FINAL
