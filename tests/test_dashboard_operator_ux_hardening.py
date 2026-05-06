from __future__ import annotations

import sys
from types import ModuleType


class _DummyWidget:
    def __init__(self, *args, value: str = '', **kwargs) -> None:
        self._value = value
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
            self._value = str(args[-1])

    def delete(self, *args, **kwargs):
        self._value = ''

    def see(self, *args, **kwargs):
        return None

    def set(self, value):
        self._value = str(value)

    def select(self):
        self._value = '1'

    def deselect(self):
        self._value = '0'

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

from tradebot.ui.dashboard import DashboardApp, build_operator_control_state


def _status(
    *,
    state: str = 'FLAT',
    pending: bool = False,
    position: bool = False,
    safe_mode: bool = False,
    kill_switch: bool = False,
    contract_version: str = '4B.4.3.6.6.7',
    account_consistency: str = 'HEALTHY',
    position_consistency: str = 'HEALTHY',
    pending_consistency: str = 'HEALTHY',
    anomaly: str | None = None,
    engine_running: bool = True,
) -> dict:
    return {
        'state': state,
        'engine_running': engine_running,
        'contract_version': contract_version,
        'health_snapshot': {
            'engine_running': engine_running,
            'ws_connected': True,
            'has_pending': pending,
            'has_position': position,
            'account_consistency': account_consistency,
            'position_consistency': position_consistency,
            'pending_consistency': pending_consistency,
            'active_anomaly_code': anomaly,
        },
        'risk_snapshot': {
            'safe_mode': safe_mode,
            'kill_switch_active': kill_switch,
            'safe_mode_reason_code': 'MAX_CONSECUTIVE_LOSSES_REACHED' if safe_mode else None,
        },
        'pending_snapshot': {'present': pending, 'side': 'BUY' if pending else None},
        'position_snapshot': {'present': position},
        'ai_snapshot': {
            'available': True,
            'schema_validated': True,
        },
    }


def test_operator_controls_flat_healthy_allows_entry_only() -> None:
    state = build_operator_control_state(_status(), connected=True)

    assert state['buttons']['force_buy'] is True
    assert state['buttons']['force_sell'] is False
    assert state['buttons']['cancel_pending'] is False
    assert state['buttons']['stop'] is True
    assert state['severity'] == 'ready'
    assert 'Force BUY' in state['hint']


def test_operator_controls_pending_locks_force_actions_and_allows_cancel() -> None:
    state = build_operator_control_state(_status(state='BUY_PENDING', pending=True), connected=True)

    assert state['buttons']['force_buy'] is False
    assert state['buttons']['force_sell'] is False
    assert state['buttons']['cancel_pending'] is True
    assert 'PENDING_ORDER_ACTIVE' in state['reason_codes']
    assert state['severity'] == 'busy'


def test_operator_controls_safe_mode_allows_protective_exit() -> None:
    state = build_operator_control_state(
        _status(state='SAFE_MODE', position=True, safe_mode=True),
        connected=True,
    )

    assert state['buttons']['force_buy'] is False
    assert state['buttons']['force_sell'] is True
    assert state['safe_mode'] is True
    assert state['severity'] == 'safe'


def test_operator_controls_stale_contract_blocks_force_actions() -> None:
    state = build_operator_control_state(_status(contract_version='4B.4.3.6.6.4'), connected=True)

    assert state['buttons']['force_buy'] is False
    assert state['buttons']['force_sell'] is False
    assert state['contract_ok'] is False
    assert 'STATUS_CONTRACT_STALE' in state['reason_codes']


def test_operator_controls_health_anomaly_blocks_force_actions() -> None:
    state = build_operator_control_state(
        _status(account_consistency='BROKEN', anomaly='ACCOUNT_POSITION_DRIFT'),
        connected=True,
    )

    assert state['buttons']['force_buy'] is False
    assert state['health_ok'] is False
    assert 'HEALTH_ANOMALY:ACCOUNT_POSITION_DRIFT' in state['reason_codes']
    assert 'ACCOUNT_CONSISTENCY_BROKEN' in state['reason_codes']


class _Button:
    def __init__(self) -> None:
        self.kwargs = {}

    def configure(self, **kwargs) -> None:
        self.kwargs.update(kwargs)


class _Label(_Button):
    pass


class _App:
    def __init__(self) -> None:
        self._last_connected = True
        self._last_status = _status(state='BUY_PENDING', pending=True)
        self.api_base = 'http://127.0.0.1:8000'
        self.messages: list[str] = []
        self.btn_start = _Button()
        self.btn_stop = _Button()
        self.btn_force_buy = _Button()
        self.btn_force_sell = _Button()
        self.btn_cancel_pending = _Button()
        self.btn_balance_sync = _Button()
        self.btn_risk_reset = _Button()
        self.btn_safe_mode_toggle = _Button()
        self.controls_hint = _Label()

    def _append_backend(self, text: str) -> None:
        self.messages.append(text)


def test_apply_health_aware_controls_sets_button_states_and_hint() -> None:
    app = _App()

    DashboardApp._apply_health_aware_controls(app, app._last_status)  # type: ignore[arg-type]

    assert app.btn_force_buy.kwargs['state'] == 'disabled'
    assert app.btn_force_sell.kwargs['state'] == 'disabled'
    assert app.btn_cancel_pending.kwargs['state'] == 'normal'
    assert app.btn_stop.kwargs['state'] == 'normal'
    assert 'PENDING' in app.controls_hint.kwargs['text']


def test_api_post_blocks_disabled_operator_action_without_http(monkeypatch) -> None:
    app = _App()
    called = {'value': False}

    def fake_post(*args, **kwargs):
        called['value'] = True
        raise AssertionError('HTTP should not be called for a UI-blocked force action')

    import tradebot.ui.dashboard as dashboard_module
    monkeypatch.setattr(dashboard_module.requests, 'post', fake_post)

    DashboardApp.api_post(app, '/force-buy')  # type: ignore[arg-type]

    assert called['value'] is False
    assert app.messages
    assert app.messages[-1].startswith('Operator action blocked:')
