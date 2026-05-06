from __future__ import annotations

import sys
from dataclasses import dataclass
from types import ModuleType, SimpleNamespace

# customtkinter stub for dashboard import
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
    def title(self, *args, **kwargs): return None
    def geometry(self, *args, **kwargs): return None
    def minsize(self, *args, **kwargs): return None
    def protocol(self, *args, **kwargs): return None
    def after(self, *args, **kwargs): return None
    def destroy(self): return None
    def mainloop(self): return None


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

from tradebot.engine import TradeBotEngine
from tradebot.models import Balance, Candle, Position, RiskPlan, RuntimeState, SymbolRules
from tradebot.ui.dashboard import DashboardApp, build_operator_control_state, build_position_management_text


@dataclass
class DummySettings:
    symbol: str = 'ETHUSDT'
    execution_mode: str = 'live_demo'
    min_notional_buffer_multiplier: float = 1.10
    atr_period: int = 14
    risk_reward_ratio: float = 2.0
    atr_multiplier: float = 1.5
    fixed_stop_loss_pct: float = 1.0
    fixed_take_profit_pct: float = 2.0
    tp_mode: str = 'rr'
    sl_mode: str = 'atr'
    break_even_trigger_r: float = 1.0
    break_even_buffer_pct: float = 0.02
    trailing_stop_enabled: bool = True
    partial_take_profit_rr: float = 1.0
    partial_take_profit_close_pct: float = 50.0
    ai_provider_enabled: bool = True
    ai_provider_mode: str = 'local_xgboost'
    ai_model_path: str = 'models/ETHUSDT_model_4b43664.ubj'
    ai_confidence_threshold: float = 0.6


class DummyLogger:
    def __init__(self) -> None:
        self.info_calls = []
        self.warn_calls = []

    def info(self, code: str, message: str, data: dict, **kwargs) -> None:
        self.info_calls.append((code, message, data))

    def warn(self, code: str, message: str, data: dict, **kwargs) -> None:
        self.warn_calls.append((code, message, data))


def make_engine(position: Position | None, *, base_free: float = 0.012) -> TradeBotEngine:
    engine = object.__new__(TradeBotEngine)
    engine.settings = DummySettings()
    engine.logger = DummyLogger()
    engine.exchange = SimpleNamespace()
    engine.runtime = RuntimeState(state='IN_POSITION' if position else 'FLAT', ws_status='CONNECTED', symbol='ETHUSDT')
    engine.runtime.position = position
    engine.runtime.balances = {
        'ETH': Balance(free=base_free, locked=0.0, dust=0.0),
        'USDT': Balance(free=5000.0, locked=0.0, dust=0.0),
    }
    engine.symbol_rules = SymbolRules(
        symbol='ETHUSDT',
        base_asset='ETH',
        quote_asset='USDT',
        tick_size=0.01,
        step_size=0.0001,
        min_qty=0.0001,
        max_qty=100000.0,
        min_notional=5.0,
    )
    candle = Candle(open_time=1, close_time=2, open=2290.0, high=2320.0, low=2280.0, close=2315.0, volume=1.0, quote_volume=2315.0)
    engine._closed_candles = [candle] * 20
    engine._latest_book = {'bestBid': 2315.0, 'bestAsk': 2315.1}
    engine._running = True
    engine.ai_provider = SimpleNamespace(available=True, load_error=None)
    engine.store = SimpleNamespace(fetch_logs=lambda *args, **kwargs: [])
    engine._save_runtime = lambda: None
    return engine


def base_status(position_snapshot: dict) -> dict:
    return {
        'state': 'IN_POSITION' if position_snapshot.get('present') else 'FLAT',
        'engine_running': True,
        'contract_version': '4B.4.3.6.6.10',
        'health_snapshot': {
            'engine_running': True,
            'ws_connected': True,
            'has_pending': False,
            'has_position': bool(position_snapshot.get('present')),
            'account_consistency': 'HEALTHY',
            'position_consistency': 'HEALTHY',
            'pending_consistency': 'HEALTHY',
        },
        'risk_snapshot': {'safe_mode': False, 'kill_switch_active': False},
        'pending_snapshot': {'present': False},
        'position_snapshot': position_snapshot,
        'ai_snapshot': {'available': True, 'schema_validated': True},
    }


def test_position_snapshot_includes_risk_plan_and_protective_exit_ready() -> None:
    position = Position(qty=0.0112, entry_price=2300.0, source='manual_force_buy')
    engine = make_engine(position, base_free=0.0112)

    snapshot = engine._position_snapshot(engine.runtime.to_dict())

    assert snapshot['present'] is True
    assert snapshot['risk_plan'] is not None
    assert snapshot['protective_exit']['protective_exit_ready'] is True
    assert snapshot['protective_exit']['tradable_exit_qty'] == 0.0112
    assert snapshot['protective_exit']['exit_notional'] > 5.5
    assert any(call[0] == 'RISK_PLAN_READY' for call in engine.logger.info_calls)


