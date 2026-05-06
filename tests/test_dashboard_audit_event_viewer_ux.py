from __future__ import annotations

import sys
from types import ModuleType


class _DummyWidget:
    def __init__(self, *args, value: str = '', **kwargs) -> None:
        self._value = value
        self.text = ''
        self.kwargs = dict(kwargs)

    def configure(self, **kwargs):
        self.kwargs.update(kwargs)

    def grid(self, *args, **kwargs):
        return None

    def grid_rowconfigure(self, *args, **kwargs):
        return None

    def grid_columnconfigure(self, *args, **kwargs):
        return None

    def insert(self, *args, **kwargs):
        if args:
            value = str(args[-1])
            self._value = value
            self.text += value

    def delete(self, *args, **kwargs):
        self._value = ''
        self.text = ''

    def see(self, *args, **kwargs):
        return None

    def set(self, value):
        self._value = str(value)

    def get(self):
        return self._value


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
ctk_stub.CTkSwitch = _DummyWidget
ctk_stub.set_appearance_mode = lambda *args, **kwargs: None
ctk_stub.set_default_color_theme = lambda *args, **kwargs: None
sys.modules.setdefault('customtkinter', ctk_stub)

from tradebot.ui.dashboard import (  # noqa: E402
    AUDIT_VIEWER_CONTRACT_VERSION,
    DashboardApp,
    build_audit_query_path,
    build_audit_summary_text,
    filter_audit_events,
    format_log_line,
)


def _event(ts: int, code: str, category: str, severity: str, **data):
    return {
        'ts': ts,
        'level': 'WARN' if severity == 'warning' else 'INFO',
        'code': code,
        'message': f'{code} message',
        'data': data,
        'category': category,
        'severity': severity,
        'correlation_id': data.get('clientOrderId') or data.get('signalKey'),
    }


def test_build_audit_query_path_uses_only_active_filters() -> None:
    path = build_audit_query_path(
        limit=20,
        order='desc',
        category='Orders',
        severity='warning',
        code_prefix='order_',
    )

    assert path.startswith('/events/audit?')
    assert 'limit=20' in path
    assert 'order=desc' in path
    assert 'category=Orders' in path
    assert 'severity=warning' in path
    assert 'code_prefix=ORDER_' in path
    assert 'since_ts' not in path


def test_build_audit_query_path_omits_all_filters() -> None:
    path = build_audit_query_path(limit=0, order='asc', category='All', severity='All', code_prefix='')

    assert path == '/events/audit?limit=0&order=asc'


def test_filter_audit_events_supports_category_severity_correlation_and_text_search() -> None:
    events = [
        _event(1, 'ORDER_SUBMITTED', 'Orders', 'info', symbol='ETHUSDT', clientOrderId='CID-1'),
        _event(2, 'AUTO_ENTRY_BLOCKED', 'Guards', 'warning', symbol='ETHUSDT', signalKey='SIG-2'),
        _event(3, 'AI_RELOAD_SUCCEEDED', 'Model', 'info', model_path='models/m.ubj'),
    ]

    filtered = filter_audit_events(
        events,
        category_filter='Guards',
        severity_filter='warning',
        correlation_filter='SIG',
        search='blocked',
    )

    assert [event['code'] for event in filtered] == ['AUTO_ENTRY_BLOCKED']


def test_format_log_line_surfaces_severity_category_and_correlation() -> None:
    line = format_log_line(_event(1, 'ORDER_SUBMITTED', 'Orders', 'info', clientOrderId='CID-3'))

    assert 'INFO' in line
    assert 'Orders' in line
    assert 'ORDER_SUBMITTED' in line
    assert 'corr=CID-3' in line


def test_build_audit_summary_text_includes_counts_and_contract() -> None:
    payload = {
        'contract_version': AUDIT_VIEWER_CONTRACT_VERSION,
        'count': 2,
        'summary': {
            'event_count': 2,
            'latest_ts': 1000,
            'warning_count': 1,
            'error_count': 0,
            'counts_by_category': {'Orders': 1, 'Guards': 1},
            'counts_by_severity': {'info': 1, 'warning': 1},
            'last_warning': {'code': 'AUTO_ENTRY_BLOCKED'},
            'last_error': None,
        },
    }

    text = build_audit_summary_text(payload, [])

    assert AUDIT_VIEWER_CONTRACT_VERSION in text
    assert 'Orders:1' in text
    assert 'warning:1' in text
    assert 'AUTO_ENTRY_BLOCKED' in text


class _App(DashboardApp):
    pass


def test_dashboard_render_logs_applies_audit_filters_and_summary() -> None:
    app = _App.__new__(_App)
    app._last_logs = [
        _event(1, 'ORDER_SUBMITTED', 'Orders', 'info', symbol='ETHUSDT', clientOrderId='CID-1'),
        _event(2, 'AUTO_ENTRY_BLOCKED', 'Guards', 'warning', symbol='ETHUSDT', signalKey='SIG-2'),
    ]
    app._last_audit_payload = {
        'contract_version': AUDIT_VIEWER_CONTRACT_VERSION,
        'count': 2,
        'summary': {
            'event_count': 2,
            'counts_by_category': {'Orders': 1, 'Guards': 1},
            'counts_by_severity': {'info': 1, 'warning': 1},
            'warning_count': 1,
            'error_count': 0,
            'latest_ts': 2,
            'last_warning': {'code': 'AUTO_ENTRY_BLOCKED'},
            'last_error': None,
        },
    }
    app.audit_search_entry = _DummyWidget(value='blocked')
    app.audit_symbol_entry = _DummyWidget(value='ETHUSDT')
    app.audit_code_entry = _DummyWidget(value='')
    app.audit_code_prefix_entry = _DummyWidget(value='')
    app.audit_correlation_entry = _DummyWidget(value='SIG')
    app.audit_category_filter = _DummyWidget(value='Guards')
    app.audit_severity_filter = _DummyWidget(value='warning')
    app.latest_box = _DummyWidget()
    app.audit_box = _DummyWidget()
    app.audit_summary_box = _DummyWidget()

    DashboardApp._render_logs(app)

    assert 'AUTO_ENTRY_BLOCKED' in app.audit_box.text
    assert 'ORDER_SUBMITTED' not in app.audit_box.text
    assert 'Rendered count  : 1' in app.audit_summary_box.text
    assert 'Warnings/errors : 1 / 0' in app.audit_summary_box.text
