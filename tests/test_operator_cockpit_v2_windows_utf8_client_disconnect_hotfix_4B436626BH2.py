from __future__ import annotations

import json
import urllib.request
from http import HTTPStatus
from pathlib import Path

import pytest

from tradebot.operator_cockpit_v2_read_only import (
    DASHBOARD_HTML,
    OPERATOR_COCKPIT_V2_CLIENT_DISCONNECT_NOISE_SUPPRESSION,
    OPERATOR_COCKPIT_V2_READ_ONLY,
    OPERATOR_COCKPIT_V2_WINDOWS_UTF8_CLIENT_DISCONNECT_HOTFIX_VERSION,
    OPERATOR_COCKPIT_V2_WINDOWS_UTF8_EMPTY_STATE_ASSERTION,
    OperatorCockpitRequestHandler,
    _is_client_disconnect_error,
    make_operator_cockpit_server,
)


class _RaisingWriter:
    def __init__(self, error: OSError) -> None:
        self.error = error

    def write(self, _: bytes) -> None:
        raise self.error


class _CollectingWriter:
    def __init__(self) -> None:
        self.body = b""

    def write(self, body: bytes) -> None:
        self.body += body


def _handler_with_writer(writer: object) -> OperatorCockpitRequestHandler:
    handler = object.__new__(OperatorCockpitRequestHandler)
    handler.wfile = writer
    handler.send_response = lambda *_args, **_kwargs: None
    handler.send_header = lambda *_args, **_kwargs: None
    handler.end_headers = lambda *_args, **_kwargs: None
    return handler


def test_26bh2_declares_windows_utf8_and_disconnect_noise_suppression_without_weakening_read_only() -> None:
    assert OPERATOR_COCKPIT_V2_WINDOWS_UTF8_CLIENT_DISCONNECT_HOTFIX_VERSION == "4B.4.3.6.6.26B-H2"
    assert OPERATOR_COCKPIT_V2_WINDOWS_UTF8_EMPTY_STATE_ASSERTION is True
    assert OPERATOR_COCKPIT_V2_CLIENT_DISCONNECT_NOISE_SUPPRESSION is True
    assert OPERATOR_COCKPIT_V2_READ_ONLY is True


def test_26bh2_dashboard_html_retains_utf8_empty_state_and_h2_badge() -> None:
    assert "MAE / MFE verisi henüz oluşmadı." in DASHBOARD_HTML
    assert "26B-H2 · READ ONLY" in DASHBOARD_HTML
    assert DASHBOARD_HTML.encode("utf-8").decode("utf-8") == DASHBOARD_HTML


def test_26bh2_expected_client_disconnect_errors_are_classified() -> None:
    assert _is_client_disconnect_error(ConnectionAbortedError(10053, "client aborted")) is True
    assert _is_client_disconnect_error(ConnectionResetError(10054, "client reset")) is True
    assert _is_client_disconnect_error(BrokenPipeError(32, "broken pipe")) is True


def test_26bh2_write_suppresses_expected_client_disconnect_noise() -> None:
    handler = _handler_with_writer(_RaisingWriter(ConnectionAbortedError(10053, "client aborted")))
    handler._write(HTTPStatus.OK, b"payload", "application/json; charset=utf-8")


def test_26bh2_write_does_not_hide_real_server_io_errors() -> None:
    handler = _handler_with_writer(_RaisingWriter(OSError(28, "disk full")))
    with pytest.raises(OSError, match="disk full"):
        handler._write(HTTPStatus.OK, b"payload", "application/json; charset=utf-8")


def test_26bh2_write_preserves_payload_when_connection_is_healthy() -> None:
    writer = _CollectingWriter()
    handler = _handler_with_writer(writer)
    handler._write(HTTPStatus.OK, "oluşmadı".encode("utf-8"), "text/plain; charset=utf-8")
    assert writer.body.decode("utf-8") == "oluşmadı"


def test_26bh2_http_dashboard_response_declares_utf8_and_mutation_remains_blocked(tmp_path: Path) -> None:
    server = make_operator_cockpit_server(tmp_path, port=0, task_query=lambda name: {"task_name": name, "state": "Disabled"}, backend_probe=lambda _: {"reachable": False, "status_code": None, "payload": {}})
    import threading
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    try:
        with urllib.request.urlopen(f"http://{host}:{port}/dashboard", timeout=3) as response:
            assert response.headers.get_content_charset() == "utf-8"
            html = response.read().decode("utf-8")
            assert "MAE / MFE verisi henüz oluşmadı." in html
        request = urllib.request.Request(f"http://{host}:{port}/api/operator-cockpit-v2/snapshot", data=b"{}", method="POST")
        with pytest.raises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(request, timeout=3)
        assert caught.value.code == 405
        blocked = json.loads(caught.value.read().decode("utf-8"))
        assert blocked["error"] == "READ_ONLY_DASHBOARD_MUTATION_BLOCKED"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
