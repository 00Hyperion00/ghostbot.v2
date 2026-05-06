from __future__ import annotations

from types import SimpleNamespace

from tradebot.ui.dashboard import DashboardApp


class _DummyWidget:
    def __init__(self) -> None:
        self.config: dict[str, object] = {}
        self.text = ''

    def configure(self, **kwargs):
        self.config.update(kwargs)

    def delete(self, *_args):
        self.text = ''

    def insert(self, *_args):
        self.text += str(_args[-1])

    def see(self, *_args):
        return None


class _DummyEntry:
    def __init__(self, value: str = '') -> None:
        self.value = value

    def get(self) -> str:
        return self.value

    def delete(self, *_args):
        self.value = ''

    def insert(self, *_args):
        self.value = str(_args[-1])


class _DummyButton:
    def __init__(self) -> None:
        self.config: dict[str, object] = {}

    def configure(self, **kwargs):
        self.config.update(kwargs)


class _DummyPage:
    def __init__(self, raisable: bool = True) -> None:
        self.raised = False
        self.raisable = raisable

    def tkraise(self):
        if self.raisable:
            self.raised = True


class _NoRaisePage:
    pass


def _app_probe() -> DashboardApp:
    app = DashboardApp.__new__(DashboardApp)
    app.api_base = 'http://127.0.0.1:8787'
    app.api_host = '127.0.0.1'
    app.api_port = 8787
    app.project_root = SimpleNamespace()
    app.config_path = SimpleNamespace(name='config.local.yaml')
    app.backend_box = _DummyWidget()
    app.status_box = _DummyWidget()
    app.log_box = _DummyWidget()
    app.latest_box = _DummyWidget()
    app.lbl_connection = _DummyWidget()
    app.lbl_state = _DummyWidget()
    app.lbl_symbol = _DummyWidget()
    app.lbl_ws = _DummyWidget()
    app.nav_buttons = {'main': _DummyButton(), 'audit': _DummyButton(), 'chart': _DummyButton()}
    app.pages = {'main': _DummyPage(), 'audit': _NoRaisePage(), 'chart': _DummyPage()}
    app.form = {'symbol': _DummyEntry('ETHUSDT')}
    app._last_logs = []
    app._backend_owned = False
    app.backend_process = None
    app._active_page = 'main'
    app.audit_search_entry = _DummyEntry('')
    app.audit_symbol_entry = _DummyEntry('')
    app.audit_code_entry = _DummyEntry('')
    app.chart_info = None
    app._chart_poll_counter = 0
    app.CHART_REFRESH_EVERY = 4
    app._last_connected = False
    return app


def test_show_page_ignores_pages_without_tkraise() -> None:
    app = _app_probe()
    DashboardApp.show_page(app, 'audit')
    assert app._active_page == 'audit'
    assert app.nav_buttons['audit'].config['fg_color'] == ('gray75', 'gray30')


def test_set_offline_ui_handles_missing_form_and_chart_info() -> None:
    app = _app_probe()
    del app.form
    del app.chart_info
    DashboardApp._set_offline_ui(app, 'boom')
    assert app.lbl_connection.config['text'] == 'Backend: OFFLINE'
    assert 'Backend çevrimdışı' in app.status_box.text


def test_poll_health_keeps_online_when_status_fails() -> None:
    app = _app_probe()

    def api_get(path: str, *, timeout: float = 2.5):
        if path == '/health':
            return {'ok': True, 'symbol': 'ETHUSDT', 'running': True, 'bootstrap_ok': True}
        raise RuntimeError('status boom')

    app.api_get = api_get
    app._append_backend = DashboardApp._append_backend.__get__(app, DashboardApp)
    DashboardApp._poll_health_and_status(app)
    assert app._last_connected is True
    assert app.lbl_connection.config['text'] == 'Backend: ONLINE'
    assert 'Backend online, ancak /status okunamadı' in app.status_box.text
