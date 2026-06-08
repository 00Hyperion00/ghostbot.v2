from __future__ import annotations

import importlib
import json
import os
import socket
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import webbrowser
from dataclasses import asdict, dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Protocol

from tradebot.operator_cockpit_v2_read_only import make_operator_cockpit_server

OPERATOR_COCKPIT_V2_DESKTOP_WRAPPER_VERSION = "4B.4.3.6.6.26D"
OPERATOR_COCKPIT_V2_DESKTOP_LOCAL_ONLY = True
OPERATOR_COCKPIT_V2_SINGLE_INSTANCE = True
OPERATOR_COCKPIT_V2_NO_CONFIG_MUTATION = True
OPERATOR_COCKPIT_V2_NO_SCHEDULER_MUTATION = True
OPERATOR_COCKPIT_V2_NO_TRADING_ACTION = True
OPERATOR_COCKPIT_V2_BROWSER_FALLBACK_REQUIRES_EXPLICIT_FLAG = True
OPERATOR_COCKPIT_V2_WINDOWS_SAFE_PID_LOCK_HOTFIX_VERSION = "4B.4.3.6.6.26D-H1"
OPERATOR_COCKPIT_V2_WINDOWS_SAFE_PID_LIVENESS_PROBE = True
OPERATOR_COCKPIT_V2_DETERMINISTIC_SINGLE_INSTANCE_LOCK = True
OPERATOR_COCKPIT_V2_WINDOWS_OS_KILL_ZERO_DISABLED = True
OPERATOR_COCKPIT_V2_NATIVE_EXPORT_BRIDGE_HOTFIX_VERSION = "4B.4.3.6.6.26D-H2"
OPERATOR_COCKPIT_V2_NATIVE_DESKTOP_EXPORT_BRIDGE = True
OPERATOR_COCKPIT_V2_NATIVE_SAVE_DIALOG_DOWNLOADS = True
OPERATOR_COCKPIT_V2_NATIVE_EXPORT_ALLOWLIST_ONLY = True
OPERATOR_COCKPIT_V2_NATIVE_EXPORT_LOOPBACK_ONLY = True
WINDOWS_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
WINDOWS_SYNCHRONIZE = 0x00100000
WINDOWS_WAIT_OBJECT_0 = 0x00000000
WINDOWS_WAIT_TIMEOUT = 0x00000102
WINDOWS_STILL_ACTIVE = 259
WINDOWS_ERROR_ACCESS_DENIED = 5
WINDOWS_ERROR_INVALID_PARAMETER = 87
DEFAULT_DESKTOP_HOST = "127.0.0.1"
DEFAULT_DESKTOP_PORT = 8090
DEFAULT_HEALTH_PATH = "/api/operator-cockpit-v2/health"
DEFAULT_DASHBOARD_PATH = "/dashboard"
DEFAULT_WINDOW_TITLE = "TradeBot V2 · Operator Cockpit"
DEFAULT_WINDOW_WIDTH = 1480
DEFAULT_WINDOW_HEIGHT = 960
DEFAULT_WINDOW_MIN_WIDTH = 1180
DEFAULT_WINDOW_MIN_HEIGHT = 760
DEFAULT_HEALTH_TIMEOUT_SECONDS = 6.0
DEFAULT_NATIVE_EXPORT_TIMEOUT_SECONDS = 8.0
MAX_NATIVE_DESKTOP_EXPORT_BYTES = 16 * 1024 * 1024
MAX_NATIVE_DESKTOP_TEXT_VIEW_BYTES = 5 * 1024 * 1024


class DesktopWrapperError(RuntimeError):
    """Raised when the desktop shell cannot be launched safely."""


class CockpitServer(Protocol):
    server_address: tuple[str, int]

    def serve_forever(self, poll_interval: float = 0.5) -> None: ...

    def shutdown(self) -> None: ...

    def server_close(self) -> None: ...