def test_position_snapshot_marks_dust_position_and_blocks_protective_exit() -> None:
    position = Position(qty=0.0001, entry_price=2300.0, source='dust_rehydrate')
    engine = make_engine(position, base_free=0.0001)

    snapshot = engine._position_snapshot(engine.runtime.to_dict())
    protective = snapshot['protective_exit']

    assert protective['is_dust'] is True
    assert protective['protective_exit_ready'] is False
    assert protective['block_reason'] == 'MIN_NOTIONAL_BLOCKED'


def test_operator_controls_disable_force_sell_when_protective_exit_blocked() -> None:
    position_snapshot = {
        'present': True,
        'qty': 0.0001,
        'protective_exit': {
            'present': True,
            'protective_exit_ready': False,
            'block_reason': 'MIN_NOTIONAL_BLOCKED',
            'is_dust': True,
        },
    }

    state = build_operator_control_state(base_status(position_snapshot), connected=True)

    assert state['buttons']['force_sell'] is False
    assert state['protective_exit_ready'] is False
    assert state['position_is_dust'] is True
    assert 'PROTECTIVE_EXIT_BLOCKED:MIN_NOTIONAL_BLOCKED' in state['reason_codes']
    assert 'POSITION_DUST' in state['warnings']


def test_operator_controls_allow_force_sell_for_real_position() -> None:
    position_snapshot = {
        'present': True,
        'qty': 0.0112,
        'protective_exit': {
            'present': True,
            'protective_exit_ready': True,
            'block_reason': None,
            'is_dust': False,
        },
    }

    state = build_operator_control_state(base_status(position_snapshot), connected=True)

    assert state['buttons']['force_buy'] is False
    assert state['buttons']['force_sell'] is True
    assert state['severity'] == 'position'


def test_position_management_text_surfaces_risk_and_exit_levels() -> None:
    rp = RiskPlan(
        atr=10.0,
        entry_price=2300.0,
        stop_loss=2285.0,
        take_profit=2330.0,
        open_risk_quote=0.168,
        planned_rr=2.0,
        break_even_trigger_price=2315.0,
        break_even_stop_price=2300.46,
        trailing_enabled=True,
        partial_tp_price=2315.0,
        partial_tp_close_pct=50.0,
    )
    position = Position(qty=0.0112, entry_price=2300.0, source='manual_force_buy', risk_plan=rp)
    engine = make_engine(position, base_free=0.0112)
    snapshot = engine._position_snapshot(engine.runtime.to_dict())

    text = build_position_management_text(base_status(snapshot))

    assert 'Position status : IN_POSITION' in text
    assert 'Protective exit : READY' in text
    assert 'Risk plan       : READY' in text
    assert 'Stop loss' in text
    assert 'Take profit' in text


class _App(DashboardApp):
    pass


def test_dashboard_render_status_contains_position_management_section() -> None:
    app = _App.__new__(_App)
    app.lbl_state = _DummyWidget()
    app.lbl_symbol = _DummyWidget()
    app.lbl_ws = _DummyWidget()
    app.status_box = _DummyWidget()
    app.log_box = _DummyWidget()
    app.form = {'symbol': 'ETHUSDT'}

    position_snapshot = {
        'present': True,
        'qty': 0.0112,
        'entry_price': 2300.0,
        'mark_price': 2315.0,
        'unrealized_pnl': 0.168,
        'unrealized_pnl_pct': 0.65217,
        'source': 'manual_force_buy',
        'risk_plan': {'stop_loss': 2285.0, 'take_profit': 2330.0},
        'protective_exit': {
            'present': True,
            'protective_exit_ready': True,
            'tradable_exit_qty': 0.0112,
            'exit_notional': 25.928,
            'is_dust': False,
            'stop_loss': 2285.0,
            'take_profit': 2330.0,
            'distance_to_stop': 30.0,
            'distance_to_stop_pct': 1.2959,
            'distance_to_take_profit': 15.0,
            'distance_to_take_profit_pct': 0.6479,
        },
    }
    status = base_status(position_snapshot)
    status.update({
        'symbol': 'ETHUSDT',
        'ws_status': 'CONNECTED',
        'last_signal': 'HOLD',
        'signal_reason': 'test',
        'trend': 'UP',
        'balances': {'ETH': {'free': 0.0112}, 'USDT': {'free': 5000.0}},
        'session': {},
    })

    DashboardApp._render_status(app, status)

    assert 'Protective exit : READY' in app.status_box.text
    assert 'Risk plan       : READY' in app.status_box.text
    assert 'Unrealized PnL' in app.status_box.text
