from __future__ import annotations

import sys
from dataclasses import dataclass
from types import ModuleType, SimpleNamespace

import pytest

# customtkinter stub for dashboard import
class _DummyWidget:
    def __init__(self, *args, value: str = '', **kwargs) -> None:
        self._value = value
        self.kwargs = dict(kwargs)

    def grid(self, *args, **kwargs):
        self.kwargs.update(kwargs)

    def grid_columnconfigure(self, *args, **kwargs):
        return None

    def grid_rowconfigure(self, *args, **kwargs):
        return None

    def configure(self, **kwargs):
        self.kwargs.update(kwargs)

    def insert(self, index, value):
        self._value = str(value)

    def delete(self, start, end=None):
        self._value = ''

    def set(self, value):
        self._value = str(value)

    def select(self):
        self._value = 1

    def deselect(self):
        self._value = 0

    def see(self, *args, **kwargs):
        return None

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

from tradebot.engine import TradeBotEngine
from tradebot.models import Balance, Candle, Position, RiskPlan, RuntimeState, SymbolRules
from tradebot.ui.dashboard import DashboardApp


@dataclass
class DummySettings:
    symbol: str = 'ETHUSDT'
    execution_mode: str = 'live_demo'
    order_notional_usd: float = 25.0
    min_notional_buffer_multiplier: float = 1.10
    force_entry_price_mode: str = 'passive'
    force_exit_price_mode: str = 'aggressive'
    sizing_mode: str = 'fixed_quote'
    auto_trade_cooldown_sec: int = 5
    max_daily_trades: int = 0
    max_consecutive_losses: int = 3
    max_daily_loss_pct: float = 2.0
    safe_mode_cooldown_min: int = 60
    atr_period: int = 14
    risk_reward_ratio: float = 2.0
    atr_multiplier: float = 1.5
    fixed_stop_loss_pct: float = 1.0
    fixed_take_profit_pct: float = 2.0
    tp_mode: str = 'rr'
    sl_mode: str = 'atr'
    break_even_enabled: bool = True
    break_even_trigger_r: float = 1.0
    break_even_buffer_pct: float = 0.02
    trailing_stop_enabled: bool = True
    trailing_atr_multiplier: float = 1.0
    trailing_only_after_break_even: bool = True
    partial_take_profit_enabled: bool = True
    partial_take_profit_rr: float = 1.0
    partial_take_profit_close_pct: float = 50.0
    order_timeout_sec: int = 20
    auto_trade_on_signal: bool = True
    auto_trade_signal_mode: str = 'normal'
    ai_provider_enabled: bool = True
    ai_provider_mode: str = 'local_xgboost'
    ai_model_path: str = 'models/ETHUSDT_model.ubj'
    ai_confidence_threshold: float = 0.60
    kline_interval: str = '1m'


class DummyLogger:
    def __init__(self) -> None:
        self.info_calls = []
        self.warn_calls = []
        self.error_calls = []

    def info(self, code: str, message: str, data: dict, *, dedupe_ms: int | None = None) -> None:
        self.info_calls.append((code, message, data))

    def warn(self, code: str, message: str, data: dict, *, dedupe_ms: int | None = None) -> None:
        self.warn_calls.append((code, message, data))

    def error(self, code: str, message: str, data: dict, *, dedupe_ms: int | None = None) -> None:
        self.error_calls.append((code, message, data))


def make_engine(*, state: str = 'FLAT', position: Position | None = None) -> TradeBotEngine:
    engine = object.__new__(TradeBotEngine)
    engine.settings = DummySettings()
    engine.logger = DummyLogger()
    engine.exchange = SimpleNamespace()
    engine.runtime = RuntimeState(state=state, ws_status='CONNECTED', symbol='ETHUSDT')
    engine.runtime.session.day_key = '2026-04-21'
    engine.runtime.balances = {
        'USDT': Balance(free=5000.0, locked=0.0, dust=0.0),
        'ETH': Balance(free=0.0, locked=0.0, dust=0.0),
    }
    engine.runtime.position = position
    engine.runtime.pending = None
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
    candle = Candle(open_time=1, close_time=2, open=2310.0, high=2316.0, low=2308.0, close=2315.5, volume=1.0, quote_volume=2315.5)
    engine._closed_candles = [candle] * 20
    engine._latest_book = {'bestBid': 2315.49, 'bestAsk': 2315.59}
    engine._partial_fill_fingerprints = {}
    engine._fill_reconcile_fingerprints = {}
    engine._recent_signal_fps = {}
    engine._submit_lock = None
    engine._exit_submit_lock = None
    engine._running = True
    engine.ai_provider = SimpleNamespace(available=True, load_error=None)
    engine._save_runtime = lambda: None
    return engine


