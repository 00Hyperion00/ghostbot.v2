from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import tradebot.operator_cockpit_v2_desktop_wrapper as desktop
from tradebot.operator_cockpit_v2_desktop_wrapper import (
    DEFAULT_DESKTOP_HOST,
    OPERATOR_COCKPIT_V2_BROWSER_FALLBACK_REQUIRES_EXPLICIT_FLAG,
    OPERATOR_COCKPIT_V2_DESKTOP_LOCAL_ONLY,
    OPERATOR_COCKPIT_V2_DESKTOP_WRAPPER_VERSION,
    OPERATOR_COCKPIT_V2_NO_CONFIG_MUTATION,
    OPERATOR_COCKPIT_V2_NO_SCHEDULER_MUTATION,
    OPERATOR_COCKPIT_V2_NO_TRADING_ACTION,
    OPERATOR_COCKPIT_V2_SINGLE_INSTANCE,
    DesktopInstanceLock,
    DesktopWrapperError,
    _assert_loopback_host,
    _assert_port_available,
    launch_desktop_shell,
    run_headless_smoke,
)


def test_26d_declares_local_single_instance_desktop_wrapper_without_trading_mutation() -> None:
    assert OPERATOR_COCKPIT_V2_DESKTOP_WRAPPER_VERSION == "4B.4.3.6.6.26D"
    assert OPERATOR_COCKPIT_V2_DESKTOP_LOCAL_ONLY is True
    assert OPERATOR_COCKPIT_V2_SINGLE_INSTANCE is True
    assert OPERATOR_COCKPIT_V2_BROWSER_FALLBACK_REQUIRES_EXPLICIT_FLAG is True
    assert OPERATOR_COCKPIT_V2_NO_CONFIG_MUTATION is True
    assert OPERATOR_COCKPIT_V2_NO_SCHEDULER_MUTATION is True
    assert OPERATOR_COCKPIT_V2_NO_TRADING_ACTION is True


def test_26d_loopback_policy_blocks_nonlocal_bind() -> None:
    _assert_loopback_host("127.0.0.1")
    _assert_loopback_host("localhost")
    _assert_loopback_host("::1")
    with pytest.raises(DesktopWrapperError, match="NON_LOOPBACK_DESKTOP_BIND_BLOCKED"):
        _assert_loopback_host("0.0.0.0")


def test_26d_instance_lock_blocks_second_process_and_recovers_stale_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    lock_path = tmp_path / "cockpit.lock"
    first = DesktopInstanceLock(lock_path)
    first.acquire()
    try:
        with pytest.raises(DesktopWrapperError, match="OPERATOR_COCKPIT_DESKTOP_INSTANCE_ALREADY_RUNNING"):
            DesktopInstanceLock(lock_path).acquire()
    finally:
        first.release()
    lock_path.write_text(json.dumps({"pid": 991122, "host": "127.0.0.1", "port": 8090, "created_at_epoch": 0.0}), encoding="utf-8")
    monkeypatch.setattr(desktop, "_pid_is_running", lambda _pid: False)
    recovered = DesktopInstanceLock(lock_path)
    recovered.acquire()
    try:
        assert json.loads(lock_path.read_text(encoding="utf-8"))["pid"] == os.getpid()
    finally:
        recovered.release()
    assert not lock_path.exists()


def test_26d_port_preflight_rejects_occupied_loopback_port() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as occupied:
        occupied.bind((DEFAULT_DESKTOP_HOST, 0))
        occupied.listen(1)
        _, port = occupied.getsockname()
        with pytest.raises(DesktopWrapperError, match="LOCAL_COCKPIT_PORT_ALREADY_IN_USE"):
            _assert_port_available(DEFAULT_DESKTOP_HOST, port)


def test_26d_headless_smoke_starts_probes_and_stops_local_server(tmp_path: Path) -> None:
    result = run_headless_smoke(tmp_path, port=0, lock_path=tmp_path / "smoke.lock")
    assert result["ok"] is True
    assert result["desktop_wrapper_version"] == "4B.4.3.6.6.26D"
    assert result["desktop_local_only"] is True
    assert result["single_instance"] is True
    assert result["url"].startswith("http://127.0.0.1:")
    assert result["health"]["payload"]["ok"] is True
    assert result["config_mutation_performed"] is False
    assert result["scheduler_mutation_performed"] is False
    assert result["trading_action_performed"] is False


def test_26d_embedded_webview_lifecycle_owns_local_server_and_uses_dashboard_url(tmp_path: Path) -> None:
    calls: list[tuple[str, object]] = []

    def create_window(title: str, url: str, **kwargs: object) -> None:
        calls.append(("create_window", {"title": title, "url": url, **kwargs}))

    def start(*, debug: bool) -> None:
        calls.append(("start", {"debug": debug}))

    fake_webview = SimpleNamespace(create_window=create_window, start=start)
    result = launch_desktop_shell(
        tmp_path,
        port=0,
        lock_path=tmp_path / "desktop.lock",
        webview_loader=lambda: fake_webview,
    )
    assert result == 0
    assert calls[0][0] == "create_window"
    window = calls[0][1]
    assert isinstance(window, dict)
    assert str(window["url"]).startswith("http://127.0.0.1:")
    assert str(window["url"]).endswith("/dashboard")
    assert calls[1] == ("start", {"debug": False})
    assert not (tmp_path / "desktop.lock").exists()


def test_26d_missing_pywebview_fails_closed_without_implicit_browser_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    browser_calls: list[str] = []
    monkeypatch.setattr(desktop.webbrowser, "open", lambda url: browser_calls.append(url))

    def missing() -> object:
        raise DesktopWrapperError("PYWEBVIEW_DEPENDENCY_MISSING")

    with pytest.raises(DesktopWrapperError, match="PYWEBVIEW_DEPENDENCY_MISSING"):
        launch_desktop_shell(
            tmp_path,
            port=0,
            lock_path=tmp_path / "desktop.lock",
            webview_loader=missing,
        )
    assert browser_calls == []
    assert not (tmp_path / "desktop.lock").exists()


def test_26d_runner_headless_smoke_stdout_is_parseable_utf8_json(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    runner = project_root / "tools" / "run_operator_cockpit_v2_desktop_4B436626D.py"
    completed = subprocess.run(
        [sys.executable, str(runner), "--project-root", str(tmp_path / "Masaüstü"), "--host", "127.0.0.1", "--port", "0", "--headless-smoke-json"],
        cwd=project_root,
        capture_output=True,
        check=False,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stderr.decode("utf-8", errors="replace")
    payload = json.loads(completed.stdout.decode("utf-8"))
    assert payload["ok"] is True
    assert payload["desktop_wrapper_version"] == "4B.4.3.6.6.26D"
    assert payload["desktop_local_only"] is True
    assert completed.stderr == b""


def test_26d_shortcut_creation_is_explicit_and_not_run_by_patch_application() -> None:
    project_root = Path(__file__).resolve().parents[1]
    apply_text = (project_root / "tools" / "apply_4B436626D_operator_cockpit_v2_desktop_wrapper.py").read_text(encoding="utf-8")
    shortcut_text = (project_root / "tools" / "create_operator_cockpit_v2_desktop_shortcut_4B436626D.ps1").read_text(encoding="utf-8")
    assert "CreateShortcut" in shortcut_text
    assert "create_operator_cockpit_v2_desktop_shortcut_4B436626D.ps1" not in apply_text
