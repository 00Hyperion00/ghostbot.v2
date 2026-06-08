from __future__ import annotations

import json
import threading
import time
import urllib.error
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from tradebot.operator_cockpit_v2_desktop_wrapper import (
    DEFAULT_NATIVE_EVIDENCE_PACK_TIMEOUT_SECONDS,
    DEFAULT_NATIVE_EXPORT_TIMEOUT_SECONDS,
    NATIVE_DESKTOP_ACTIONS,
    OPERATOR_COCKPIT_V2_EVIDENCE_PACK_TIMEOUT_HOTFIX_VERSION,
    OPERATOR_COCKPIT_V2_NATIVE_EXPORT_RESPONSE_PREFLIGHT,
    OPERATOR_COCKPIT_V2_NATIVE_EXPORT_TIMEOUT_CONTRACT,
    DesktopWrapperError,
    NativeDesktopExportBridge,
    _is_native_export_timeout,
    _native_export_response_preflight,
    _read_bounded_local_get,
)


class _StaticExportHandler(BaseHTTPRequestHandler):
    def log_message(self, *_args: Any) -> None:
        return

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/api/operator-cockpit-v2/static-too-large.zip":
            self.send_response(HTTPStatus.OK.value)
            self.send_header("Content-Type", "application/zip")
            self.send_header("Content-Length", "4096")
            self.end_headers()
            return
        if self.path == "/api/operator-cockpit-v2/static-invalid-length.zip":
            self.send_response(HTTPStatus.OK.value)
            self.send_header("Content-Type", "application/zip")
            self.send_header("Content-Length", "not-a-number")
            self.end_headers()
            return
        if self.path == "/api/operator-cockpit-v2/static-ok.zip":
            payload = b"PK\x03\x04fixture"
            self.send_response(HTTPStatus.OK.value)
            self.send_header("Content-Type", "application/zip")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        if self.path == "/api/operator-cockpit-v2/slow-header.zip":
            time.sleep(0.25)
            payload = b"PK\x03\x04slow"
            self.send_response(HTTPStatus.OK.value)
            self.send_header("Content-Type", "application/zip")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            try:
                self.wfile.write(payload)
            except OSError:
                pass
            return
        self.send_response(HTTPStatus.NOT_FOUND.value)
        self.send_header("Content-Length", "0")
        self.end_headers()


class _StaticServer:
    def __enter__(self) -> str:
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), _StaticExportHandler)
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address
        return f"http://{host}:{port}"

    def __exit__(self, *_args: object) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)


class _SaveWindow:
    def __init__(self, result: str) -> None:
        self.result = result

    def create_file_dialog(self, _dialog_type: object, *, save_filename: str) -> str:
        return self.result


def test_26dh2h2_declares_response_preflight_and_timeout_contract() -> None:
    assert OPERATOR_COCKPIT_V2_EVIDENCE_PACK_TIMEOUT_HOTFIX_VERSION == "4B.4.3.6.6.26D-H2-H2"
    assert OPERATOR_COCKPIT_V2_NATIVE_EXPORT_RESPONSE_PREFLIGHT is True
    assert OPERATOR_COCKPIT_V2_NATIVE_EXPORT_TIMEOUT_CONTRACT is True
    assert DEFAULT_NATIVE_EVIDENCE_PACK_TIMEOUT_SECONDS > DEFAULT_NATIVE_EXPORT_TIMEOUT_SECONDS


def test_26dh2h2_preflight_rejects_invalid_and_oversized_declared_length() -> None:
    assert _native_export_response_preflight({}, 16) is None
    assert _native_export_response_preflight({"Content-Length": " 8 "}, 16) == 8
    with pytest.raises(DesktopWrapperError, match="NATIVE_DESKTOP_EXPORT_TOO_LARGE"):
        _native_export_response_preflight({"Content-Length": "17"}, 16)
    with pytest.raises(DesktopWrapperError, match="NATIVE_DESKTOP_EXPORT_CONTENT_LENGTH_INVALID"):
        _native_export_response_preflight({"Content-Length": "broken"}, 16)
    with pytest.raises(DesktopWrapperError, match="NATIVE_DESKTOP_EXPORT_CONTENT_LENGTH_INVALID"):
        _native_export_response_preflight({"Content-Length": "-1"}, 16)
    with pytest.raises(DesktopWrapperError, match="NATIVE_DESKTOP_EXPORT_MAX_BYTES_INVALID"):
        _native_export_response_preflight({"Content-Length": "1"}, 0)


def test_26dh2h2_static_response_preflight_rejects_too_large_before_body_read() -> None:
    with _StaticServer() as origin:
        with pytest.raises(DesktopWrapperError, match="NATIVE_DESKTOP_EXPORT_TOO_LARGE"):
            _read_bounded_local_get(origin, "/api/operator-cockpit-v2/static-too-large.zip", 2, 1.0)


def test_26dh2h2_static_invalid_length_contract_is_deterministic() -> None:
    with _StaticServer() as origin:
        with pytest.raises(DesktopWrapperError, match="NATIVE_DESKTOP_EXPORT_CONTENT_LENGTH_INVALID"):
            _read_bounded_local_get(origin, "/api/operator-cockpit-v2/static-invalid-length.zip", 1024, 1.0)


def test_26dh2h2_slow_header_is_mapped_to_deterministic_timeout_contract() -> None:
    with _StaticServer() as origin:
        with pytest.raises(DesktopWrapperError, match="NATIVE_DESKTOP_EXPORT_TIMEOUT"):
            _read_bounded_local_get(origin, "/api/operator-cockpit-v2/slow-header.zip", 1024, 0.03)


def test_26dh2h2_small_static_zip_payload_remains_readable() -> None:
    with _StaticServer() as origin:
        payload = _read_bounded_local_get(origin, "/api/operator-cockpit-v2/static-ok.zip", 1024, 1.0)
    assert payload == b"PK\x03\x04fixture"


def test_26dh2h2_urllib_wrapped_timeout_is_classified() -> None:
    assert _is_native_export_timeout(TimeoutError("timed out")) is True
    assert _is_native_export_timeout(urllib.error.URLError(TimeoutError("timed out"))) is True
    assert _is_native_export_timeout(urllib.error.URLError("connection refused")) is False


def test_26dh2h2_evidence_pack_bridge_uses_extended_timeout_budget(tmp_path: Path) -> None:
    destination = tmp_path / "evidence.zip"
    calls: list[tuple[str, str, int, float]] = []

    def fetcher(base_url: str, endpoint: str, max_bytes: int, timeout_seconds: float) -> bytes:
        calls.append((base_url, endpoint, max_bytes, timeout_seconds))
        return b"PK\x03\x04fixture"

    bridge = NativeDesktopExportBridge("http://127.0.0.1:8090", fetcher=fetcher, writer=lambda path, payload: path.write_bytes(payload))
    bridge.bind_window(_SaveWindow(str(destination)), SimpleNamespace(SAVE_DIALOG="SAVE"))
    result = bridge.export_file("DOWNLOAD_EVIDENCE_PACK_ZIP")
    assert result["ok"] is True
    assert calls == [(
        "http://127.0.0.1:8090",
        "/api/operator-cockpit-v2/export/evidence-pack.zip",
        NATIVE_DESKTOP_ACTIONS["DOWNLOAD_EVIDENCE_PACK_ZIP"].max_bytes,
        DEFAULT_NATIVE_EVIDENCE_PACK_TIMEOUT_SECONDS,
    )]
    assert destination.read_bytes() == b"PK\x03\x04fixture"