@pytest.mark.asyncio
async def test_status_includes_health_risk_ai_pending_position_snapshots() -> None:
    position = Position(qty=0.0107, entry_price=2320.0, source='manual_force_buy')
    engine = make_engine(state='IN_POSITION', position=position)
    engine.runtime.last_signal = 'BUY'
    engine.runtime.signal_reason = 'AI Kararı | Güven Skoru: %61.2'
    engine.runtime.trend = 'UP'
    engine.runtime.last_signal_provider = 'local_xgboost'
    engine.runtime.last_signal_confidence = 0.612
    engine.runtime.last_signal_metrics = {'class_probs': {'BUY': 0.612, 'HOLD': 0.3, 'SELL': 0.088}}
    engine.runtime.last_evaluated_close_time = 1776761819999
    engine.runtime.last_signal_key = 'ETHUSDT|1m|BUY|1776761819999|abcd12'
    engine.runtime.safe_mode = True
    engine.runtime.safe_mode_source = 'consecutive_losses'
    engine.runtime.safe_mode_reason_code = 'MAX_CONSECUTIVE_LOSSES_REACHED'
    engine.runtime.safe_mode_until = 9999999999999
    engine.runtime.session.daily_realized_pnl = -0.25
    engine.runtime.session.daily_trade_count = 4
    engine.runtime.session.consecutive_losses = 2
    engine.runtime.session.last_closed_pnl = -0.05
    engine.runtime.balances['ETH'] = Balance(free=0.0107, locked=0.0, dust=0.0001)

    status = await TradeBotEngine.get_status(engine)

    assert 'health_snapshot' in status
    assert 'risk_snapshot' in status
    assert 'ai_snapshot' in status
    assert 'pending_snapshot' in status
    assert 'position_snapshot' in status
    assert status['health_snapshot']['has_position'] is True
    assert status['risk_snapshot']['safe_mode'] is True
    assert status['risk_snapshot']['safe_mode_source'] == 'consecutive_losses'
    assert status['ai_snapshot']['confidence'] == 0.612
    assert status['ai_snapshot']['provider'] == 'local_xgboost'
    assert status['position_snapshot']['present'] is True
    assert status['position_snapshot']['qty'] == pytest.approx(0.0107)
    assert status['pending_snapshot']['present'] is False


@pytest.mark.asyncio
async def test_status_serializes_position_risk_plan_without_status_crash() -> None:
    position = Position(
        qty=0.0107,
        entry_price=2320.0,
        source='manual_force_buy',
        risk_plan=RiskPlan(
            atr=1.25,
            entry_price=2320.0,
            stop_loss=2318.5,
            take_profit=2323.0,
            open_risk_quote=0.016,
            planned_rr=2.0,
        ),
    )
    engine = make_engine(state='IN_POSITION', position=position)

    status = await TradeBotEngine.get_status(engine)

    assert status['position_snapshot']['present'] is True
    assert status['position_snapshot']['risk_plan'] == {
        'atr': 1.25,
        'entry_price': 2320.0,
        'stop_loss': 2318.5,
        'take_profit': 2323.0,
        'open_risk_quote': 0.016,
        'planned_rr': 2.0,
        'break_even_trigger_price': None,
        'break_even_stop_price': None,
        'trailing_enabled': False,
        'partial_tp_price': None,
        'partial_tp_close_pct': None,
    }


class _Label:
    def __init__(self) -> None:
        self.kwargs = {}

    def configure(self, **kwargs):
        self.kwargs.update(kwargs)


class _Field:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value


