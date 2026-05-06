from __future__ import annotations

import sys
from types import ModuleType


class _DummyWidget:
    def __init__(self, *args, **kwargs) -> None:
        self.kwargs = {}

    def configure(self, **kwargs):
        self.kwargs.update(kwargs)

    def grid(self, *args, **kwargs):
        return None

    def grid_rowconfigure(self, *args, **kwargs):
        return None

    def grid_columnconfigure(self, *args, **kwargs):
        return None

    def insert(self, *args, **kwargs):
        return None

    def delete(self, *args, **kwargs):
        return None

    def see(self, *args, **kwargs):
        return None

    def set(self, *args, **kwargs):
        return None

    def select(self):
        return None

    def deselect(self):
        return None

    def get(self):
        return ''


class _DummyCTk(_DummyWidget):
    def title(self, *args, **kwargs):
        return None

    def geometry(self, *args, **kwargs):
        return None

    def minsize(self, *args, **kwargs):
        return None

    def protocol(self, *args, **kwargs):
        return None

    def after(self, *args, **kwargs):
        return None

    def destroy(self):
        return None

    def mainloop(self):
        return None


ctk_stub = ModuleType('customtkinter')
ctk_stub.CTk = _DummyCTk
ctk_stub.CTkFrame = _DummyWidget
ctk_stub.CTkLabel = _DummyWidget
ctk_stub.CTkTextbox = _DummyWidget
ctk_stub.CTkButton = _DummyWidget
ctk_stub.CTkEntry = _DummyWidget
ctk_stub.CTkOptionMenu = _DummyWidget
class _TabView(_DummyWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._tabs = {}

    def add(self, name):
        self._tabs[name] = _DummyWidget()

    def tab(self, name):
        return self._tabs.setdefault(name, _DummyWidget())

ctk_stub.CTkSwitch = _DummyWidget
ctk_stub.CTkTabview = _TabView
ctk_stub.set_appearance_mode = lambda *args, **kwargs: None
ctk_stub.set_default_color_theme = lambda *args, **kwargs: None
sys.modules.setdefault('customtkinter', ctk_stub)

from tradebot.ui.dashboard import DashboardApp


class DummyLabel:
    def __init__(self) -> None:
        self.kwargs = {}

    def configure(self, **kwargs):
        self.kwargs.update(kwargs)


class DummyApp:
    def __init__(self) -> None:
        self.lbl_connection = DummyLabel()
        self.lbl_state = DummyLabel()
        self.lbl_symbol = DummyLabel()
        self.lbl_ws = DummyLabel()
        self.status_box = 'status-box'
        self.log_box = 'log-box'
        self._last_status = {}
        self._last_connected = False
        self.calls = []

    def api_get(self, path: str, *, timeout: float = 2.5):
        if path == '/health':
            return {'ok': True, 'symbol': 'SOLUSDT'}
        if path == '/status':
            raise RuntimeError('boom')
        raise AssertionError(path)

    def _set_text(self, widget, text: str) -> None:
        self.calls.append((widget, text))

    def _render_status(self, status):
        self.calls.append(('render', status))

    def _refresh_logs(self):
        self.calls.append(('logs', None))


def test_poll_health_keeps_online_when_status_fails():
    app = DummyApp()

    DashboardApp._poll_health_and_status(app)  # type: ignore[arg-type]

    assert app._last_connected is True
    assert app.lbl_connection.kwargs['text'] == 'Backend: ONLINE'
    assert app.lbl_state.kwargs['text'] == 'Durum: STATUS ERROR'
    assert app.calls[0][0] == 'status-box'
    assert 'Backend online, ancak /status okunamadı' in app.calls[0][1]
