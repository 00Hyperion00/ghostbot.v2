from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import tradebot.operator_cockpit_v2_desktop_wrapper as desktop
from tradebot.operator_cockpit_v2_desktop_wrapper import (
    MAX_NATIVE_DESKTOP_EXPORT_BYTES,
    NATIVE_DESKTOP_ACTIONS,
    NATIVE_DESKTOP_EXPORT_BRIDGE_JS,
    OPERATOR_COCKPIT_V2_NATIVE_DESKTOP_EXPORT_BRIDGE,
    OPERATOR_COCKPIT_V2_NATIVE_EXPORT_ALLOWLIST_ONLY,
    OPERATOR_COCKPIT_V2_NATIVE_EXPORT_BRIDGE_HOTFIX_VERSION,
    OPERATOR_COCKPIT_V2_NATIVE_EXPORT_LOOPBACK_ONLY,
    OPERATOR_COCKPIT_V2_NATIVE_SAVE_DIALOG_DOWNLOADS,
    DesktopWrapperError,
    NativeDesktopExportBridge,
    _attach_native_desktop_export_bridge,
    _dashboard_origin,
    _normalize_loopback_base_url,
    _normalize_save_dialog_result,
    _read_bounded_local_get,
    launch_desktop_shell,
    start_local_cockpit_server,
)