class _DashboardProbe:
    def __init__(self) -> None:
        self.lbl_state = _Label()
        self.lbl_symbol = _Label()
        self.lbl_ws = _Label()
        self.status_box = 'status-box'
        self.event_box = 'event-box'
        self.risk_box = 'risk-box'
        self.position_box = 'position-box'
        self.ai_box = 'ai-box'
        self.pending_box = 'pending-box'
        self.log_box = 'log-box'
        self.event_count_label = _Label()
        self.controls_hint = _Label()
        self.btn_start = _Label()
        self.btn_stop = _Label()
        self.btn_force_buy = _Label()
        self.btn_force_sell = _Label()
        self.btn_cancel_pending = _Label()
        self.btn_balance_sync = _Label()
        self.btn_risk_reset = _Label()
        self.btn_safe_mode_toggle = _Label()
        self.captured = {}
        self._log_items = []
        self._event_filter_value = 'All'
        self._button_style_enabled = {
            'state': 'normal',
            'fg_color': ('#3B8ED0', '#1F6AA5'),
            'hover_color': ('#36719F', '#144870'),
            'text_color': ('#FFFFFF', '#FFFFFF'),
            'text_color_disabled': ('#FFFFFF', '#FFFFFF'),
            'hover': True,
        }
        self._button_style_disabled = {
            'state': 'disabled',
            'fg_color': ('#8C8C8C', '#5F5F5F'),
            'hover_color': ('#8C8C8C', '#5F5F5F'),
            'text_color': ('#E8E8E8', '#D8D8D8'),
            'text_color_disabled': ('#E8E8E8', '#D8D8D8'),
            'hover': False,
        }
        self.form = {
            'auto_trade_on_signal': _Field(True),
            'auto_trade_signal_mode': _Field('normal'),
            'ai_provider_enabled': _Field(True),
            'ai_model_path': _Field('models/ETHUSDT_model.ubj'),
            'order_notional_usd': _Field('25'),
            'execution_mode': _Field('live_demo'),
            'live_trading_armed': _Field(True),
        }

    def _set_text(self, widget, text: str) -> None:
        self.captured[widget] = text

    def _optional_set_text(self, widget_name: str, text: str) -> None:
        widget = getattr(self, widget_name, None)
        if widget is not None:
            self._set_text(widget, text)

    def _fmt_number(self, value, digits: int = 6) -> str:
        if isinstance(value, bool):
            return str(value)
        if isinstance(value, (int, float)):
            return f'{value:.{digits}f}'
        return '-' if value is None else str(value)

    def _fmt_health(self, value):
        raw = '-' if value is None else str(value)
        normalized = raw.upper()
        if normalized == 'HEALTHY':
            return 'OK'
        if normalized in {'WARNING', 'WARN'}:
            return 'WARN'
        if normalized in {'LOCKED', 'ERROR', 'BROKEN'}:
            return normalized
        return raw

    def _fmt_time(self, value):
        if value in (None, '', '-'):
            return '-'
        return str(value)

    def _fmt_duration(self, value):
        if value in (None, '', '-'):
            return '-'
        return str(value)

    def _state_color(self, state):
        return ('white', 'white')

    def _ws_color(self, ws_status):
        return ('white', 'white')

    def _format_log_ts(self, value):
        return DashboardApp._format_log_ts(self, value)

    def _event_brief(self, item):
        return DashboardApp._event_brief(self, item)

    def _summary_trade_scope(self, status):
        return DashboardApp._summary_trade_scope(self, status)

    def _normalize_health_state(self, value):
        return DashboardApp._normalize_health_state(self, value)

    def _set_button_enabled(self, button, enabled: bool):
        return DashboardApp._set_button_enabled(self, button, enabled)



