from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

from tradebot.engine import TradeBotEngine
from tradebot.models import PendingOrder, RuntimeState
from tradebot.order_reconciliation import ORDER_RECONCILIATION_CONTRACT_VERSION, build_reconciliation_snapshot


@dataclass(slots=True)
class DummySettings:
    symbol: str = 'ETHUSDT'
    order_timeout_sec: int = 20
    reconciliation_base_backoff_ms: int = 1000
    reconciliation_max_backoff_ms: int = 15000
    reconciliation_missing_warning_count: int = 2
    reconciliation_missing_critical_count: int = 3
    reconciliation_max_attempts_before_deferred: int = 8
    reconciliation_late_fill_grace_ms: int = 30000


def make_pending(**kwargs) -> PendingOrder:
    data = dict(side='BUY', price=2300.0, qty=0.01, status='NEW', order_id='123', client_order_id='cid-123', submitted_at=1_000, source='AUTO_SIGNAL')
    data.update(kwargs)
    return PendingOrder(**data)


def test_reconciliation_snapshot_reports_idle_without_pending() -> None:
    snap = build_reconciliation_snapshot(pending=None, now=5_000, symbol='ETHUSDT', settings=DummySettings())

    assert snap['contract_version'] == ORDER_RECONCILIATION_CONTRACT_VERSION
    assert snap['pending_present'] is False
    assert snap['state'] == 'IDLE'
    assert snap['recommended_action'] == 'NONE'


def test_reconciliation_snapshot_classifies_partial_fill() -> None:
    pending = make_pending(reconcile_attempts=2)
    order = {'status': 'PARTIALLY_FILLED', 'executedQty': '0.004', 'origQty': '0.010', 'orderId': '123'}

    snap = build_reconciliation_snapshot(pending=pending, now=3_000, symbol='ETHUSDT', settings=DummySettings(), order=order)

    assert snap['state'] == 'PARTIAL_FILL'
    assert snap['recommended_action'] == 'POLL_AGAIN'
    assert snap['partial_fill'] is True
    assert snap['live_executed_qty'] == 0.004
    assert snap['live_remaining_qty'] == 0.006


def test_reconciliation_snapshot_classifies_missing_orphan() -> None:
    pending = make_pending(missing_count=3, reconcile_attempts=4)

    snap = build_reconciliation_snapshot(pending=pending, now=30_000, symbol='ETHUSDT', settings=DummySettings(), order=None, open_orders=[])

    assert snap['state'] == 'ORPHAN_MISSING'
    assert snap['severity'] == 'critical'
    assert snap['recommended_action'] == 'CLEAR_PENDING'
    assert 'LIVE_ORDER_MISSING_CRITICAL' in snap['reason_codes']


def test_reconciliation_snapshot_classifies_deferred_cancel_request() -> None:
    pending = make_pending(reconcile_attempts=8)
    open_orders = [{'orderId': '123', 'clientOrderId': 'cid-123', 'status': 'NEW'}]

    snap = build_reconciliation_snapshot(pending=pending, now=30_000, symbol='ETHUSDT', settings=DummySettings(), order=None, open_orders=open_orders)

    assert snap['state'] == 'DEFER_CANDIDATE'
    assert snap['recommended_action'] == 'REQUEST_CANCEL'
    assert 'MAX_RECONCILE_ATTEMPTS_REACHED' in snap['reason_codes']


def test_engine_status_exposes_reconciliation_snapshot_without_pending() -> None:
    engine = object.__new__(TradeBotEngine)
    engine.settings = DummySettings()
    engine.runtime = RuntimeState()
    engine.runtime.pending = None

    snap = TradeBotEngine._reconciliation_snapshot(engine)

    assert snap['contract_version'] == ORDER_RECONCILIATION_CONTRACT_VERSION
    assert snap['pending_present'] is False
    assert snap['state'] == 'IDLE'


def test_engine_status_exposes_reconciliation_snapshot_with_pending() -> None:
    engine = object.__new__(TradeBotEngine)
    engine.settings = DummySettings()
    engine.runtime = RuntimeState()
    engine.runtime.pending = make_pending(reconcile_attempts=1)

    snap = TradeBotEngine._reconciliation_snapshot(engine)

    assert snap['pending_present'] is True
    assert snap['order_id'] == '123'
    assert snap['client_order_id'] == 'cid-123'
    assert snap['recommended_action'] in {'WAIT', 'POLL_AGAIN'}
    assert engine.runtime.reconciliation_snapshot['contract_version'] == ORDER_RECONCILIATION_CONTRACT_VERSION
