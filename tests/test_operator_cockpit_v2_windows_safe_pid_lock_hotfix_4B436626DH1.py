from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import pytest

import tradebot.operator_cockpit_v2_desktop_wrapper as desktop
from tradebot.operator_cockpit_v2_desktop_wrapper import (
    OPERATOR_COCKPIT_V2_DETERMINISTIC_SINGLE_INSTANCE_LOCK,
    OPERATOR_COCKPIT_V2_WINDOWS_OS_KILL_ZERO_DISABLED,
    OPERATOR_COCKPIT_V2_WINDOWS_SAFE_PID_LIVENESS_PROBE,
    OPERATOR_COCKPIT_V2_WINDOWS_SAFE_PID_LOCK_HOTFIX_VERSION,
    WINDOWS_ERROR_ACCESS_DENIED,
    WINDOWS_ERROR_INVALID_PARAMETER,
    WINDOWS_STILL_ACTIVE,
    WINDOWS_WAIT_OBJECT_0,
    WINDOWS_WAIT_TIMEOUT,
    DesktopInstanceLock,
    DesktopWrapperError,
    _pid_is_running,
    _windows_pid_is_running,
)


class FakeKernel32:
    def __init__(self, *, handle: int = 42, wait_result: int = WINDOWS_WAIT_TIMEOUT, exit_code: int = WINDOWS_STILL_ACTIVE) -> None:
        self.handle = handle
        self.wait_result = wait_result
        self.exit_code = exit_code
        self.open_calls: list[tuple[int, bool, int]] = []
        self.wait_calls: list[tuple[int, int]] = []
        self.close_calls: list[int] = []
        self.exit_code_calls: list[int] = []

    def OpenProcess(self, access: int, inherit_handle: bool, pid: int) -> int:  # noqa: N802
        self.open_calls.append((access, inherit_handle, pid))
        return self.handle

    def WaitForSingleObject(self, handle: int, timeout_ms: int) -> int:  # noqa: N802
        self.wait_calls.append((handle, timeout_ms))
        return self.wait_result

    def GetExitCodeProcess(self, handle: int, exit_code_pointer: Any) -> int:  # noqa: N802
        self.exit_code_calls.append(handle)
        exit_code_pointer._obj.value = self.exit_code
        return 1

    def CloseHandle(self, handle: int) -> int:  # noqa: N802
        self.close_calls.append(handle)
        return 1


def test_26dh1_declares_windows_safe_pid_probe_and_deterministic_lock() -> None:
    assert OPERATOR_COCKPIT_V2_WINDOWS_SAFE_PID_LOCK_HOTFIX_VERSION == "4B.4.3.6.6.26D-H1"
    assert OPERATOR_COCKPIT_V2_WINDOWS_SAFE_PID_LIVENESS_PROBE is True
    assert OPERATOR_COCKPIT_V2_DETERMINISTIC_SINGLE_INSTANCE_LOCK is True
    assert OPERATOR_COCKPIT_V2_WINDOWS_OS_KILL_ZERO_DISABLED is True


def test_26dh1_current_pid_fast_path_never_calls_os_kill_or_winapi(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(desktop.os, "kill", lambda *_args: (_ for _ in ()).throw(AssertionError("os.kill must not run")))
    monkeypatch.setattr(desktop, "_windows_pid_is_running", lambda _pid: (_ for _ in ()).throw(AssertionError("WinAPI must not run")))
    assert _pid_is_running(os.getpid()) is True


def test_26dh1_windows_branch_uses_winapi_and_never_calls_os_kill(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []
    monkeypatch.setattr(desktop, "_is_windows_platform", lambda: True)
    monkeypatch.setattr(desktop.os, "kill", lambda *_args: (_ for _ in ()).throw(AssertionError("os.kill must not run on Windows")))
    monkeypatch.setattr(desktop, "_windows_pid_is_running", lambda pid: calls.append(pid) or True)
    assert _pid_is_running(991122) is True
    assert calls == [991122]


def test_26dh1_windows_active_and_exited_handles_are_closed() -> None:
    active = FakeKernel32(wait_result=WINDOWS_WAIT_TIMEOUT)
    assert _windows_pid_is_running(991122, kernel32=active, last_error_getter=lambda: 0) is True
    assert active.wait_calls == [(42, 0)]
    assert active.close_calls == [42]

    exited = FakeKernel32(wait_result=WINDOWS_WAIT_OBJECT_0)
    assert _windows_pid_is_running(991123, kernel32=exited, last_error_getter=lambda: 0) is False
    assert exited.wait_calls == [(42, 0)]
    assert exited.close_calls == [42]


def test_26dh1_windows_openprocess_denied_is_active_and_invalid_pid_is_stale() -> None:
    no_handle = FakeKernel32(handle=0)
    assert _windows_pid_is_running(991122, kernel32=no_handle, last_error_getter=lambda: WINDOWS_ERROR_ACCESS_DENIED) is True
    assert _windows_pid_is_running(991123, kernel32=no_handle, last_error_getter=lambda: WINDOWS_ERROR_INVALID_PARAMETER) is False
    assert no_handle.close_calls == []


def test_26dh1_windows_unknown_wait_uses_exit_code_and_closes_handle() -> None:
    kernel = FakeKernel32(wait_result=0xFFFFFFFF, exit_code=WINDOWS_STILL_ACTIVE)
    assert _windows_pid_is_running(991122, kernel32=kernel, last_error_getter=lambda: 0) is True
    assert kernel.exit_code_calls == [42]
    assert kernel.close_calls == [42]


def test_26dh1_posix_branch_retains_signal_zero_probe(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[int, int]] = []
    monkeypatch.setattr(desktop, "_is_windows_platform", lambda: False)
    monkeypatch.setattr(desktop.os, "kill", lambda pid, signal: calls.append((pid, signal)))
    assert _pid_is_running(991122) is True
    assert calls == [(991122, 0)]


def test_26dh1_single_instance_lock_blocks_immediately_and_recovers_stale_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    lock_path = tmp_path / "cockpit.lock"
    first = DesktopInstanceLock(lock_path)
    first.acquire()
    started = time.monotonic()
    try:
        with pytest.raises(DesktopWrapperError, match="OPERATOR_COCKPIT_DESKTOP_INSTANCE_ALREADY_RUNNING"):
            DesktopInstanceLock(lock_path).acquire()
    finally:
        first.release()
    assert time.monotonic() - started < 1.0

    lock_path.write_text(json.dumps({"pid": 991122, "host": "127.0.0.1", "port": 8090, "created_at_epoch": 0.0}), encoding="utf-8")
    monkeypatch.setattr(desktop, "_pid_is_running", lambda _pid: False)
    recovered = DesktopInstanceLock(lock_path)
    metadata = recovered.acquire()
    try:
        payload = json.loads(lock_path.read_text(encoding="utf-8"))
        assert payload["pid"] == os.getpid()
        assert payload["lock_id"] == metadata.lock_id
        assert metadata.lock_id
    finally:
        recovered.release()
    assert not lock_path.exists()


def test_26dh1_release_does_not_delete_lock_owned_by_another_instance(tmp_path: Path) -> None:
    lock_path = tmp_path / "cockpit.lock"
    lock = DesktopInstanceLock(lock_path)
    lock.acquire()
    lock_path.write_text(json.dumps({"pid": 991122, "host": "127.0.0.1", "port": 8090, "created_at_epoch": 0.0, "lock_id": "other-instance"}), encoding="utf-8")
    lock.release()
    assert lock_path.exists()
    assert json.loads(lock_path.read_text(encoding="utf-8"))["lock_id"] == "other-instance"