@dataclass(frozen=True)
class DesktopLockMetadata:
    pid: int
    host: str
    port: int
    created_at_epoch: float
    lock_id: str = ""
    version: str = OPERATOR_COCKPIT_V2_DESKTOP_WRAPPER_VERSION


@dataclass
class RunningCockpitServer:
    server: CockpitServer
    thread: threading.Thread
    url: str
    health_url: str

    def stop(self) -> None:
        """Stop the local cockpit server and wait briefly for the daemon thread."""
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3.0)


WebViewLoader = Callable[[], ModuleType]
HealthProbe = Callable[[str, float], dict[str, Any]]
NativeFetch = Callable[[str, str, int, float], bytes]
NativeWrite = Callable[[Path, bytes], None]


@dataclass(frozen=True)
class NativeDesktopActionSpec:
    action_code: str
    endpoint: str
    filename: str
    mode: str
    max_bytes: int


NATIVE_DESKTOP_ACTIONS: dict[str, NativeDesktopActionSpec] = {
    "DOWNLOAD_SNAPSHOT_JSON": NativeDesktopActionSpec("DOWNLOAD_SNAPSHOT_JSON", "/api/operator-cockpit-v2/export/snapshot.json", "operator-cockpit-snapshot.json", "download", MAX_NATIVE_DESKTOP_EXPORT_BYTES),
    "OPEN_LATEST_AUDIT_JSON": NativeDesktopActionSpec("OPEN_LATEST_AUDIT_JSON", "/api/operator-cockpit-v2/view/latest-audit.json", "latest-25y-audit.json", "text", MAX_NATIVE_DESKTOP_TEXT_VIEW_BYTES),
    "OPEN_ACTION_MANIFEST": NativeDesktopActionSpec("OPEN_ACTION_MANIFEST", "/api/operator-cockpit-v2/actions/manifest", "safe-actions-manifest.json", "text", MAX_NATIVE_DESKTOP_TEXT_VIEW_BYTES),
    "DOWNLOAD_EVIDENCE_PACK_ZIP": NativeDesktopActionSpec("DOWNLOAD_EVIDENCE_PACK_ZIP", "/api/operator-cockpit-v2/export/evidence-pack.zip", "operator-cockpit-evidence-pack.zip", "download", MAX_NATIVE_DESKTOP_EXPORT_BYTES),
    "DOWNLOAD_MERGED_LEDGER_JSONL": NativeDesktopActionSpec("DOWNLOAD_MERGED_LEDGER_JSONL", "/api/operator-cockpit-v2/export/latest-ledger", "latest-merged-ledger.jsonl", "download", MAX_NATIVE_DESKTOP_EXPORT_BYTES),
}


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Block redirects so native exports can never leave the local cockpit origin."""

    def redirect_request(self, *_args: Any, **_kwargs: Any) -> None:
        raise DesktopWrapperError("NATIVE_DESKTOP_EXPORT_REDIRECT_BLOCKED")


def _default_lock_path() -> Path:
    return Path(tempfile.gettempdir()) / "tradebot_v2_operator_cockpit_desktop.lock"


def _is_loopback_host(host: str) -> bool:
    return host.strip().lower() in {"127.0.0.1", "localhost", "::1"}


def _assert_loopback_host(host: str) -> None:
    if not _is_loopback_host(host):
        raise DesktopWrapperError("NON_LOOPBACK_DESKTOP_BIND_BLOCKED")


def _is_windows_platform() -> bool:
    return os.name == "nt"


def _load_windows_kernel32() -> Any:
    """Load configured WinAPI functions lazily so non-Windows imports remain safe."""
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel32.WaitForSingleObject.restype = wintypes.DWORD
    kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel32.GetExitCodeProcess.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    return kernel32


def _windows_pid_is_running(
    pid: int,
    *,
    kernel32: Any | None = None,
    last_error_getter: Callable[[], int] | None = None,
) -> bool:
    """Probe process liveness with WinAPI handles; never send a signal on Windows."""
    if pid <= 0:
        return False
    if pid == os.getpid():
        return True

    import ctypes
    from ctypes import wintypes

    api = kernel32 or _load_windows_kernel32()
    get_last_error = last_error_getter or ctypes.get_last_error
    desired_access = WINDOWS_PROCESS_QUERY_LIMITED_INFORMATION | WINDOWS_SYNCHRONIZE
    handle = api.OpenProcess(desired_access, False, pid)
    if not handle:
        error_code = int(get_last_error())
        if error_code == WINDOWS_ERROR_INVALID_PARAMETER:
            return False
        if error_code == WINDOWS_ERROR_ACCESS_DENIED:
            return True
        return True  # Unknown probe failure: fail closed and keep the existing lock.

    try:
        wait_result = int(api.WaitForSingleObject(handle, 0))
        if wait_result == WINDOWS_WAIT_TIMEOUT:
            return True
        if wait_result == WINDOWS_WAIT_OBJECT_0:
            return False

        exit_code = wintypes.DWORD(0)
        if api.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
            return int(exit_code.value) == WINDOWS_STILL_ACTIVE
        return True  # Unknown WinAPI state: fail closed and keep the existing lock.
    finally:
        api.CloseHandle(handle)


def _posix_pid_is_running(pid: int) -> bool:
    """Probe process liveness without terminating it on POSIX systems."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _pid_is_running(pid: int) -> bool:
    if pid <= 0:
        return False
    if pid == os.getpid():
        return True
    if _is_windows_platform():
        return _windows_pid_is_running(pid)
    return _posix_pid_is_running(pid)


