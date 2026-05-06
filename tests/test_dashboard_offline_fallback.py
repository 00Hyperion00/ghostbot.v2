from __future__ import annotations

import sys
from types import ModuleType


class _DummyWidget:
    def __init__(self, *args, **kwargs) -> None:
        self.kwargs = {}
        self.text = ''

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


class _TabView(_DummyWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._tabs = {}

    def add(self, name):
        self._tabs[name] = _DummyWidget()

    def tab(self, name):
        return self._tabs.setdefault(name, _DummyWidget())


ctk_stub = ModuleType('customtkinter')
ctk_stub.CTk = _DummyCTk
ctk_stub.CTkFrame = _DummyWidget
ctk_stub.CTkLabel = _DummyWidget
ctk_stub.CTkTextbox = _DummyWidget
ctk_stub.CTkButton = _DummyWidget
ctk_stub.CTkEntry = _DummyWidget
ctk_stub.CTkOptionMenu = _DummyWidget
ctk_stub.CTkSwitch = _DummyWidget
ctk_stub.CTkTabview = _TabView
ctk_stub.set_appearance_mode = lambda *args, **kwargs: None
ctk_stub.set_default_color_theme = lambda *args, **kwargs: None
sys.modules['customtkinter'] = ctk_stub

from tradebot.ui.dashboard import DashboardApp


class _Label:
    def __init__(self):
        self.kwargs = {}

    def configure(self, **kwargs):
        self.kwargs.update(kwargs)


class _Widget:
    def __init__(self):
        self.text = None


class DummyApp:
    def __init__(self) -> None:
        self.lbl_connection = _Label()
        self.lbl_state = _Label()
        self.lbl_symbol = _Label()
        self.lbl_ws = _Label()
        self.status_box = _Widget()
        self.risk_box = _Widget()
        self.position_box = _Widget()
        self.ai_box = _Widget()
        self.pending_box = _Widget()
        self.log_box = _Widget()
        self.chart_status_label = _Label()
        self.form = {'ai_model_path': type('W', (), {'get': lambda self: 'models/test.ubj'})()}
        self.applied = None

    def _set_text(self, widget, text):
        widget.text = text

    def _optional_set_text(self, widget_name: str, text: str):
        getattr(self, widget_name).text = text

    def _apply_health_aware_controls(self, status):
        self.applied = status


def test_offline_ui_does_not_raise_name_error_and_populates_ai_box():
    app = DummyApp()
    DashboardApp._set_offline_ui(app, 'TEST_REASON')  # type: ignore[arg-type]
    assert 'Backend çevrimdışı (TEST_REASON).' == app.status_box.text
    assert 'Reason          : Backend çevrimdışı (TEST_REASON).' in app.ai_box.text
    assert app.chart_status_label.kwargs['text'] == 'Backend çevrimdışı (TEST_REASON).'
