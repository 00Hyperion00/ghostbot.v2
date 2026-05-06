from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / 'src' / 'tradebot' / 'engine.py'
API = ROOT / 'src' / 'tradebot' / 'api.py'
DASHBOARD = ROOT / 'src' / 'tradebot' / 'ui' / 'dashboard.py'

VERSION_FROM = '4B.4.3.6.6.11'
VERSION_TO = '4B.4.3.6.6.12'

RECOVERY_METHODS = r'''
    @staticmethod
    def _order_value(row: dict[str, Any], *names: str, default: Any = None) -> Any:
        for name in names:
            if name in row and row.get(name) is not None:
                return row.get(name)
        return default

    @staticmethod
    def _to_float(value: Any, default: float = 0.0) -> float:
        try:
            if value is None or value == '':
                return default
            return float(value)
        except (TypeError, ValueError):
            return default

    def _pending_from_live_order(self, row: dict[str, Any]) -> PendingOrder:
        side = str(self._order_value(row, 'side', default='BUY')).upper()
        qty = self._to_float(self._order_value(row, 'origQty', 'quantity', 'qty', default=0.0))
        executed_qty = self._to_float(self._order_value(row, 'executedQty', 'executed_qty', default=0.0))
        remaining_qty = max(qty - executed_qty, 0.0)
        price = self._to_float(self._order_value(row, 'price', default=0.0))
        if price <= 0 and self._latest_mark_price() is not None:
            price = float(self._latest_mark_price() or 0.0)
        return PendingOrder(
            side=side,
            price=price,
            qty=qty,
            status=str(self._order_value(row, 'status', default='NEW')),
            order_id=str(self._order_value(row, 'orderId', 'order_id', default='')) or None,
            client_order_id=str(self._order_value(row, 'clientOrderId', 'client_order_id', 'newClientOrderId', default='')) or None,
            source='startup_live_open_order',
            submitted_at=int(self._order_value(row, 'time', 'transactTime', default=utc_ms()) or utc_ms()),
            partial_executed_qty=executed_qty,
            remaining_qty=remaining_qty,
            last_reconcile_at=utc_ms(),
        )

    def _recovery_state_for_current_runtime(self) -> str:
        if self.runtime.pending is not None:
            side = str(self.runtime.pending.side or '').upper()
            return BotState.BUY_PENDING.value if side == 'BUY' else BotState.SELL_PENDING.value
        if self.runtime.position is not None:
            return BotState.IN_POSITION.value
        return BotState.FLAT.value

    async def _fetch_recovery_open_orders(self) -> list[dict[str, Any]]:
        fetch_open_orders = getattr(self.exchange, 'fetch_open_orders', None)
        if not callable(fetch_open_orders):
            return []
        try:
            return list(await fetch_open_orders(self.settings.symbol))
        except TypeError:
            return list(await fetch_open_orders())

    async def _startup_reconcile_persistent_state(self) -> dict[str, Any]:
        """Reconcile persisted runtime state with live account data at startup.

        This method is deliberately conservative: live open orders and live base balance
        are treated as the source of truth. Local orphan pending/position state is cleared
        when it no longer has live support.
        """
        now = utc_ms()
        base_asset = self.symbol_rules.base_asset if self.symbol_rules else ''
        quote_asset = self.symbol_rules.quote_asset if self.symbol_rules else ''
        base_balance = self.runtime.balances.get(base_asset, Balance()) if base_asset else Balance()
        step = self.symbol_rules.step_size if self.symbol_rules else 1e-8
        min_qty = self.symbol_rules.min_qty if self.symbol_rules else 0.0
        min_notional = (self.symbol_rules.min_notional * self.settings.min_notional_buffer_multiplier) if self.symbol_rules else 0.0
        mark = self._latest_mark_price()
        tradable_base = round_down_to_step(max(float(base_balance.free or 0.0) - float(base_balance.dust or 0.0), 0.0), step)
        live_notional = tradable_base * float(mark or 0.0)
        live_position_supported = tradable_base >= min_qty and (min_notional <= 0 or live_notional >= min_notional)

        snapshot: dict[str, Any] = {
            'contract_version': '4B.4.3.6.6.12',
            'recovered_at': now,
            'symbol': self.settings.symbol,
            'base_asset': base_asset,
            'quote_asset': quote_asset,
            'live_free_base': base_balance.free,
            'base_dust': base_balance.dust,
            'tradable_base': tradable_base,
            'live_position_supported': live_position_supported,
            'open_order_count': 0,
            'pending_before': self.runtime.pending is not None,
            'position_before': self.runtime.position is not None,
            'pending_action': 'UNCHANGED',
            'position_action': 'UNCHANGED',
            'state_before': str(self.runtime.state),
            'state_after': None,
            'warnings': [],
        }

        open_orders: list[dict[str, Any]] = []
        try:
            open_orders = await self._fetch_recovery_open_orders()
        except Exception as exc:
            snapshot['open_order_fetch_error'] = str(exc)
            snapshot['warnings'].append('OPEN_ORDERS_FETCH_FAILED')
            if getattr(self, 'logger', None):
                self.logger.warn('RECOVERY_OPEN_ORDERS_FETCH_FAILED', 'Startup open order reconciliation atlandı', {'error': str(exc), 'symbol': self.settings.symbol})
        snapshot['open_order_count'] = len(open_orders)

        live_order = None
        for row in open_orders:
            status = str(self._order_value(row, 'status', default='')).upper()
            symbol = str(self._order_value(row, 'symbol', default=self.settings.symbol)).upper()
            if symbol == str(self.settings.symbol).upper() and status in {'NEW', 'PARTIALLY_FILLED'}:
                live_order = row
                break

        if live_order is not None:
            live_pending = self._pending_from_live_order(live_order)
            previous_pending = self.runtime.pending
            self.runtime.pending = live_pending
            snapshot['pending_action'] = 'RECOVERED_LIVE_OPEN_ORDER' if previous_pending is None else 'REFRESHED_FROM_LIVE_OPEN_ORDER'
            snapshot['pending_side'] = live_pending.side
            snapshot['pending_status'] = live_pending.status
            snapshot['pending_order_id'] = live_pending.order_id
            snapshot['pending_client_order_id'] = live_pending.client_order_id
            snapshot['pending_executed_qty'] = live_pending.partial_executed_qty
            snapshot['pending_remaining_qty'] = live_pending.remaining_qty
        elif self.runtime.pending is not None:
            snapshot['pending_action'] = 'CLEARED_ORPHAN_LOCAL_PENDING'
            snapshot['orphan_pending'] = {
                'side': self.runtime.pending.side,
                'status': self.runtime.pending.status,
                'order_id': self.runtime.pending.order_id,
                'client_order_id': self.runtime.pending.client_order_id,
            }
            self.runtime.pending = None

        if self.runtime.position is not None:
            if not live_position_supported:
                snapshot['position_action'] = 'CLEARED_ORPHAN_LOCAL_POSITION'
                snapshot['orphan_position'] = {
                    'qty': self.runtime.position.qty,
                    'entry_price': self.runtime.position.entry_price,
                    'source': self.runtime.position.source,
                    'order_id': self.runtime.position.order_id,
                    'client_order_id': self.runtime.position.client_order_id,
                }
                self.runtime.position = None
            else:
                old_qty = float(self.runtime.position.qty or 0.0)
                if abs(old_qty - tradable_base) >= max(step, 1e-12):
                    self.runtime.position.qty = tradable_base
                    snapshot['position_action'] = 'ADJUSTED_QTY_FROM_LIVE_BALANCE'
                    snapshot['position_qty_before'] = old_qty
                    snapshot['position_qty_after'] = tradable_base
                if getattr(self.runtime.position, 'risk_plan', None) is None:
                    ensure = getattr(self, '_ensure_position_risk_plan', None)
                    if callable(ensure):
                        ensure()
        elif live_position_supported:
            entry_price = float(mark or 0.0)
            if entry_price <= 0:
                closed_candles = getattr(self, '_closed_candles', []) or []
                entry_price = float(getattr(closed_candles[-1], 'close', 0.0) if closed_candles else 0.0)
            self.runtime.position = Position(qty=tradable_base, entry_price=entry_price, source='startup_live_balance_rehydrate', opened_at=now)
            ensure = getattr(self, '_ensure_position_risk_plan', None)
            if callable(ensure):
                ensure()
            snapshot['position_action'] = 'REHYDRATED_FROM_LIVE_BALANCE'
            snapshot['position_qty_after'] = tradable_base
            snapshot['position_entry_price'] = entry_price

        new_state = self._recovery_state_for_current_runtime()
        previous_state = str(self.runtime.state)
        if previous_state != new_state:
            transition(self.runtime, BotState(new_state))
        snapshot['state_after'] = str(self.runtime.state)
        snapshot['has_pending'] = self.runtime.pending is not None
        snapshot['has_position'] = self.runtime.position is not None
        snapshot['position_source'] = self.runtime.position.source if self.runtime.position is not None else None
        snapshot['pending_source'] = self.runtime.pending.source if self.runtime.pending is not None else None

        self._last_recovery_snapshot = snapshot
        if getattr(self, 'logger', None):
            self.logger.info('RECOVERY_RECONCILE_COMPLETED', 'Startup persistent/live state reconciliation tamamlandı', snapshot)
        self._save_runtime()
        return snapshot

'''