class DesktopInstanceLock:
    """Cross-platform stale-aware process lock stored outside the project directory."""

    def __init__(self, path: Path | None = None, *, host: str = DEFAULT_DESKTOP_HOST, port: int = DEFAULT_DESKTOP_PORT) -> None:
        self.path = (path or _default_lock_path()).resolve()
        self.host = host
        self.port = port
        self._acquired = False
        self._metadata: DesktopLockMetadata | None = None

    def _read_metadata(self) -> DesktopLockMetadata | None:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            return DesktopLockMetadata(
                pid=int(payload["pid"]),
                host=str(payload.get("host") or ""),
                port=int(payload.get("port") or 0),
                created_at_epoch=float(payload.get("created_at_epoch") or 0.0),
                lock_id=str(payload.get("lock_id") or ""),
                version=str(payload.get("version") or OPERATOR_COCKPIT_V2_DESKTOP_WRAPPER_VERSION),
            )
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
            return None

    def acquire(self) -> DesktopLockMetadata:
        _assert_loopback_host(self.host)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        metadata = DesktopLockMetadata(pid=os.getpid(), host=self.host, port=self.port, created_at_epoch=time.time(), lock_id=uuid.uuid4().hex)
        for _ in range(2):
            try:
                descriptor = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            except FileExistsError:
                existing = self._read_metadata()
                if existing is not None and _pid_is_running(existing.pid):
                    raise DesktopWrapperError("OPERATOR_COCKPIT_DESKTOP_INSTANCE_ALREADY_RUNNING")
                try:
                    self.path.unlink()
                except FileNotFoundError:
                    pass
                continue
            try:
                os.write(descriptor, json.dumps(asdict(metadata), ensure_ascii=False, indent=2).encode("utf-8"))
            finally:
                os.close(descriptor)
            self._acquired = True
            self._metadata = metadata
            return metadata
        raise DesktopWrapperError("OPERATOR_COCKPIT_DESKTOP_LOCK_ACQUIRE_FAILED")

    def release(self) -> None:
        if not self._acquired:
            return
        self._acquired = False
        metadata = self._metadata
        self._metadata = None
        if metadata is None:
            return
        existing = self._read_metadata()
        if existing is None or existing.lock_id != metadata.lock_id:
            return
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass

    def __enter__(self) -> DesktopInstanceLock:
        self.acquire()
        return self

    def __exit__(self, _exc_type: object, _exc: object, _traceback: object) -> None:
        self.release()



