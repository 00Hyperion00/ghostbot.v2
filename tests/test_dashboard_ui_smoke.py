from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType


class _BaseWidget:
    def __init__(self, *args, **kwargs):
        self._value = ''
        self.kwargs = dict(kwargs)

    def grid(self, *args, **kwargs):
        self.kwargs.update(kwargs)

    def grid_columnconfigure(self, index, **kwargs):
        if not isinstance(index, int):
            raise TypeError(f'grid_columnconfigure index must be int, got {type(index).__name__}')

    def grid_rowconfigure(self, index, **kwargs):
        if not isinstance(index, int):
            raise TypeError(f'grid_rowconfigure index must be int, got {type(index).__name__}')

    def configure(self, **kwargs):
        self.kwargs.update(kwargs)

    def insert(self, index, value):
        self._value = str(value)

    def delete(self, start, end=None):
        self._value = ''

    def get(self):
        return self._value

    def set(self, value):
        self._value = str(value)

    def select(self):
        self._value = 1

    def deselect(self):
        self._value = 0

    def see(self, *args, **kwargs):
        return None


class _CTk(_BaseWidget):
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


class _Textbox(_BaseWidget):
    pass


ctk_stub = ModuleType('customtkinter')
ctk_stub.CTk = _CTk
ctk_stub.CTkFrame = _BaseWidget
ctk_stub.CTkLabel = _BaseWidget
ctk_stub.CTkTextbox = _Textbox
ctk_stub.CTkButton = _BaseWidget
ctk_stub.CTkEntry = _BaseWidget
ctk_stub.CTkOptionMenu = _BaseWidget
class _TabView(_BaseWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._tabs = {}

    def add(self, name):
        self._tabs[name] = _BaseWidget()

    def tab(self, name):
        return self._tabs.setdefault(name, _BaseWidget())

ctk_stub.CTkSwitch = _BaseWidget
ctk_stub.CTkTabview = _TabView
ctk_stub.set_appearance_mode = lambda *args, **kwargs: None
ctk_stub.set_default_color_theme = lambda *args, **kwargs: None
sys.modules['customtkinter'] = ctk_stub

from tradebot.ui.dashboard import DashboardApp


def test_dashboard_app_builds_ui_without_runtime_errors(tmp_path: Path) -> None:
    cfg = tmp_path / 'config.local.yaml'
    app = DashboardApp(str(cfg))

    assert hasattr(app, 'status_box')
    assert hasattr(app, 'risk_box')
    assert hasattr(app, 'position_box')
    assert hasattr(app, 'ai_box')
    assert hasattr(app, 'pending_box')
    assert hasattr(app, 'log_box')
    assert hasattr(app, 'event_box')
    assert hasattr(app, 'event_filter_menu')
    assert hasattr(app, 'event_count_label')
    assert hasattr(app, 'backend_box')
    assert hasattr(app, 'btn_force_buy')
    assert hasattr(app, 'btn_force_sell')
    assert hasattr(app, 'btn_cancel_pending')
    assert hasattr(app, 'controls_hint')
    assert 'ai_model_path' in app.form