def test_dashboard_render_uses_snapshot_payloads() -> None:
    app = _DashboardProbe()
    status = {
        'state': 'IN_POSITION',
        'symbol': 'ETHUSDT',
        'ws_status': 'CONNECTED',
        'last_signal': 'BUY',
        'signal_reason': 'AI Kararı | Güven Skoru: %61.2',
        'trend': 'UP',
        'auto_debug': '-',
        'auto_guard': 'cooldown 5s',
        'last_preflight': 'LIVE_PREFLIGHT_OK',
        'last_order_event': 'BUY filled @ 2320.00',
        'balances': {'ETH': {'free': 0.0107, 'dust': 0.0001}, 'USDT': {'free': 4975.0}},
        'dust_snapshot': {'ETH': 0.0001},
        'health_snapshot': {
            'account_consistency': 'HEALTHY',
            'position_consistency': 'HEALTHY',
            'pending_consistency': 'HEALTHY',
            'active_anomaly_code': None,
            'last_reconcile_result': 'STATUS_POLL',
        },
        'risk_snapshot': {
            'daily_realized_pnl': 0.123,
            'daily_trade_count': 2,
            'consecutive_losses': 0,
            'safe_mode': False,
            'safe_mode_source': None,
            'safe_mode_reason_code': None,
            'safe_mode_remaining_sec': None,
            'kill_switch_active': False,
        },
        'ai_snapshot': {
            'enabled': True,
            'model_path': 'models/ETHUSDT_model.ubj',
            'provider': 'local_xgboost',
            'confidence': 0.612,
            'trend': 'UP',
        },
        'position_snapshot': {
            'present': True,
            'qty': 0.0107,
            'entry_price': 2320.0,
            'unrealized_pnl': 0.045,
        },
        'pending_snapshot': {
            'present': False,
            'side': None,
            'submitted_qty': 0.0,
            'executed_qty': 0.0,
            'remaining_qty': 0.0,
            'status': None,
        },
        'session': {'daily_realized_pnl': 0.123, 'daily_trade_count': 2, 'consecutive_losses': 0},
    }

    DashboardApp._render_status(app, status)  # type: ignore[arg-type]

    assert 'Account         : OK' in app.captured['status-box']
    assert 'Daily PnL       : 0.123000' in app.captured['risk-box']
    assert 'Unrealized PnL  : 0.045000' in app.captured['position-box']
    assert 'Confidence      : %61.2' in app.captured['ai-box']
    assert 'Pending order   : NO' in app.captured['pending-box']
    assert 'Health          : OK/OK/OK' in app.captured['log-box']
    assert 'Model           : models/ETHUSDT_model.ubj' in app.captured['log-box']




def test_dashboard_health_aware_controls_disable_and_hint_buttons() -> None:
    app = _DashboardProbe()
    app._last_connected = True
    status = {
        'state': 'FLAT',
        'health_snapshot': {
            'account_consistency': 'HEALTHY',
            'position_consistency': 'HEALTHY',
            'pending_consistency': 'HEALTHY',
            'active_anomaly_code': None,
        },
        'risk_snapshot': {'safe_mode': True, 'safe_mode_reason_code': 'MAX_CONSECUTIVE_LOSSES_REACHED'},
        'pending_snapshot': {'present': False},
        'position_snapshot': {'present': False},
    }

    DashboardApp._apply_health_aware_controls(app, status)  # type: ignore[arg-type]

    assert app.btn_force_buy.kwargs.get('state') == 'disabled'
    assert app.btn_force_buy.kwargs.get('fg_color') == ('#8C8C8C', '#5F5F5F')
    assert app.btn_force_sell.kwargs.get('state') == 'disabled'
    assert app.btn_cancel_pending.kwargs.get('state') == 'disabled'
    assert 'safe mode' in app.controls_hint.kwargs.get('text', '').lower()


def test_dashboard_health_aware_controls_enable_exit_and_cancel_when_needed() -> None:
    app = _DashboardProbe()
    app._last_connected = True
    status = {
        'state': 'IN_POSITION',
        'health_snapshot': {
            'account_consistency': 'HEALTHY',
            'position_consistency': 'HEALTHY',
            'pending_consistency': 'HEALTHY',
            'active_anomaly_code': None,
        },
        'risk_snapshot': {'safe_mode': False},
        'pending_snapshot': {'present': False},
        'position_snapshot': {'present': True},
    }

    DashboardApp._apply_health_aware_controls(app, status)  # type: ignore[arg-type]

    assert app.btn_force_buy.kwargs.get('state') == 'disabled'
    assert app.btn_force_buy.kwargs.get('fg_color') == ('#8C8C8C', '#5F5F5F')
    assert app.btn_force_sell.kwargs.get('state') == 'normal'
    assert app.btn_force_sell.kwargs.get('fg_color') == ('#3B8ED0', '#1F6AA5')
    assert 'force sell aktif' in app.controls_hint.kwargs.get('text', '').lower()

    status['pending_snapshot'] = {'present': True}
    DashboardApp._apply_health_aware_controls(app, status)  # type: ignore[arg-type]
    assert app.btn_cancel_pending.kwargs.get('state') == 'normal'
    assert app.btn_cancel_pending.kwargs.get('fg_color') == ('#3B8ED0', '#1F6AA5')
    assert 'pending emir var' in app.controls_hint.kwargs.get('text', '').lower()