def _normalize_loopback_base_url(base_url: str) -> str:
    """Normalize one HTTP loopback origin and reject credentials, paths and fragments."""
    parsed = urllib.parse.urlparse(base_url)
    host = parsed.hostname or ""
    if parsed.scheme.lower() != "http" or not _is_loopback_host(host):
        raise DesktopWrapperError("NATIVE_DESKTOP_EXPORT_NON_LOOPBACK_BLOCKED")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise DesktopWrapperError("NATIVE_DESKTOP_EXPORT_BASE_URL_INVALID")
    if parsed.path not in {"", "/"}:
        raise DesktopWrapperError("NATIVE_DESKTOP_EXPORT_BASE_URL_INVALID")
    try:
        port = parsed.port
    except ValueError as error:
        raise DesktopWrapperError("NATIVE_DESKTOP_EXPORT_BASE_URL_INVALID") from error
    if port is None:
        raise DesktopWrapperError("NATIVE_DESKTOP_EXPORT_BASE_URL_INVALID")
    display_host = f"[{host}]" if ":" in host else host
    return f"http://{display_host}:{port}"


def _dashboard_origin(dashboard_url: str) -> str:
    parsed = urllib.parse.urlparse(dashboard_url)
    host = parsed.hostname or ""
    try:
        port = parsed.port
    except ValueError as error:
        raise DesktopWrapperError("NATIVE_DESKTOP_EXPORT_BASE_URL_INVALID") from error
    if port is None:
        raise DesktopWrapperError("NATIVE_DESKTOP_EXPORT_BASE_URL_INVALID")
    display_host = f"[{host}]" if ":" in host else host
    return _normalize_loopback_base_url(f"{parsed.scheme}://{display_host}:{port}")


def _resolve_native_action(action_code: str, *, expected_mode: str | None = None) -> NativeDesktopActionSpec:
    spec = NATIVE_DESKTOP_ACTIONS.get(str(action_code or ""))
    if spec is None or (expected_mode is not None and spec.mode != expected_mode):
        raise DesktopWrapperError("NATIVE_DESKTOP_ACTION_NOT_ALLOWED")
    return spec


def _read_bounded_local_get(base_url: str, endpoint: str, max_bytes: int, timeout_seconds: float = DEFAULT_NATIVE_EXPORT_TIMEOUT_SECONDS) -> bytes:
    """Read one fixed local GET endpoint without redirects or unbounded buffering."""
    normalized_base = _normalize_loopback_base_url(base_url)
    if not endpoint.startswith("/api/operator-cockpit-v2/") or "?" in endpoint or "#" in endpoint:
        raise DesktopWrapperError("NATIVE_DESKTOP_EXPORT_ENDPOINT_NOT_ALLOWED")
    url = normalized_base + endpoint
    opener = urllib.request.build_opener(_NoRedirectHandler())
    request = urllib.request.Request(url, method="GET", headers={"Cache-Control": "no-store"})
    try:
        with opener.open(request, timeout=timeout_seconds) as response:
            final_url = response.geturl()
            final = urllib.parse.urlparse(final_url)
            final_origin = _dashboard_origin(f"{final.scheme}://{final.netloc}/dashboard")
            if final_origin != normalized_base:
                raise DesktopWrapperError("NATIVE_DESKTOP_EXPORT_ORIGIN_CHANGED")
            raw_length = response.headers.get("Content-Length")
            if raw_length:
                try:
                    declared_length = int(raw_length)
                except ValueError as error:
                    raise DesktopWrapperError("NATIVE_DESKTOP_EXPORT_CONTENT_LENGTH_INVALID") from error
                if declared_length < 0 or declared_length > max_bytes:
                    raise DesktopWrapperError("NATIVE_DESKTOP_EXPORT_TOO_LARGE")
            chunks: list[bytes] = []
            total = 0
            while True:
                chunk = response.read(min(64 * 1024, max_bytes - total + 1))
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise DesktopWrapperError("NATIVE_DESKTOP_EXPORT_TOO_LARGE")
                chunks.append(chunk)
            return b"".join(chunks)
    except urllib.error.HTTPError as error:
        raise DesktopWrapperError(f"NATIVE_DESKTOP_EXPORT_HTTP_ERROR: {error.code}") from error
    except urllib.error.URLError as error:
        raise DesktopWrapperError(f"NATIVE_DESKTOP_EXPORT_LOCAL_GET_FAILED: {error.reason}") from error


