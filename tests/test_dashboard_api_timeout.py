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


class DummyResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


class DummyApp:
    def __init__(self) -> None:
        self.api_base = 'http://127.0.0.1:8787'
        self.messages: list[str] = []

    def _append_backend(self, text: str) -> None:
        self.messages.append(text)


def test_stop_endpoint_uses_longer_timeout(monkeypatch) -> None:
    app = DummyApp()
    calls: list[float] = []

    def fake_post(url: str, timeout: float):
        calls.append(timeout)
        return DummyResponse({'ok': True})

    import tradebot.ui.dashboard as dashboard_module
    monkeypatch.setattr(dashboard_module.requests, 'post', fake_post)

    DashboardApp.api_post(app, '/stop')  # type: ignore[arg-type]
    DashboardApp.api_post(app, '/start')  # type: ignore[arg-type]

    assert calls == [15, 5]