def replace_all_versions(text: str) -> str:
    return text.replace(VERSION_FROM, VERSION_TO)


def ensure_engine_imports(text: str) -> str:
    text = text.replace('from .models import Balance, ExitIntent, PendingOrder, Position, RuntimeState', 'from .models import Balance, ExitIntent, PendingOrder, Position, RuntimeState')
    if 'ExitIntent' not in text.split('\n', 40)[0:40].__str__():
        text = text.replace('from .models import Balance, PendingOrder, Position, RuntimeState', 'from .models import Balance, ExitIntent, PendingOrder, Position, RuntimeState')
    return text


def insert_recovery_methods(text: str) -> str:
    if 'def _startup_reconcile_persistent_state' in text:
        return text
    markers = [
        '    def _protective_exit_snapshot(self, position: Position | None, mark: float | None) -> dict[str, Any]:\n',
        '    def _position_snapshot(self, runtime_payload: dict[str, Any]) -> dict[str, Any]:\n',
        '    def _pending_snapshot(self) -> dict[str, Any]:\n',
    ]
    for marker in markers:
        if marker in text:
            return text.replace(marker, RECOVERY_METHODS + marker, 1)
    raise RuntimeError('Could not find insertion point for startup recovery reconciliation methods')


def insert_start_call(text: str) -> str:
    if 'await self._startup_reconcile_persistent_state()' in text:
        return text
    # Prefer the line immediately before STATE_CHANGED logging inside start().
    needle = "        self.runtime.ws_status = 'CONNECTED'\n        self.logger.info('STATE_CHANGED'"
    if needle in text:
        return text.replace(needle, "        await self._startup_reconcile_persistent_state()\n" + needle, 1)
    # Fallback: after bootstrap. This is less ideal but still safe because method is idempotent.
    needle = '        await self.bootstrap()\n'
    if needle in text:
        return text.replace(needle, needle + '        await self._startup_reconcile_persistent_state()\n', 1)
    raise RuntimeError('Could not insert startup recovery reconciliation call into start()')