def _seed_minimal_isolated_r1_ledger(project_root: Path) -> Path:
    """Create one deterministic isolated-R1 merged-ledger fixture row for local export integration tests."""
    reports_dir = project_root / "reports" / "hyp005_r1_isolated"
    reports_dir.mkdir(parents=True, exist_ok=True)
    ledger = reports_dir / "4B436625X_hyp005_shadow_merged_ledger_20260608_120000.jsonl"
    ledger.write_text(
        json.dumps(
            {
                "symbol": "BTCUSDT",
                "timestamp_utc": "2026-06-08T12:00:00+00:00",
                "observation_id": "HYP-005-BTCUSDT-4h-fixture-20260608T120000Z",
                "spread_slippage_proxy_bps": 4.25,
                "forward_return_bps_final": 12.5,
                "mae_bps": -18.0,
                "mfe_bps": 31.0,
            },
            ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )
    return ledger


class FakeLoadedEvent:
    def __init__(self) -> None:
        self.handlers: list[Any] = []

    def __iadd__(self, handler: Any) -> "FakeLoadedEvent":
        self.handlers.append(handler)
        return self

    def fire(self) -> None:
        for handler in list(self.handlers):
            handler()


class FakeWindow:
    def __init__(self, *, save_result: Any = None) -> None:
        self.save_result = save_result
        self.dialog_calls: list[tuple[object, str]] = []
        self.evaluated_js: list[str] = []
        self.events = SimpleNamespace(loaded=FakeLoadedEvent())

    def create_file_dialog(self, dialog_type: object, *, save_filename: str) -> Any:
        self.dialog_calls.append((dialog_type, save_filename))
        return self.save_result

    def evaluate_js(self, script: str) -> None:
        self.evaluated_js.append(script)


def test_26dh2_declares_native_save_dialog_bridge_without_trading_mutation() -> None:
    assert OPERATOR_COCKPIT_V2_NATIVE_EXPORT_BRIDGE_HOTFIX_VERSION == "4B.4.3.6.6.26D-H2"
    assert OPERATOR_COCKPIT_V2_NATIVE_DESKTOP_EXPORT_BRIDGE is True
    assert OPERATOR_COCKPIT_V2_NATIVE_SAVE_DIALOG_DOWNLOADS is True
    assert OPERATOR_COCKPIT_V2_NATIVE_EXPORT_ALLOWLIST_ONLY is True
    assert OPERATOR_COCKPIT_V2_NATIVE_EXPORT_LOOPBACK_ONLY is True
    assert desktop.OPERATOR_COCKPIT_V2_NO_CONFIG_MUTATION is True
    assert desktop.OPERATOR_COCKPIT_V2_NO_SCHEDULER_MUTATION is True
    assert desktop.OPERATOR_COCKPIT_V2_NO_TRADING_ACTION is True


def test_26dh2_action_allowlist_is_fixed_and_loopback_base_url_rejects_external_origins() -> None:
    assert set(NATIVE_DESKTOP_ACTIONS) == {
        "DOWNLOAD_SNAPSHOT_JSON",
        "OPEN_LATEST_AUDIT_JSON",
        "OPEN_ACTION_MANIFEST",
        "DOWNLOAD_EVIDENCE_PACK_ZIP",
        "DOWNLOAD_MERGED_LEDGER_JSONL",
    }
    assert all(spec.endpoint.startswith("/api/operator-cockpit-v2/") for spec in NATIVE_DESKTOP_ACTIONS.values())
    assert _normalize_loopback_base_url("http://127.0.0.1:8090") == "http://127.0.0.1:8090"
    assert _dashboard_origin("http://127.0.0.1:8090/dashboard") == "http://127.0.0.1:8090"
    with pytest.raises(DesktopWrapperError, match="NATIVE_DESKTOP_EXPORT_NON_LOOPBACK_BLOCKED"):
        _normalize_loopback_base_url("https://example.com:443")
    with pytest.raises(DesktopWrapperError, match="NATIVE_DESKTOP_EXPORT_NON_LOOPBACK_BLOCKED"):
        _normalize_loopback_base_url("http://192.168.1.20:8090")
    with pytest.raises(DesktopWrapperError, match="NATIVE_DESKTOP_EXPORT_BASE_URL_INVALID"):
        _normalize_loopback_base_url("http://127.0.0.1:8090/dashboard")


def test_26dh2_native_snapshot_download_uses_save_dialog_allowlist_and_atomic_writer(tmp_path: Path) -> None:
    destination = tmp_path / "snapshot.json"
    fetch_calls: list[tuple[str, str, int, float]] = []
    write_calls: list[tuple[Path, bytes]] = []

    def fetcher(base_url: str, endpoint: str, max_bytes: int, timeout_seconds: float) -> bytes:
        fetch_calls.append((base_url, endpoint, max_bytes, timeout_seconds))
        return b'{"ok":true}'

    def writer(path: Path, payload: bytes) -> None:
        write_calls.append((path, payload))
        path.write_bytes(payload)

    window = FakeWindow(save_result=(str(destination),))
    bridge = NativeDesktopExportBridge("http://127.0.0.1:8090", fetcher=fetcher, writer=writer)
    bridge.bind_window(window, SimpleNamespace(SAVE_DIALOG="SAVE"))
    result = bridge.export_file("DOWNLOAD_SNAPSHOT_JSON")

    assert result == {"ok": True, "cancelled": False, "action_code": "DOWNLOAD_SNAPSHOT_JSON", "filename": "snapshot.json", "bytes_written": 11}
    assert window.dialog_calls == [("SAVE", "operator-cockpit-snapshot.json")]
    assert fetch_calls == [("http://127.0.0.1:8090", "/api/operator-cockpit-v2/export/snapshot.json", MAX_NATIVE_DESKTOP_EXPORT_BYTES, desktop.DEFAULT_NATIVE_EXPORT_TIMEOUT_SECONDS)]
    assert write_calls == [(destination, b'{"ok":true}')]
    assert destination.read_bytes() == b'{"ok":true}'


def test_26dh2_cancelled_save_dialog_does_not_fetch_or_write(tmp_path: Path) -> None:
    fetch_calls: list[str] = []
    write_calls: list[str] = []
    bridge = NativeDesktopExportBridge(
        "http://127.0.0.1:8090",
        fetcher=lambda *_args: fetch_calls.append("fetch") or b"payload",
        writer=lambda *_args: write_calls.append("write"),
    )
    bridge.bind_window(FakeWindow(save_result=None), SimpleNamespace(SAVE_DIALOG="SAVE"))
    assert bridge.export_file("DOWNLOAD_EVIDENCE_PACK_ZIP") == {"ok": True, "cancelled": True, "action_code": "DOWNLOAD_EVIDENCE_PACK_ZIP"}
    assert fetch_calls == []
    assert write_calls == []


def test_26dh2_text_actions_render_pretty_utf8_json_and_reject_download_mode() -> None:
    calls: list[str] = []

    def fetcher(_base: str, endpoint: str, _max: int, _timeout: float) -> bytes:
        calls.append(endpoint)
        return json.dumps({"başlık": "henüz oluşmadı"}, ensure_ascii=False).encode("utf-8")

    bridge = NativeDesktopExportBridge("http://127.0.0.1:8090", fetcher=fetcher)
    audit = bridge.read_text("OPEN_LATEST_AUDIT_JSON")
    assert audit["ok"] is True
    assert '"başlık": "henüz oluşmadı"' in str(audit["content"])
    assert calls == ["/api/operator-cockpit-v2/view/latest-audit.json"]
    blocked = bridge.read_text("DOWNLOAD_EVIDENCE_PACK_ZIP")
    assert blocked == {"ok": False, "action_code": "DOWNLOAD_EVIDENCE_PACK_ZIP", "error": "NATIVE_DESKTOP_ACTION_NOT_ALLOWED"}


def test_26dh2_arbitrary_action_code_is_fail_closed_before_fetch_or_dialog() -> None:
    calls: list[str] = []
    bridge = NativeDesktopExportBridge("http://127.0.0.1:8090", fetcher=lambda *_args: calls.append("fetch") or b"x")
    bridge.bind_window(FakeWindow(save_result="ignored"), SimpleNamespace(SAVE_DIALOG="SAVE"))
    result = bridge.export_file("../../etc/passwd")
    assert result == {"ok": False, "cancelled": False, "action_code": "../../etc/passwd", "error": "NATIVE_DESKTOP_ACTION_NOT_ALLOWED"}
    assert calls == []


def test_26dh2_save_dialog_result_normalization_is_safe() -> None:
    assert _normalize_save_dialog_result(None) is None
    assert _normalize_save_dialog_result(()) is None
    assert _normalize_save_dialog_result(("C:/tmp/output.zip",)) == Path("C:/tmp/output.zip")
    assert _normalize_save_dialog_result("C:/tmp/output.zip") == Path("C:/tmp/output.zip")
    with pytest.raises(DesktopWrapperError, match="NATIVE_DESKTOP_SAVE_DIALOG_RESULT_INVALID"):
        _normalize_save_dialog_result(123)


def test_26dh2_default_local_get_fetches_allowlisted_payload_and_enforces_size(tmp_path: Path) -> None:
    _seed_minimal_isolated_r1_ledger(tmp_path)
    running = start_local_cockpit_server(tmp_path, port=0)
    try:
        origin = _dashboard_origin(running.url)
        payload = _read_bounded_local_get(origin, "/api/operator-cockpit-v2/export/latest-ledger", 1024, 2.0)
        assert b"BTCUSDT" in payload
        with pytest.raises(DesktopWrapperError, match="NATIVE_DESKTOP_EXPORT_TOO_LARGE"):
            _read_bounded_local_get(origin, "/api/operator-cockpit-v2/export/evidence-pack.zip", 2, 2.0)
        with pytest.raises(DesktopWrapperError, match="NATIVE_DESKTOP_EXPORT_ENDPOINT_NOT_ALLOWED"):
            _read_bounded_local_get(origin, "https://example.com/file", 1024, 2.0)
    finally:
        running.stop()


def test_26dh2_loaded_event_injects_click_interceptor_for_native_download_and_json_modal() -> None:
    window = FakeWindow()
    assert _attach_native_desktop_export_bridge(window) is True
    assert window.evaluated_js == []
    window.events.loaded.fire()
    assert len(window.evaluated_js) == 1
    script = window.evaluated_js[0]
    assert "window.pywebview.api" in script
    assert "api.export_file(code)" in script
    assert "api.read_text(code)" in script
    assert "DOWNLOAD_EVIDENCE_PACK_ZIP" in script
    assert "native-desktop-json-overlay" in script
    assert "event.preventDefault()" in script
    assert script == NATIVE_DESKTOP_EXPORT_BRIDGE_JS


def test_26dh2_launch_shell_passes_js_api_bridge_and_loaded_event_injects_script(tmp_path: Path) -> None:
    calls: list[tuple[str, object]] = []
    window = FakeWindow()

    def create_window(title: str, url: str, **kwargs: object) -> FakeWindow:
        calls.append(("create_window", {"title": title, "url": url, **kwargs}))
        return window

    def start(*, debug: bool) -> None:
        calls.append(("start", {"debug": debug}))
        window.events.loaded.fire()

    fake_webview = SimpleNamespace(create_window=create_window, start=start, SAVE_DIALOG="SAVE")
    result = launch_desktop_shell(tmp_path, port=0, lock_path=tmp_path / "desktop.lock", webview_loader=lambda: fake_webview)
    assert result == 0
    create = calls[0][1]
    assert isinstance(create, dict)
    assert isinstance(create["js_api"], NativeDesktopExportBridge)
    assert calls[1] == ("start", {"debug": False})
    assert len(window.evaluated_js) == 1
    assert not (tmp_path / "desktop.lock").exists()
