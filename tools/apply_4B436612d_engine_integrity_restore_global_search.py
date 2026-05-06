from __future__ import annotations

import ast
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src' / 'tradebot'
ENGINE = SRC / 'engine.py'
API = SRC / 'api.py'
DASHBOARD = SRC / 'ui' / 'dashboard.py'
RUNTIME_OBS_TEST = ROOT / 'tests' / 'test_runtime_observability_event_audit.py'

VERSION_FROM_VALUES = [
    '4B.4.3.6.6.9',
    '4B.4.3.6.6.10',
    '4B.4.3.6.6.11',
]
VERSION_TO = '4B.4.3.6.6.12'

CORE_REQUIRED_METHODS = [
    'get_status',
    '_entry_guard',
    '_exit_guard',
    '_submit_entry',
    '_submit_exit',
    '_commit_filled_pending',
    '_clear_pending',
    '_reconcile_pending_order',
    '_position_snapshot',
    '_risk_plan_execution_snapshot',
]
FINAL_REQUIRED_METHODS = CORE_REQUIRED_METHODS + [
    '_startup_reconcile_persistent_state',
    '_latest_mark_price',
]

SAFE_LATEST_MARK_PRICE = '''    def _latest_mark_price(self) -> float | None:
        """Return latest mark price without assuming runtime/test-only attributes exist."""
        latest_book = getattr(self, '_latest_book', None)
        if isinstance(latest_book, dict):
            for key in ('bestBid', 'bestAsk'):
                value = latest_book.get(key)
                if value not in (None, '', 0, 0.0):
                    try:
                        return float(value)
                    except (TypeError, ValueError):
                        continue

        closed_candles = getattr(self, '_closed_candles', None) or []
        if closed_candles:
            try:
                value = getattr(closed_candles[-1], 'close', None)
                if value not in (None, ''):
                    return float(value)
            except (TypeError, ValueError, AttributeError, IndexError):
                return None
        return None
'''

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
        mark = self._latest_mark_price()
        if price <= 0 and mark is not None:
            price = float(mark or 0.0)
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
        """Reconcile persisted runtime state with live account data at startup."""
        now = utc_ms()
        symbol_rules = getattr(self, 'symbol_rules', None)
        base_asset = symbol_rules.base_asset if symbol_rules else ''
        quote_asset = symbol_rules.quote_asset if symbol_rules else ''
        base_balance = self.runtime.balances.get(base_asset, Balance()) if base_asset else Balance()
        step = symbol_rules.step_size if symbol_rules else 1e-8
        min_qty = symbol_rules.min_qty if symbol_rules else 0.0
        min_notional = (symbol_rules.min_notional * self.settings.min_notional_buffer_multiplier) if symbol_rules else 0.0
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
            logger = getattr(self, 'logger', None)
            if logger is not None:
                logger.warn('RECOVERY_OPEN_ORDERS_FETCH_FAILED', 'Startup open order reconciliation atlandı', {'error': str(exc), 'symbol': self.settings.symbol})
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
                ensure = getattr(self, '_ensure_position_risk_plan', None)
                if getattr(self.runtime.position, 'risk_plan', None) is None and callable(ensure):
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
        logger = getattr(self, 'logger', None)
        if logger is not None:
            logger.info('RECOVERY_RECONCILE_COMPLETED', 'Startup persistent/live state reconciliation tamamlandı', snapshot)
        self._save_runtime()
        return snapshot

