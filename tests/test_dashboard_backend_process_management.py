from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

from tradebot.ui.dashboard import DashboardApp


class DummyProc:
    def __init__(self):
        self.stdout = None
        self.terminated = False
        self.killed = False

    def poll(self):
        return None

    def terminate(self):
        self.terminated = True

    def wait(self, timeout=None):
        return 0

    def kill(self):
        self.killed = True


class DummyEntry:
    def __init__(self, value=''):
        self.value = value

    def get(self):
        return self.value


class DummyBox:
    def __init__(self):
        self.lines: list[str] = []
    def configure(self, **kwargs):
        return None
    def insert(self, *_args):
        self.lines.append(str(_args[-1]).rstrip())
    def see(self, *_args):
        return None


def make_app() -> DashboardApp:
    app = DashboardApp.__new__(DashboardApp)
    app.api_base = 'http://127.0.0.1:8787'
    app.api_host = '127.0.0.1'
    app.api_port = 8787
    app.project_root = Path('/tmp')
    app.config_path = Path('/tmp/config.local.yaml')
    app.backend_box = DummyBox()
    app.form = {'symbol': DummyEntry('ETHUSDT')}
    app._backend_owned = False
    app.backend_process = None
    app.save_config = Mock()
    app._creationflags = Mock(return_value=0)
    app._read_process_output = Mock()
    return app


def test_start_backend_attaches_when_health_is_already_online(monkeypatch) -> None:
    app = make_app()
    app._backend_health = Mock(return_value={'ok': True, 'symbol': 'ETHUSDT'})
    popen = Mock()
    monkeypatch.setattr('tradebot.ui.dashboard.subprocess.Popen', popen)
    DashboardApp.start_backend(app)
    popen.assert_not_called()
    assert app._backend_owned is False
    assert any('Mevcut API sürecine bağlanıldı.' in line for line in app.backend_box.lines)


def test_stop_backend_does_not_kill_external_backend() -> None:
    app = make_app()
    app._backend_health = Mock(return_value={'ok': True})
    DashboardApp.stop_backend(app)
    assert any('Harici backend algılandı' in line for line in app.backend_box.lines)


def test_stop_backend_terminates_owned_process() -> None:
    app = make_app()
    proc = DummyProc()
    app.backend_process = proc
    app._backend_owned = True
    app._backend_health = Mock(return_value=None)
    DashboardApp.stop_backend(app)
    assert proc.terminated is True
    assert app.backend_process is None
    assert app._backend_owned is False