def _write_binary_atomic(destination: Path, payload: bytes) -> None:
    """Atomically write a user-selected local export target without touching project state."""
    target = destination.expanduser().resolve()
    if not target.parent.is_dir():
        raise DesktopWrapperError("NATIVE_DESKTOP_EXPORT_TARGET_DIRECTORY_MISSING")
    temporary = target.parent / f".{target.name}.{uuid.uuid4().hex}.tmp"
    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _normalize_save_dialog_result(result: Any) -> Path | None:
    if result is None or result == "":
        return None
    if isinstance(result, (list, tuple)):
        if not result:
            return None
        result = result[0]
    if not isinstance(result, str) or not result.strip():
        raise DesktopWrapperError("NATIVE_DESKTOP_SAVE_DIALOG_RESULT_INVALID")
    return Path(result)


class NativeDesktopExportBridge:
    """Expose a minimal allowlisted desktop bridge to pywebview JavaScript."""

    def __init__(
        self,
        base_url: str,
        *,
        fetcher: NativeFetch = _read_bounded_local_get,
        writer: NativeWrite = _write_binary_atomic,
    ) -> None:
        self.base_url = _normalize_loopback_base_url(base_url)
        self._fetcher = fetcher
        self._writer = writer
        self._window: Any | None = None
        self._webview_module: Any | None = None

    def bind_window(self, window: Any, webview_module: Any) -> None:
        self._window = window
        self._webview_module = webview_module

    def _fetch(self, spec: NativeDesktopActionSpec) -> bytes:
        return self._fetcher(self.base_url, spec.endpoint, spec.max_bytes, DEFAULT_NATIVE_EXPORT_TIMEOUT_SECONDS)

    def _choose_save_path(self, filename: str) -> Path | None:
        if self._window is None or self._webview_module is None:
            raise DesktopWrapperError("NATIVE_DESKTOP_SAVE_DIALOG_NOT_BOUND")
        save_dialog = getattr(self._webview_module, "SAVE_DIALOG", None)
        if save_dialog is None:
            raise DesktopWrapperError("NATIVE_DESKTOP_SAVE_DIALOG_UNAVAILABLE")
        create_file_dialog = getattr(self._window, "create_file_dialog", None)
        if not callable(create_file_dialog):
            raise DesktopWrapperError("NATIVE_DESKTOP_SAVE_DIALOG_UNAVAILABLE")
        return _normalize_save_dialog_result(create_file_dialog(save_dialog, save_filename=filename))

    def export_file(self, action_code: str) -> dict[str, Any]:
        try:
            spec = _resolve_native_action(action_code, expected_mode="download")
            target = self._choose_save_path(spec.filename)
            if target is None:
                return {"ok": True, "cancelled": True, "action_code": spec.action_code}
            payload = self._fetch(spec)
            self._writer(target, payload)
            return {"ok": True, "cancelled": False, "action_code": spec.action_code, "filename": target.name, "bytes_written": len(payload)}
        except DesktopWrapperError as error:
            return {"ok": False, "cancelled": False, "action_code": str(action_code or ""), "error": str(error)}
        except OSError as error:
            return {"ok": False, "cancelled": False, "action_code": str(action_code or ""), "error": f"NATIVE_DESKTOP_EXPORT_WRITE_FAILED: {error}"}

    def read_text(self, action_code: str) -> dict[str, Any]:
        try:
            spec = _resolve_native_action(action_code, expected_mode="text")
            payload = self._fetch(spec)
            decoded = payload.decode("utf-8")
            try:
                content = json.dumps(json.loads(decoded), ensure_ascii=False, indent=2)
            except json.JSONDecodeError:
                content = decoded
            return {"ok": True, "action_code": spec.action_code, "filename": spec.filename, "content": content}
        except UnicodeDecodeError:
            return {"ok": False, "action_code": str(action_code or ""), "error": "NATIVE_DESKTOP_TEXT_EXPORT_UTF8_INVALID"}
        except DesktopWrapperError as error:
            return {"ok": False, "action_code": str(action_code or ""), "error": str(error)}