'''


def read(path: Path) -> str:
    return path.read_text(encoding='utf-8')


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding='utf-8')


def replace_versions(text: str) -> str:
    for value in VERSION_FROM_VALUES:
        text = text.replace(value, VERSION_TO)
    return text


def has_method(text: str, name: str) -> bool:
    return re.search(rf'^    (?:async\s+)?def {re.escape(name)}\(', text, flags=re.MULTILINE) is not None


def method_score(text: str) -> int:
    return sum(1 for name in CORE_REQUIRED_METHODS if has_method(text, name))


def find_class_method_span(text: str, name: str) -> tuple[int, int] | None:
    pattern = re.compile(rf'^    (?:async\s+)?def {re.escape(name)}\([^\n]*:\n', re.MULTILINE)
    match = pattern.search(text)
    if not match:
        return None
    start = match.start()
    next_match = re.search(r'^    (?:async\s+)?def \w+\([^\n]*\):\n|^    @(?:staticmethod|classmethod)\n', text[match.end():], flags=re.MULTILINE)
    if next_match:
        end = match.end() + next_match.start()
    else:
        end = len(text)
    return start, end


def replace_or_insert_method_before(text: str, name: str, method_source: str, before_name: str) -> str:
    span = find_class_method_span(text, name)
    if span:
        start, end = span
        return text[:start] + method_source.rstrip() + '\n\n' + text[end:].lstrip('\n')
    before_span = find_class_method_span(text, before_name)
    if not before_span:
        raise RuntimeError(f'Cannot find insertion point before {before_name} for {name}')
    start, _ = before_span
    return text[:start] + method_source + '\n' + text[start:]


def ensure_imports(text: str) -> str:
    if 'ExitIntent' not in text.split('\n', 50).__str__():
        text = text.replace(
            'from .models import Balance, PendingOrder, Position, RuntimeState',
            'from .models import Balance, ExitIntent, PendingOrder, Position, RuntimeState',
        )
    return text


def safe_latest_mark_price(text: str) -> str:
    return replace_or_insert_method_before(text, '_latest_mark_price', SAFE_LATEST_MARK_PRICE, '_latest_atr')


def safe_existing_recovery_method(text: str) -> str:
    span = find_class_method_span(text, '_startup_reconcile_persistent_state')
    if not span:
        return text
    start, end = span
    method = text[start:end]
    if "symbol_rules = getattr(self, 'symbol_rules', None)" not in method:
        method = method.replace(
            '        now = utc_ms()\n',
            "        now = utc_ms()\n        symbol_rules = getattr(self, 'symbol_rules', None)\n",
            1,
        )
    method = method.replace('self.symbol_rules', 'symbol_rules')
    return text[:start] + method + text[end:]


def insert_recovery_methods_if_missing(text: str) -> str:
    if has_method(text, '_startup_reconcile_persistent_state'):
        return safe_existing_recovery_method(text)
    for marker_name in ('_protective_exit_snapshot', '_position_snapshot', '_pending_snapshot', '_latest_mark_price'):
        span = find_class_method_span(text, marker_name)
        if span:
            start, _ = span
            return text[:start] + RECOVERY_METHODS + text[start:]
    raise RuntimeError('No safe insertion point found for recovery methods')


def ensure_start_call(text: str) -> str:
    if 'await self._startup_reconcile_persistent_state()' in text:
        return text
    span = find_class_method_span(text, 'start')
    if not span:
        raise RuntimeError('start() method not found')
    start, end = span
    method = text[start:end]
    needle = "        self.runtime.ws_status = 'CONNECTED'\n"
    if needle in method:
        method = method.replace(needle, "        await self._startup_reconcile_persistent_state()\n" + needle, 1)
    else:
        needle = '        await self.bootstrap()\n'
        if needle not in method:
            raise RuntimeError('Could not insert recovery call into start()')
        method = method.replace(needle, needle + '        await self._startup_reconcile_persistent_state()\n', 1)
    return text[:start] + method + text[end:]


def ensure_recovery_snapshot_in_status(text: str) -> str:
    if "'recovery_snapshot':" in text or '"recovery_snapshot":' in text:
        return text
    span = find_class_method_span(text, 'get_status')
    if not span:
        raise RuntimeError('get_status() method not found')
    start, end = span
    method = text[start:end]
    for line in (
        "            'event_audit_snapshot': self._event_audit_snapshot(),\n",
        "            'startup_hygiene_snapshot': getattr(self.runtime, 'startup_hygiene', None) or {\n",
        "            'health_snapshot': self._health_snapshot(),\n",
    ):
        if line in method:
            method = method.replace(line, "            'recovery_snapshot': getattr(self, '_last_recovery_snapshot', {}) or {},\n" + line, 1)
            return text[:start] + method + text[end:]
    raise RuntimeError('Could not insert recovery_snapshot into get_status()')


def sanitize_restored_engine(text: str) -> str:
    text = replace_versions(text)
    text = ensure_imports(text)
    text = safe_latest_mark_price(text)
    text = insert_recovery_methods_if_missing(text)
    text = ensure_start_call(text)
    text = ensure_recovery_snapshot_in_status(text)
    text = safe_existing_recovery_method(text)
    return text


def _safe_mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def _add_engine_path(paths: list[Path], seen: set[str], path: Path) -> None:
    try:
        resolved = str(path.resolve())
    except OSError:
        resolved = str(path)
    if path.exists() and resolved not in seen:
        seen.add(resolved)
        paths.append(path)


def candidate_paths() -> list[Path]:
    """Find complete engine.py candidates beyond the current folder."""
    paths: list[Path] = []
    seen: set[str] = set()

    roots: list[Path] = []
    for root in [ROOT.parent, ROOT.parent.parent, ROOT.parent.parent.parent]:
        if root.exists() and root not in roots:
            roots.append(root)

    for root in roots:
        for pattern in ('trade_botV2_BACKUP*', '*BACKUP*', 'trade_botV2*'):
            for folder in sorted(root.glob(pattern), key=_safe_mtime, reverse=True):
                _add_engine_path(paths, seen, folder / 'src' / 'tradebot' / 'engine.py')

    users_root = Path(ROOT.anchor) / 'Users' if ROOT.anchor else None
    if users_root is not None and users_root.exists():
        for user_dir in sorted(users_root.glob('*'), key=lambda p: p.name.lower()):
            for desktop_name in ('OneDrive/Masaüstü', 'OneDrive/Desktop', 'Desktop', 'Masaüstü'):
                desktop = user_dir / desktop_name
                if not desktop.exists():
                    continue
                for pattern in ('trade_botV2_BACKUP*', '*BACKUP*', 'trade_botV2*'):
                    for folder in sorted(desktop.glob(pattern), key=_safe_mtime, reverse=True):
                        _add_engine_path(paths, seen, folder / 'src' / 'tradebot' / 'engine.py')
    return paths


def candidate_zip_entries() -> list[tuple[Path, str]]:
    """Find full-project zip candidates containing src/tradebot/engine.py."""
    results: list[tuple[Path, str]] = []
    zip_roots: list[Path] = [ROOT.parent, ROOT.parent.parent]
    users_root = Path(ROOT.anchor) / 'Users' if ROOT.anchor else None
    if users_root is not None and users_root.exists():
        for user_dir in sorted(users_root.glob('*'), key=lambda p: p.name.lower()):
            for name in ('Downloads', 'OneDrive/Masaüstü', 'OneDrive/Desktop', 'Desktop', 'Masaüstü'):
                candidate = user_dir / name
                if candidate.exists():
                    zip_roots.append(candidate)
    seen_zip: set[str] = set()
    for root in zip_roots:
        if not root.exists():
            continue
        for zpath in sorted(root.glob('trade_botV2*.zip'), key=_safe_mtime, reverse=True):
            try:
                key = str(zpath.resolve())
            except OSError:
                key = str(zpath)
            if key in seen_zip:
                continue
            seen_zip.add(key)
            try:
                with zipfile.ZipFile(zpath) as zf:
                    for name in zf.namelist():
                        normalized = name.replace('\\', '/')
                        if normalized.endswith('src/tradebot/engine.py'):
                            results.append((zpath, name))
            except Exception:
                continue
    return results


def pick_backup_engine() -> tuple[Path, str, int]:
    best: tuple[Path, str, int] | None = None
    scanned: list[str] = []
    for path in candidate_paths():
        scanned.append(str(path))
        try:
            text = read(path)
            ast.parse(text)
        except Exception:
            continue
        score = method_score(text)
        if score >= len(CORE_REQUIRED_METHODS):
            return path, text, score
        if best is None or score > best[2]:
            best = (path, text, score)

    for zpath, entry in candidate_zip_entries():
        pseudo = Path(f'{zpath}!{entry}')
        scanned.append(str(pseudo))
        try:
            with zipfile.ZipFile(zpath) as zf:
                text = zf.read(entry).decode('utf-8')
            ast.parse(text)
        except Exception:
            continue
        score = method_score(text)
        if score >= len(CORE_REQUIRED_METHODS):
            return pseudo, text, score
        if best is None or score > best[2]:
            best = (pseudo, text, score)

    if best:
        raise RuntimeError(
            f'No complete backup engine.py found. Best candidate={best[0]} '
            f'score={best[2]}/{len(CORE_REQUIRED_METHODS)}. Scanned={len(scanned)} candidates.'
        )
    raise RuntimeError(
        'No backup engine.py found across current folder, sibling backups, C:\\Users\\* desktops, or Downloads zips. '
        'Upload a full patched project zip or copy a known-good trade_botV2_BACKUP folder next to the active project.'
    )

def backup_current_engine() -> Path:
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    target = ENGINE.with_suffix(f'.broken_before_4B436612d_{timestamp}.py')
    shutil.copy2(ENGINE, target)
    return target


def patch_optional_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {'exists': False}
    before = read(path)
    after = replace_versions(before)
    if path == RUNTIME_OBS_TEST:
        after = after.replace('4B.4.3.6.6.11', VERSION_TO)
    if after != before:
        write(path, after)
    return {'exists': True, 'changed': after != before, 'version_12': VERSION_TO in after}


def main() -> int:
    if not ENGINE.exists():
        raise SystemExit(f'engine.py not found: {ENGINE}')

    current = read(ENGINE)
    current_score = method_score(current)
    source_path: str
    restored_from_backup = False

    if current_score >= len(CORE_REQUIRED_METHODS):
        source = current
        source_path = str(ENGINE)
    else:
        backup_path, source, backup_score = pick_backup_engine()
        backup_file = backup_current_engine()
        source_path = str(backup_path)
        restored_from_backup = True
        print(f'4B.4.3.6.6.12d detected truncated/corrupt engine.py score={current_score}/{len(CORE_REQUIRED_METHODS)}')
        print(f' - current engine backup: {backup_file}')
        print(f' - restoring from: {backup_path} score={backup_score}/{len(CORE_REQUIRED_METHODS)}')

    updated = sanitize_restored_engine(source)
    ast.parse(updated)
    write(ENGINE, updated)

    after = read(ENGINE)
    final_checks = {
        'restored_from_backup': restored_from_backup,
        'source_path': source_path,
        'method_score': method_score(after),
        'all_required_methods_present': all(has_method(after, name) for name in FINAL_REQUIRED_METHODS),
        'safe_latest_book': "getattr(self, '_latest_book', None)" in after,
        'safe_closed_candles': "getattr(self, '_closed_candles', None)" in after,
        'recovery_snapshot_present': "'recovery_snapshot':" in after,
        'contract_version_12': VERSION_TO in after,
    }
    if not all(value for key, value in final_checks.items() if key not in {'restored_from_backup', 'source_path', 'method_score'}):
        raise SystemExit(f'4B.4.3.6.6.12d engine verification failed: {final_checks}')

    api = patch_optional_file(API)
    dashboard = patch_optional_file(DASHBOARD)
    obs_test = patch_optional_file(RUNTIME_OBS_TEST)

    print('4B.4.3.6.6.12d engine integrity restore hotfix applied')
    print(f' - engine: {final_checks}')
    print(f' - api: {api}')
    print(f' - dashboard: {dashboard}')
    print(f' - runtime_observability_tests: {obs_test}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
