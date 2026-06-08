from __future__ import annotations

import io
import json
import threading
import urllib.error
import urllib.request
from email.message import Message
from pathlib import Path

from tradebot.operator_cockpit_v2_read_only import (
    MAX_MUTATION_REQUEST_BODY_DRAIN_BYTES,
    OPERATOR_COCKPIT_V2_HTTP_405_CONTRACT_PRESERVATION,
    OPERATOR_COCKPIT_V2_MUTATION_REQUEST_BODY_DRAIN,
    OPERATOR_COCKPIT_V2_READ_ONLY,
    OPERATOR_COCKPIT_V2_WINDOWS_MUTATION_BODY_DRAIN_HOTFIX_VERSION,
    OperatorCockpitRequestHandler,
    _parse_content_length,
    make_operator_cockpit_server,
)


class _TrackingReader(io.BytesIO):
    def __init__(self, initial_bytes: bytes) -> None:
        super().__init__(initial_bytes)
        self.total_requested = 0

    def read(self, size: int = -1) -> bytes:
        self.total_requested += size if size >= 0 else len(self.getbuffer())
        return super().read(size)


def _handler_with_body(body: bytes, *, content_length: str | None = None, transfer_encoding: str | None = None) -> tuple[OperatorCockpitRequestHandler, _TrackingReader]:
    handler = object.__new__(OperatorCockpitRequestHandler)
    headers = Message()
    if content_length is not None:
        headers["Content-Length"] = content_length
    if transfer_encoding is not None:
        headers["Transfer-Encoding"] = transfer_encoding
    reader = _TrackingReader(body)
    handler.headers = headers
    handler.rfile = reader
    handler.close_connection = False
    return handler, reader


def test_26bh3_declares_body_drain_and_http405_preservation_without_weakening_read_only() -> None:
    assert OPERATOR_COCKPIT_V2_WINDOWS_MUTATION_BODY_DRAIN_HOTFIX_VERSION == "4B.4.3.6.6.26B-H3"
    assert OPERATOR_COCKPIT_V2_MUTATION_REQUEST_BODY_DRAIN is True
    assert OPERATOR_COCKPIT_V2_HTTP_405_CONTRACT_PRESERVATION is True
    assert OPERATOR_COCKPIT_V2_READ_ONLY is True
    assert MAX_MUTATION_REQUEST_BODY_DRAIN_BYTES == 64 * 1024


def test_26bh3_content_length_parser_rejects_invalid_or_negative_values() -> None:
    assert _parse_content_length(None) == 0
    assert _parse_content_length("") == 0
    assert _parse_content_length(" 2 ") == 2
    assert _parse_content_length("-1") is None
    assert _parse_content_length("not-a-number") is None


def test_26bh3_small_mutation_payload_is_fully_drained_before_405() -> None:
    handler, reader = _handler_with_body(b"{}", content_length="2")
    drained = handler._drain_mutation_request_body()
    assert drained == 2
    assert reader.read() == b""
    assert handler.close_connection is False


def test_26bh3_oversized_mutation_payload_is_bounded_and_connection_is_closed() -> None:
    body = b"x" * (MAX_MUTATION_REQUEST_BODY_DRAIN_BYTES + 32)
    handler, reader = _handler_with_body(body, content_length=str(len(body)))
    drained = handler._drain_mutation_request_body()
    assert drained == MAX_MUTATION_REQUEST_BODY_DRAIN_BYTES
    assert reader.tell() == MAX_MUTATION_REQUEST_BODY_DRAIN_BYTES
    assert handler.close_connection is True


def test_26bh3_invalid_length_or_chunked_payload_forces_connection_close_without_processing_payload() -> None:
    invalid_handler, invalid_reader = _handler_with_body(b"{}", content_length="broken")
    assert invalid_handler._drain_mutation_request_body() == 0
    assert invalid_reader.tell() == 0
    assert invalid_handler.close_connection is True

    chunked_handler, chunked_reader = _handler_with_body(b"2\r\n{}\r\n0\r\n\r\n", transfer_encoding="chunked")
    assert chunked_handler._drain_mutation_request_body() == 0
    assert chunked_reader.tell() == 0
    assert chunked_handler.close_connection is True


def test_26bh3_all_mutation_methods_return_stable_405_json_with_request_body(tmp_path: Path) -> None:
    server = make_operator_cockpit_server(
        tmp_path,
        port=0,
        task_query=lambda name: {"task_name": name, "state": "Disabled"},
        backend_probe=lambda _: {"reachable": False, "status_code": None, "payload": {}},
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    try:
        for method in ("POST", "PUT", "PATCH", "DELETE"):
            request = urllib.request.Request(
                f"http://{host}:{port}/api/operator-cockpit-v2/snapshot",
                data=b"{}",
                method=method,
                headers={"Content-Type": "application/json"},
            )
            try:
                urllib.request.urlopen(request, timeout=3)
            except urllib.error.HTTPError as error:
                assert error.code == 405
                payload = json.loads(error.read().decode("utf-8"))
                assert payload == {
                    "ok": False,
                    "error": "READ_ONLY_DASHBOARD_MUTATION_BLOCKED",
                    "read_only": True,
                }
            else:
                raise AssertionError(f"{method} unexpectedly succeeded")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_26bh3_read_only_snapshot_remains_available_after_blocked_mutation(tmp_path: Path) -> None:
    server = make_operator_cockpit_server(
        tmp_path,
        port=0,
        task_query=lambda name: {"task_name": name, "state": "Disabled"},
        backend_probe=lambda _: {"reachable": False, "status_code": None, "payload": {}},
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    try:
        request = urllib.request.Request(f"http://{host}:{port}/api/operator-cockpit-v2/snapshot", data=b"{}", method="POST")
        try:
            urllib.request.urlopen(request, timeout=3)
        except urllib.error.HTTPError as error:
            assert error.code == 405
        else:
            raise AssertionError("POST unexpectedly succeeded")
        with urllib.request.urlopen(f"http://{host}:{port}/api/operator-cockpit-v2/health", timeout=3) as response:
            payload = json.loads(response.read().decode("utf-8"))
            assert payload["ok"] is True
            assert payload["read_only"] is True
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
