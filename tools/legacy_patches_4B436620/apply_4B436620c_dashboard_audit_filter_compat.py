from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / 'src' / 'tradebot' / 'ui' / 'dashboard.py'
MARKER = '# 4B.4.3.6.6.20c audit event filter compatibility'

FUNCTION_BLOCK = r'''
# 4B.4.3.6.6.20c audit event filter compatibility
def filter_audit_events(events_or_payload: Any = None, **kwargs: Any) -> list[dict[str, Any]]:
    """Backward-compatible client-side audit event filter.

    Supports raw event lists or payloads with events/logs/items/results and the
    common filters used by the dashboard audit viewer tests.
    """
    filters = kwargs.pop('filters', None)
    merged: dict[str, Any] = {}
    if isinstance(filters, dict):
        merged.update(filters)
    merged.update({k: v for k, v in kwargs.items() if v is not None})

    alias_map = {
        'codePrefix': 'code_prefix',
        'codePrefixFilter': 'code_prefix',
        'message_contains': 'contains',
        'text': 'contains',
        'search': 'q',
        'query': 'q',
        'date_from': 'since_ts',
        'from_ts': 'since_ts',
        'date_to': 'until_ts',
        'to_ts': 'until_ts',
    }
    for old_key, new_key in alias_map.items():
        if old_key in merged and new_key not in merged:
            merged[new_key] = merged.pop(old_key)

    if isinstance(events_or_payload, dict):
        raw_events = (
            events_or_payload.get('events')
            or events_or_payload.get('logs')
            or events_or_payload.get('items')
            or events_or_payload.get('results')
            or []
        )
    elif events_or_payload is None:
        raw_events = []
    else:
        raw_events = events_or_payload

    events: list[dict[str, Any]] = []
    for item in raw_events or []:
        if isinstance(item, dict):
            events.append(item)
        else:
            events.append({'level': 'INFO', 'code': '-', 'message': str(item)})

    level_filter = str(merged.get('level') or '').strip().upper()
    code_filter = str(merged.get('code') or '').strip()
    prefix_filter = str(merged.get('code_prefix') or '').strip()
    text_filter = str(merged.get('contains') or merged.get('q') or '').strip().lower()

    def _to_number(value: Any) -> float | None:
        try:
            if value is None or value == '':
                return None
            return float(value)
        except Exception:
            return None

    since_value = _to_number(merged.get('since_ts'))
    until_value = _to_number(merged.get('until_ts'))

    filtered: list[dict[str, Any]] = []
    for event in events:
        event_level = str(event.get('level') or 'INFO').upper()
        event_code = str(event.get('code') or '')
        searchable = ' '.join([
            event_level,
            event_code,
            str(event.get('message') or ''),
            str(event.get('data') or ''),
        ]).lower()
        ts_value = _to_number(event.get('ts'))
        if level_filter and event_level != level_filter:
            continue
        if code_filter and event_code != code_filter:
            continue
        if prefix_filter and not event_code.startswith(prefix_filter):
            continue
        if text_filter and text_filter not in searchable:
            continue
        if since_value is not None and ts_value is not None and ts_value < since_value:
            continue
        if until_value is not None and ts_value is not None and ts_value > until_value:
            continue
        filtered.append(event)

    order_value = str(merged.get('order') or '').strip().lower()
    if order_value in {'desc', 'descending', 'newest'}:
        filtered.sort(key=lambda e: _to_number(e.get('ts')) or 0.0, reverse=True)
    elif order_value in {'asc', 'ascending', 'oldest'}:
        filtered.sort(key=lambda e: _to_number(e.get('ts')) or 0.0)

    try:
        offset_value = max(0, int(merged.get('offset') or 0))
    except Exception:
        offset_value = 0
    try:
        raw_limit = merged.get('limit')
        limit_value = None if raw_limit is None or raw_limit == '' else max(0, int(raw_limit))
    except Exception:
        limit_value = None
    if offset_value:
        filtered = filtered[offset_value:]
    if limit_value is not None:
        filtered = filtered[:limit_value]
    return filtered
'''


def ensure_filter_function(text: str) -> tuple[str, bool]:
    if 'def filter_audit_events(' in text:
        return text, False
    for anchor in ('def build_audit_query_path(', 'def build_audit_summary_text(', '# 4B.4.3.6.6.20a dashboard compatibility helpers'):
        idx = text.find(anchor)
        if idx >= 0:
            return text[:idx] + FUNCTION_BLOCK + '\n\n' + text[idx:], True
    raise RuntimeError('Could not find audit helper insertion point in dashboard.py')


def main() -> int:
    if not DASHBOARD.exists():
        raise RuntimeError(f'dashboard.py not found: {DASHBOARD}')
    text = DASHBOARD.read_text(encoding='utf-8')
    updated, inserted = ensure_filter_function(text)
    DASHBOARD.write_text(updated, encoding='utf-8')
    final = DASHBOARD.read_text(encoding='utf-8')
    checks = {
        'inserted': inserted,
        'function_present': 'def filter_audit_events(' in final,
        'level_filter_present': 'level_filter' in final,
        'code_prefix_filter_present': 'prefix_filter' in final,
        'return_filtered_present': 'return filtered' in final,
    }
    if not all(v for k, v in checks.items() if k != 'inserted'):
        raise RuntimeError(f'20c dashboard audit filter compat verification failed: {checks}')
    print('4B.4.3.6.6.20c dashboard audit filter compatibility patch applied')
    for key, value in checks.items():
        print(f' - {key}: {value}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