NATIVE_DESKTOP_EXPORT_BRIDGE_JS = r"""
(() => {
  const ACTIONS = {
    '/api/operator-cockpit-v2/export/snapshot.json': ['download', 'DOWNLOAD_SNAPSHOT_JSON'],
    '/api/operator-cockpit-v2/view/latest-audit.json': ['text', 'OPEN_LATEST_AUDIT_JSON'],
    '/api/operator-cockpit-v2/actions/manifest': ['text', 'OPEN_ACTION_MANIFEST'],
    '/api/operator-cockpit-v2/export/evidence-pack.zip': ['download', 'DOWNLOAD_EVIDENCE_PACK_ZIP'],
    '/api/operator-cockpit-v2/export/latest-ledger': ['download', 'DOWNLOAD_MERGED_LEDGER_JSONL']
  };
  function feedback(message) {
    const node = document.getElementById('action-feedback');
    if (node) node.textContent = message;
  }
  function ensureModal() {
    let overlay = document.getElementById('native-desktop-json-overlay');
    if (overlay) return overlay;
    overlay = document.createElement('div');
    overlay.id = 'native-desktop-json-overlay';
    overlay.style.cssText = 'position:fixed;inset:0;z-index:99999;background:rgba(1,7,15,.82);display:none;padding:28px;';
    overlay.innerHTML = '<div style="height:100%;max-width:1180px;margin:auto;background:#0e1a2b;border:1px solid rgba(255,255,255,.15);border-radius:14px;display:flex;flex-direction:column;overflow:hidden"><div style="display:flex;justify-content:space-between;align-items:center;padding:14px 16px;border-bottom:1px solid rgba(255,255,255,.1)"><strong id="native-desktop-json-title">JSON</strong><button id="native-desktop-json-close" type="button" style="padding:7px 12px;border-radius:8px;border:1px solid rgba(255,255,255,.15);background:#162841;color:#e8f0fb;cursor:pointer">Kapat</button></div><pre id="native-desktop-json-content" style="margin:0;padding:16px;overflow:auto;white-space:pre-wrap;color:#d7e4f2;font-size:12px;line-height:1.5"></pre></div>';
    document.body.appendChild(overlay);
    overlay.querySelector('#native-desktop-json-close').addEventListener('click', () => { overlay.style.display = 'none'; });
    return overlay;
  }
  async function run(mode, code) {
    const api = window.pywebview && window.pywebview.api;
    if (!api) { feedback('Native desktop export bridge hazır değil.'); return; }
    feedback('İşlem hazırlanıyor…');
    try {
      if (mode === 'download') {
        const result = await api.export_file(code);
        if (!result.ok) { feedback('İndirme başarısız: ' + (result.error || 'Bilinmeyen hata')); return; }
        if (result.cancelled) { feedback('İndirme iptal edildi.'); return; }
        feedback('Dosya kaydedildi: ' + result.filename + ' · ' + result.bytes_written + ' byte');
        return;
      }
      const result = await api.read_text(code);
      if (!result.ok) { feedback('JSON görünümü açılamadı: ' + (result.error || 'Bilinmeyen hata')); return; }
      const overlay = ensureModal();
      overlay.querySelector('#native-desktop-json-title').textContent = result.filename || 'JSON';
      overlay.querySelector('#native-desktop-json-content').textContent = result.content || '';
      overlay.style.display = 'block';
      feedback('JSON görünümü açıldı: ' + (result.filename || 'JSON'));
    } catch (error) {
      feedback('Native desktop işlem hatası: ' + String(error));
    }
  }
  function install() {
    if (window.__tradebotNativeExportBridgeInstalled) return;
    window.__tradebotNativeExportBridgeInstalled = true;
    document.addEventListener('click', event => {
      const anchor = event.target && event.target.closest ? event.target.closest('a[href]') : null;
      if (!anchor) return;
      const path = new URL(anchor.href, window.location.href).pathname;
      const action = ACTIONS[path];
      if (!action) return;
      event.preventDefault();
      event.stopPropagation();
      run(action[0], action[1]);
    }, true);
  }
  if (window.pywebview && window.pywebview.api) install();
  else window.addEventListener('pywebviewready', install, { once: true });
})();
"""