def insert_status_snapshot(text: str) -> str:
    if "'recovery_snapshot':" in text or '"recovery_snapshot":' in text:
        return text
    line = "            'event_audit_snapshot': self._event_audit_snapshot(),\n"
    if line in text:
        return text.replace(line, "            'recovery_snapshot': getattr(self, '_last_recovery_snapshot', {}) or {},\n" + line, 1)
    line = "            'startup_hygiene_snapshot': getattr(self.runtime, 'startup_hygiene', None) or {\n"
    if line in text:
        # Insert before startup hygiene if exact event marker is unavailable.
        return text.replace(line, "            'recovery_snapshot': getattr(self, '_last_recovery_snapshot', {}) or {},\n" + line, 1)
    line = "            'health_snapshot': self._health_snapshot(),\n"
    if line in text:
        return text.replace(line, "            'recovery_snapshot': getattr(self, '_last_recovery_snapshot', {}) or {},\n" + line, 1)
    raise RuntimeError('Could not insert recovery_snapshot into get_status()')


def patch_engine() -> dict[str, object]:
    if not ENGINE.exists():
        raise FileNotFoundError(f'engine.py not found: {ENGINE}')
    before = ENGINE.read_text(encoding='utf-8')
    text = replace_all_versions(before)
    text = ensure_engine_imports(text)
    text = insert_recovery_methods(text)
    text = insert_start_call(text)
    text = insert_status_snapshot(text)
    ENGINE.write_text(text, encoding='utf-8')
    after = ENGINE.read_text(encoding='utf-8')
    checks = {
        'has_recovery_method': 'def _startup_reconcile_persistent_state' in after,
        'has_start_call': 'await self._startup_reconcile_persistent_state()' in after,
        'has_recovery_snapshot': "'recovery_snapshot':" in after,
        'contract_version_12': VERSION_TO in after,
    }
    if not all(checks.values()):
        raise RuntimeError(f'engine recovery patch verification failed: {checks}')
    return checks


def patch_optional_file(path: Path) -> dict[str, object]:
    if not path.exists():
        return {'exists': False}
    before = path.read_text(encoding='utf-8')
    after = replace_all_versions(before)
    path.write_text(after, encoding='utf-8')
    return {'exists': True, 'version_replacements': before.count(VERSION_FROM)}


def main() -> int:
    results: dict[str, object] = {}
    results['engine'] = patch_engine()
    results['api'] = patch_optional_file(API)
    results['dashboard'] = patch_optional_file(DASHBOARD)
    print('4B.4.3.6.6.12 restart recovery / persistent reconciliation patch applied')
    for name, value in results.items():
        print(f' - {name}: {value}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