def test_dashboard_event_timeline_filtering_and_session_summary() -> None:
    app = _DashboardProbe()
    app._log_items = [
        {'ts': 1776767519999, 'level': 'INFO', 'code': 'ORDER_SUBMITTED', 'message': 'Giriş emri oluşturuldu', 'data': {'side': 'BUY', 'qty': 0.0107, 'price': 2329.02}, 'category': 'Orders'},
        {'ts': 1776767579999, 'level': 'INFO', 'code': 'POSITION_CLOSED', 'message': 'Pozisyon kapandı', 'data': {'symbol': 'ETHUSDT', 'pnl': -0.004922}, 'category': 'Orders'},
        {'ts': 1776767639999, 'level': 'WARN', 'code': 'SAFE_MODE_AUTO_ENABLED', 'message': 'Safe mode etkin', 'data': {'reason': 'test'}, 'category': 'Warnings'},
        {'ts': 1776767699999, 'level': 'INFO', 'code': 'STRATEGY_EVAL', 'message': 'Strateji değerlendirildi', 'data': {'signal': 'HOLD', 'trend': 'DOWN'}, 'category': 'AI'},
    ]
    app._event_filter_value = 'Warnings'

    DashboardApp._render_event_timeline(app)  # type: ignore[arg-type]
    DashboardApp._render_session_summary(app, {
        'last_signal': 'HOLD',
        'signal_reason': 'AI Kararı | Güven Skoru: %45.4',
        'trend': 'DOWN',
        'auto_debug': 'NO_ACTION_SIGNAL_HOLD',
        'auto_guard': '-',
        'last_preflight': 'OK | ENTRY',
        'last_order_event': 'SELL filled',
        'health_snapshot': {'account_consistency': 'HEALTHY', 'position_consistency': 'HEALTHY', 'pending_consistency': 'HEALTHY'},
        'ai_snapshot': {'enabled': True, 'model_path': 'models/ETHUSDT_model.ubj', 'confidence': 0.454},
        'risk_snapshot': {'daily_realized_pnl': -0.004922, 'daily_trade_count': 2},
        'session': {'daily_realized_pnl': -0.004922, 'daily_trade_count': 2},
    })  # type: ignore[arg-type]

    assert 'SAFE_MODE_AUTO_ENABLED' in app.captured['event-box']
    assert 'Warnings: 1 event' == app.event_count_label.kwargs.get('text')
    assert 'Tracked W/L/BE  : 0/1/0' in app.captured['log-box']
    assert 'Last warning    : SAFE_MODE_AUTO_ENABLED' in app.captured['log-box']
    assert 'Tracked trades  : ETHUSDT -0.004922' in app.captured['log-box']
    assert 'Scope note      : partial log scope (1/2)' in app.captured['log-box']


def test_dashboard_session_summary_scopes_today_counts_after_manual_reset() -> None:
    app = _DashboardProbe()
    app._log_items = [
        {'ts': 1, 'level': 'INFO', 'code': 'POSITION_CLOSED', 'message': 'Pozisyon kapandı', 'data': {'symbol': 'ETHUSDT', 'pnl': 0.023754}, 'category': 'Orders'},
        {'ts': 2, 'level': 'INFO', 'code': 'POSITION_CLOSED', 'message': 'Pozisyon kapandı', 'data': {'symbol': 'ETHUSDT', 'pnl': -0.004922}, 'category': 'Orders'},
        {'ts': 3, 'level': 'INFO', 'code': 'RISK_STATS_RESET', 'message': 'Risk sıfırlandı', 'data': {'reason': 'MANUAL_RESET'}, 'category': 'Risk'},
        {'ts': 4, 'level': 'INFO', 'code': 'POSITION_CLOSED', 'message': 'Pozisyon kapandı', 'data': {'symbol': 'ETHUSDT', 'pnl': -0.012852}, 'category': 'Orders'},
    ]

    DashboardApp._render_session_summary(app, {
        'last_signal': 'HOLD',
        'signal_reason': 'AI Kararı | Güven Skoru: %35.1',
        'trend': 'DOWN',
        'auto_debug': 'NO_ACTION_SIGNAL_HOLD',
        'auto_guard': '-',
        'last_preflight': 'OK | EXIT',
        'last_order_event': 'SELL filled @ 2307.25',
        'health_snapshot': {'account_consistency': 'HEALTHY', 'position_consistency': 'HEALTHY', 'pending_consistency': 'HEALTHY'},
        'ai_snapshot': {'enabled': True, 'model_path': 'models/ETHUSDT_model.ubj', 'confidence': 0.351},
        'risk_snapshot': {'daily_realized_pnl': -0.012852, 'daily_trade_count': 1},
        'session': {'daily_realized_pnl': -0.012852, 'daily_trade_count': 1},
    })  # type: ignore[arg-type]

    assert 'Trades today    : 1' in app.captured['log-box']
    assert 'Today W/L/BE    : 0/1/0' in app.captured['log-box']
    assert 'Today trades    : ETHUSDT -0.012852' in app.captured['log-box']
    assert 'Recent hist.    : ETHUSDT 0.023754 / ETHUSDT -0.004922 / ETHUSDT -0.012852' in app.captured['log-box']
    assert 'Scope note      : -' in app.captured['log-box']