def _inject_native_desktop_export_bridge(window: Any) -> bool:
    evaluate_js = getattr(window, "evaluate_js", None)
    if not callable(evaluate_js):
        return False
    evaluate_js(NATIVE_DESKTOP_EXPORT_BRIDGE_JS)
    return True


def _attach_native_desktop_export_bridge(window: Any) -> bool:
    if window is None:
        return False
    events = getattr(window, "events", None)
    loaded = getattr(events, "loaded", None)
    if loaded is None:
        return _inject_native_desktop_export_bridge(window)

    def inject(*_args: Any, **_kwargs: Any) -> None:
        _inject_native_desktop_export_bridge(window)

    try:
        loaded += inject
    except Exception as error:
        raise DesktopWrapperError(f"NATIVE_DESKTOP_WEBVIEW_EVENT_BIND_FAILED: {error}") from error
    return True

def _probe_local_health(url: str, timeout_seconds: float = 2.0) -> dict[str, Any]:
    """Probe only the local cockpit health endpoint."""
    try:
        with urllib.request.urlopen(url, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return {"reachable": True, "status_code": response.status, "payload": payload}
    except (OSError, urllib.error.URLError, ValueError, json.JSONDecodeError) as error:
        return {"reachable": False, "status_code": None, "error": str(error), "payload": {}}


def _wait_for_local_health(url: str, *, timeout_seconds: float = DEFAULT_HEALTH_TIMEOUT_SECONDS, probe: HealthProbe = _probe_local_health) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    last: dict[str, Any] = {"reachable": False, "status_code": None, "payload": {}}
    while time.monotonic() < deadline:
        last = probe(url, min(1.0, timeout_seconds))
        if last.get("reachable") and bool((last.get("payload") or {}).get("ok")):
            return last
        time.sleep(0.05)
    raise DesktopWrapperError(f"LOCAL_COCKPIT_HEALTH_TIMEOUT: {last}")


def _assert_port_available(host: str, port: int) -> None:
    """Fail fast when the configured loopback port is already occupied."""
    _assert_loopback_host(host)
    if port == 0:
        return
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as candidate:
        candidate.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            candidate.bind((host, port))
        except OSError as error:
            raise DesktopWrapperError(f"LOCAL_COCKPIT_PORT_ALREADY_IN_USE: {host}:{port}") from error


def start_local_cockpit_server(
    project_root: Path,
    *,
    host: str = DEFAULT_DESKTOP_HOST,
    port: int = DEFAULT_DESKTOP_PORT,
    health_probe: HealthProbe = _probe_local_health,
) -> RunningCockpitServer:
    """Start the existing read-only cockpit server in a background daemon thread."""
    _assert_loopback_host(host)
    _assert_port_available(host, port)
    try:
        server = make_operator_cockpit_server(project_root.resolve(), host=host, port=port)
    except OSError as error:
        raise DesktopWrapperError(f"LOCAL_COCKPIT_SERVER_START_FAILED: {host}:{port}") from error
    actual_host, actual_port = server.server_address[:2]
    url = f"http://{actual_host}:{actual_port}{DEFAULT_DASHBOARD_PATH}"
    health_url = f"http://{actual_host}:{actual_port}{DEFAULT_HEALTH_PATH}"
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.25}, daemon=True, name="tradebot-cockpit-local-server")
    thread.start()
    running = RunningCockpitServer(server=server, thread=thread, url=url, health_url=health_url)
    try:
        _wait_for_local_health(health_url, probe=health_probe)
    except Exception:
        running.stop()
        raise
    return running


