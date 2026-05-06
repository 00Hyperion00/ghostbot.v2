from __future__ import annotations

import sys
from types import ModuleType


class _DummyWidget:
    def __init__(self, *args, value: str = '', **kwargs) -> None:
        self.text = ''
        self._value = value
        self.kwargs = {}

    def configure(self, **kwargs):
        self.kwargs.update(kwargs)

    def grid(self, *args, **kwargs):
        return None

    def grid_rowconfigure(self, *args, **kwargs):
        return None

    def grid_columnconfigure(self, *args, **kwargs):
        return None

    def insert(self, *args):
        if args:
            self.text += str(args[-1])

    def delete(self, *args):
        self.text = ''

    def get(self):
        return self._value


class _DummyCTk(_DummyWidget):
    def title(self, *args, **kwargs): return None
    def geometry(self, *args, **kwargs): return None
    def minsize(self, *args, **kwargs): return None
    def protocol(self, *args, **kwargs): return None
    def after(self, *args, **kwargs): return None


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


yaml_stub = ModuleType('yaml')
yaml_stub.safe_load = lambda *args, **kwargs: {}
yaml_stub.safe_dump = lambda *args, **kwargs: ''
sys.modules.setdefault('yaml', yaml_stub)

requests_stub = ModuleType('requests')
requests_stub.get = lambda *args, **kwargs: None
sys.modules.setdefault('requests', requests_stub)

from tradebot.ui.dashboard import build_operator_cockpit_text


def test_operator_cockpit_text_consolidates_key_snapshots() -> None:
    text = build_operator_cockpit_text({
        'contract_version': '4B.4.3.6.6.20',
        'state': 'IN_POSITION',
        'ws_status': 'CONNECTED',
        'diagnostics_snapshot': {
            'severity': 'warning',
            'ready_to_operate': True,
            'reason_codes': ['RECENT_WARNING_EVENTS_PRESENT'],
            'latest_critical_events': [{'code': 'ORDER_CANCELED'}],
        },
        'config_safety_snapshot': {
            'severity': 'ok',
            'safe_to_trade': True,
            'safe_to_auto_trade': True,
        },
        'decision_audit_snapshot': {
            'action': 'SUBMIT_ENTRY',
            'action_intent': 'ENTRY',
            'should_submit_order': True,
            'effective_decision': {'signal': 'BUY', 'reason': 'AI Kararı'},
            'guard_path': {'action': 'SUBMIT_ENTRY', 'skip_code': None},
        },
        'reconciliation_snapshot': {'state': 'TRACKING', 'recommended_action': 'WAIT'},
        'position_snapshot': {'present': True, 'qty': 0.01},
        'pending_snapshot': {'present': False, 'side': None, 'status': None},
        'risk_snapshot': {'safe_mode': False, 'kill_switch_active': False},
        'model_quality_snapshot': {'severity': 'warming_up', 'sample_count': 2, 'recommendation': 'OK'},
        'performance_snapshot': {
            'closed_trade_count': 3,
            'realized_pnl': 1.23,
            'win_rate_pct': 66.7,
            'profit_factor': 1.8,
            'open_trade': {'present': True},
        },
    })

    assert 'Operator Cockpit' in text
    assert 'Contract        : 4B.4.3.6.6.20' in text
    assert 'Runtime         : IN_POSITION / WS CONNECTED' in text
    assert 'Diagnostics     : warning / ready YES' in text
    assert 'Config safety   : ok / trade YES / auto YES' in text
    assert 'Decision        : BUY / ENTRY / submit YES' in text
    assert 'Reconciliation  : TRACKING / WAIT' in text
    assert 'Position        : present YES / qty 0.01' in text
    assert 'Performance     : closed 3 / pnl 1.23 / win 66.7% / pf 1.8' in text
    assert 'Reason codes    : RECENT_WARNING_EVENTS_PRESENT' in text


def test_operator_cockpit_text_handles_missing_snapshots() -> None:
    text = build_operator_cockpit_text({})

    assert 'Operator Cockpit' in text
    assert 'Contract        : -' in text
    assert 'Diagnostics     : - / ready NO' in text
    assert 'Decision        : - / - / submit NO' in text
    assert 'Reconciliation  : - / -' in text
    assert 'Critical events : 0' in text