def test_dashboard_session_summary_marks_partial_scope_when_engine_totals_exceed_local_log() -> None:
    app = _DashboardProbe()
    app._log_items = [
        {'ts': 10, 'level': 'INFO', 'code': 'POSITION_CLOSED', 'message': 'Pozisyon kapandı', 'data': {'symbol': 'ETHUSDT', 'pnl': -0.012204}, 'category': 'Orders'},
        {'ts': 11, 'level': 'INFO', 'code': 'POSITION_CLOSED', 'message': 'Pozisyon kapandı', 'data': {'symbol': 'ETHUSDT', 'pnl': 0.014148}, 'category': 'Orders'},
    ]

    DashboardApp._render_session_summary(app, {
        'last_signal': 'HOLD',
        'signal_reason': 'AI Kararı | Güven Skoru: %35.9',
        'trend': 'UP',
        'auto_debug': 'NO_ACTION_SIGNAL_HOLD',
        'auto_guard': '-',
        'last_preflight': 'OK | EXIT',
        'last_order_event': 'SELL filled @ 2312.47',
        'health_snapshot': {'account_consistency': 'HEALTHY', 'position_consistency': 'HEALTHY', 'pending_consistency': 'HEALTHY'},
        'ai_snapshot': {'enabled': True, 'model_path': 'models/ETHUSDT_model.ubj', 'confidence': 0.359},
        'risk_snapshot': {'daily_realized_pnl': -0.025164, 'daily_trade_count': 5},
        'session': {'daily_realized_pnl': -0.025164, 'daily_trade_count': 5},
    })  # type: ignore[arg-type]

    assert 'Trades today    : 5' in app.captured['log-box']
    assert 'Tracked PnL     : 0.001944' in app.captured['log-box']
    assert 'Tracked W/L/BE  : 1/1/0' in app.captured['log-box']
    assert 'Tracked trades  : ETHUSDT -0.012204 / ETHUSDT 0.014148' in app.captured['log-box']
    assert 'Scope note      : partial log scope (2/5)' in app.captured['log-box']


def test_dashboard_health_aware_controls_pending_state_hints_are_specific() -> None:
    app = _DashboardProbe()
    app._last_connected = True

    buy_pending_status = {
        'state': 'BUY_PENDING',
        'health_snapshot': {
            'account_consistency': 'HEALTHY',
            'position_consistency': 'HEALTHY',
            'pending_consistency': 'HEALTHY',
            'active_anomaly_code': None,
        },
        'risk_snapshot': {'safe_mode': False},
        'pending_snapshot': {'present': True},
        'position_snapshot': {'present': False},
    }
    DashboardApp._apply_health_aware_controls(app, buy_pending_status)  # type: ignore[arg-type]
    assert 'giriş emri bekliyor' in app.controls_hint.kwargs.get('text', '').lower()
    assert app.btn_force_buy.kwargs.get('state') == 'disabled'
    assert app.btn_force_sell.kwargs.get('state') == 'disabled'
    assert app.btn_cancel_pending.kwargs.get('state') == 'normal'

    sell_pending_status = {
        'state': 'SELL_PENDING',
        'health_snapshot': {
            'account_consistency': 'HEALTHY',
            'position_consistency': 'HEALTHY',
            'pending_consistency': 'HEALTHY',
            'active_anomaly_code': None,
        },
        'risk_snapshot': {'safe_mode': False},
        'pending_snapshot': {'present': True},
        'position_snapshot': {'present': True},
    }
    DashboardApp._apply_health_aware_controls(app, sell_pending_status)  # type: ignore[arg-type]
    assert 'çıkış emri bekliyor' in app.controls_hint.kwargs.get('text', '').lower()
    assert app.btn_force_buy.kwargs.get('state') == 'disabled'
    assert app.btn_force_sell.kwargs.get('state') == 'disabled'
    assert app.btn_cancel_pending.kwargs.get('state') == 'normal'
