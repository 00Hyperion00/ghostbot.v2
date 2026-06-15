from __future__ import annotations

import io
import urllib.error


def test_hyp006_shadow_section_label_replaces_hyp005_legacy_title() -> None:
    from tradebot.operator_cockpit_v2_read_only import DASHBOARD_HTML
    from tradebot.operator_cockpit_hyp006_ui_export_bridge_hotfix import ui_label_parity_ok

    assert "HYP-006-R1 Shadow Sample Expansion" in DASHBOARD_HTML
    assert "HYP-006 no-order shadow" in DASHBOARD_HTML
    assert "28F-H3 · READ ONLY" in DASHBOARD_HTML
    assert "28F-H3 · HYP006 EXPORTS" in DASHBOARD_HTML
    assert "HYP-005-R1 Shadow Validation" not in DASHBOARD_HTML
    assert ui_label_parity_ok(DASHBOARD_HTML)


def test_native_desktop_export_412_maps_to_operator_safe_message() -> None:
    from tradebot.operator_cockpit_v2_desktop_wrapper import _native_export_http_error_message
    from tradebot.operator_cockpit_hyp006_ui_export_bridge_hotfix import (
        NATIVE_EXPORT_412_SAFE_ERROR,
        native_export_error_is_operator_safe,
    )

    error = urllib.error.HTTPError(
        "http://127.0.0.1:8090/api/operator-cockpit-v2/export/latest-ledger",
        412,
        "Precondition Failed",
        {},
        io.BytesIO(b"{}"),
    )
    mapped = _native_export_http_error_message(error)
    assert mapped == NATIVE_EXPORT_412_SAFE_ERROR
    assert native_export_error_is_operator_safe(mapped)
    assert "HTTP_ERROR: 412" not in mapped


def test_h3_does_not_enable_mutating_actions() -> None:
    from tradebot.operator_cockpit_hyp006_ui_export_bridge_hotfix import OPERATOR_COCKPIT_HYP006_UI_EXPORT_BRIDGE_HOTFIX_VERSION
    from tradebot.operator_cockpit_v2_read_only import OPERATOR_COCKPIT_V2_NO_CONFIG_MUTATION, OPERATOR_COCKPIT_V2_NO_SCHEDULER_MUTATION, OPERATOR_COCKPIT_V2_NO_TRADING_ACTION

    assert OPERATOR_COCKPIT_HYP006_UI_EXPORT_BRIDGE_HOTFIX_VERSION == "4B.4.3.6.6.28F-H3"
    assert OPERATOR_COCKPIT_V2_NO_CONFIG_MUTATION is True
    assert OPERATOR_COCKPIT_V2_NO_SCHEDULER_MUTATION is True
    assert OPERATOR_COCKPIT_V2_NO_TRADING_ACTION is True