def _load_pywebview() -> ModuleType:
    try:
        return importlib.import_module("webview")
    except ModuleNotFoundError as error:
        raise DesktopWrapperError("PYWEBVIEW_DEPENDENCY_MISSING: run tools/install_operator_cockpit_v2_desktop_dependency_4B436626D.ps1") from error


def launch_desktop_shell(
    project_root: Path,
    *,
    host: str = DEFAULT_DESKTOP_HOST,
    port: int = DEFAULT_DESKTOP_PORT,
    lock_path: Path | None = None,
    webview_loader: WebViewLoader = _load_pywebview,
    health_probe: HealthProbe = _probe_local_health,
    allow_browser_fallback: bool = False,
) -> int:
    """Launch one embedded local cockpit window and cleanly own the server lifecycle."""
    _assert_loopback_host(host)
    with DesktopInstanceLock(lock_path, host=host, port=port):
        running = start_local_cockpit_server(project_root, host=host, port=port, health_probe=health_probe)
        try:
            try:
                webview_module = webview_loader()
            except DesktopWrapperError:
                if not allow_browser_fallback:
                    raise
                webbrowser.open(running.url)
                try:
                    while running.thread.is_alive():
                        time.sleep(0.25)
                except KeyboardInterrupt:
                    return 0
                return 0
            bridge = NativeDesktopExportBridge(_dashboard_origin(running.url))
            window = webview_module.create_window(
                DEFAULT_WINDOW_TITLE,
                running.url,
                width=DEFAULT_WINDOW_WIDTH,
                height=DEFAULT_WINDOW_HEIGHT,
                min_size=(DEFAULT_WINDOW_MIN_WIDTH, DEFAULT_WINDOW_MIN_HEIGHT),
                js_api=bridge,
            )
            bridge.bind_window(window, webview_module)
            _attach_native_desktop_export_bridge(window)
            webview_module.start(debug=False)
            return 0
        finally:
            running.stop()


def run_headless_smoke(
    project_root: Path,
    *,
    host: str = DEFAULT_DESKTOP_HOST,
    port: int = 0,
    lock_path: Path | None = None,
    health_probe: HealthProbe = _probe_local_health,
) -> dict[str, Any]:
    """Start, probe and stop the local server without opening any UI."""
    _assert_loopback_host(host)
    with DesktopInstanceLock(lock_path, host=host, port=port):
        running = start_local_cockpit_server(project_root, host=host, port=port, health_probe=health_probe)
        try:
            health = health_probe(running.health_url, 2.0)
            return {
                "ok": bool(health.get("reachable") and (health.get("payload") or {}).get("ok")),
                "desktop_wrapper_version": OPERATOR_COCKPIT_V2_DESKTOP_WRAPPER_VERSION,
                "desktop_local_only": True,
                "single_instance": True,
                "url": running.url,
                "health_url": running.health_url,
                "health": health,
                "config_mutation_performed": False,
                "scheduler_mutation_performed": False,
                "trading_action_performed": False,
            }
        finally:
            running.stop()
