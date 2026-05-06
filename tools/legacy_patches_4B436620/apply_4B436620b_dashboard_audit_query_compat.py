from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / 'src' / 'tradebot' / 'ui' / 'dashboard.py'
MARKER = '# 4B.4.3.6.6.20b audit query path compatibility'

FUNCTION_BLOCK = r'''
# 4B.4.3.6.6.20b audit query path compatibility
def build_audit_query_path(
    filters: dict[str, Any] | None = None,
    *,
    limit: int | str | None = 50,
    level: str | None = None,
    code: str | None = None,
    code_prefix: str | None = None,
    contains: str | None = None,
    q: str | None = None,
    since_ts: int | str | None = None,
    until_ts: int | str | None = None,
    order: str | None = None,
    offset: int | str | None = None,
    cursor: str | None = None,
    **extra: Any,
) -> str:
    """Build the dashboard audit endpoint path in a deterministic, testable way.

    Backward-compatible helper for the audit/event viewer tests and UI.
    It intentionally accepts both a filters dict and keyword args so older
    tests/UI code can call it without knowing the latest signature.
    """
    from urllib.parse import urlencode

    merged: dict[str, Any] = {}
    if isinstance(filters, dict):
        merged.update(filters)
    merged.update({k: v for k, v in extra.items() if v is not None})

    explicit = {
        'limit': limit,
        'level': level,
        'code': code,
        'code_prefix': code_prefix,
        'contains': contains,
        'q': q,
        'since_ts': since_ts,
        'until_ts': until_ts,
        'order': order,
        'offset': offset,
        'cursor': cursor,
    }
    for key, value in explicit.items():
        if value is not None and key not in merged:
            merged[key] = value

    # Common aliases used across previous dashboard/test revisions.
    alias_map = {
        'codePrefix': 'code_prefix',
        'codePrefixFilter': 'code_prefix',
        'message_contains': 'contains',
        'text': 'contains',
        'search': 'q',
        'date_from': 'since_ts',
        'from_ts': 'since_ts',
        'date_to': 'until_ts',
        'to_ts': 'until_ts',
    }
    for old_key, new_key in alias_map.items():
        if old_key in merged and new_key not in merged:
            merged[new_key] = merged.pop(old_key)

    try:
        limit_value = int(merged.get('limit', 50) or 50)
    except Exception:
        limit_value = 50
    limit_value = max(1, min(limit_value, 500))
    merged['limit'] = limit_value

    ordered_keys = [
        'limit',
        'level',
        'code',
        'code_prefix',
        'contains',
        'q',
        'since_ts',
        'until_ts',
        'order',
        'offset',
        'cursor',
    ]
    params: list[tuple[str, str]] = []
    for key in ordered_keys:
        value = merged.pop(key, None)
        if value is None or value == '':
            continue
        params.append((key, str(value)))
    for key in sorted(merged):
        value = merged[key]
        if value is None or value == '':
            continue
        params.append((str(key), str(value)))

    query = urlencode(params)
    return f'/events/audit?{query}' if query else '/events/audit'
'''


def ensure_function(text: str) -> tuple[str, bool]:
    if 'def build_audit_query_path(' in text and MARKER in text:
        return text, False
    if 'def build_audit_query_path(' in text:
        raise RuntimeError('build_audit_query_path exists but is not the 20b compatibility implementation; inspect manually.')
    anchor = 'def build_audit_summary_text('
    if anchor in text:
        return text.replace('\ndef build_audit_summary_text(', FUNCTION_BLOCK + '\n\ndef build_audit_summary_text(', 1), True
    marker = '# 4B.4.3.6.6.20a dashboard compatibility helpers'
    if marker in text:
        idx = text.find(marker)
        return text[:idx] + FUNCTION_BLOCK + '\n' + text[idx:], True
    raise RuntimeError('Could not find audit helper insertion point in dashboard.py')


def main() -> int:
    if not DASHBOARD.exists():
        raise RuntimeError(f'dashboard.py not found: {DASHBOARD}')
    text = DASHBOARD.read_text(encoding='utf-8')
    updated, inserted = ensure_function(text)
    DASHBOARD.write_text(updated, encoding='utf-8')

    final = DASHBOARD.read_text(encoding='utf-8')
    checks = {
        'inserted': inserted,
        'function_present': 'def build_audit_query_path(' in final,
        'marker_present': MARKER in final,
        'endpoint_present': "'/events/audit'" in final or '"/events/audit"' in final,
        'urlencode_present': 'urlencode(params)' in final,
    }
    if not all(v for k, v in checks.items() if k != 'inserted'):
        raise RuntimeError(f'20b dashboard audit query compat verification failed: {checks}')
    print('4B.4.3.6.6.20b dashboard audit query compatibility patch applied')
    for key, value in checks.items():
        print(f' - {key}: {value}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
