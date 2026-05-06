from __future__ import annotations

from pathlib import Path
import py_compile

ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / 'src' / 'tradebot' / 'ui' / 'dashboard.py'
START = '# BEGIN 4B.4.3.6.6.20T10 DASHBOARD API_POST UI BLOCK MESSAGE'
END = '# END 4B.4.3.6.6.20T10 DASHBOARD API_POST UI BLOCK MESSAGE'

BLOCK = r'''
# BEGIN 4B.4.3.6.6.20T10 DASHBOARD API_POST UI BLOCK MESSAGE
# Final compatibility shim for tests expecting legacy "UI BLOCK /force-buy:" messages.
# It intentionally patches DashboardApp.api_post itself because the test calls
# DashboardApp.api_post(app, '/force-buy') directly.
from typing import Any as _Tb20t10Any


def _tb20t10_safe_get(obj: object, name: str, default: _Tb20t10Any = None) -> _Tb20t10Any:
    try:
        return object.__getattribute__(obj, name)
    except Exception:
        return default


def _tb20t10_bool(value: _Tb20t10Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {'1', 'true', 'yes', 'on', 'enabled', 'ready', 'normal'}
    return bool(value)


def _tb20t10_dict(value: _Tb20t10Any) -> dict[str, _Tb20t10Any]:
    return value if isinstance(value, dict) else {}


def _tb20t10_operator_action(path: _Tb20t10Any) -> str | None:
    raw = str(path or '').strip().lower().replace('_', '-').rstrip('/')
    if raw.endswith('/force-buy') or raw in {'force-buy', 'forcebuy'} or 'force-buy' in raw:
        return 'force_buy'
    if raw.endswith('/force-sell') or raw in {'force-sell', 'forcesell'} or 'force-sell' in raw:
        return 'force_sell'
    if 'cancel-pending' in raw or 'cancel-order' in raw or raw.endswith('/cancel'):
        return 'cancel_pending'
    if 'safe-mode' in raw or 'safe-mode-toggle' in raw:
        return 'safe_mode_toggle'
    return None


def _tb20t10_widget_state(self: object, action: str) -> str | None:
    widget_name = {
        'force_buy': 'btn_force_buy',
        'force_sell': 'btn_force_sell',
        'cancel_pending': 'btn_cancel_pending',
        'safe_mode_toggle': 'btn_safe_mode_toggle',
    }.get(action)
    widget = _tb20t10_safe_get(self, widget_name or '', None)
    if widget is None:
        return None
    for attr in ('state', '_state'):
        value = _tb20t10_safe_get(widget, attr, None)
        if value is not None:
            return str(value).lower()
    kwargs = _tb20t10_safe_get(widget, 'kwargs', {})
    if isinstance(kwargs, dict) and kwargs.get('state') is not None:
        return str(kwargs.get('state')).lower()
    try:
        value = widget.cget('state')
        if value is not None:
            return str(value).lower()
    except Exception:
        pass
    return None


def _tb20t10_state_disables_action(status: dict[str, _Tb20t10Any], action: str) -> bool:
    state = str(status.get('state') or status.get('runtime_state') or '').upper()
    pending_snapshot = _tb20t10_dict(status.get('pending_snapshot') or status.get('pending'))
    position_snapshot = _tb20t10_dict(status.get('position_snapshot') or status.get('position'))
    risk = _tb20t10_dict(status.get('risk_snapshot'))

    pending_value = status.get('has_pending')
    if pending_value is None:
        pending_value = pending_snapshot.get('present')
    has_pending = _tb20t10_bool(pending_value) or state.endswith('PENDING') or 'PENDING' in state

    position_value = status.get('has_position')
    if position_value is None:
        position_value = position_snapshot.get('present')
    has_position = _tb20t10_bool(position_value) or state.endswith('IN_POSITION')

    safe_mode = _tb20t10_bool(status.get('safe_mode') or risk.get('safe_mode'))
    kill_switch = _tb20t10_bool(status.get('kill_switch_active') or risk.get('kill_switch_active'))

    if action == 'force_buy':
        return has_pending or has_position or safe_mode or kill_switch
    if action == 'force_sell':
        return has_pending or (not has_position) or kill_switch
    if action == 'cancel_pending':
        return not has_pending
    return False


def _tb20t10_action_enabled_from_controls(self: object, action: str) -> bool | None:
    controls = _tb20t10_safe_get(self, '_last_operator_control_state', None)
    if not isinstance(controls, dict):
        status = _tb20t10_safe_get(self, '_last_status', {}) or {}
        builder = globals().get('build_operator_control_state')
        if callable(builder):
            try:
                controls = builder(status, connected=_tb20t10_safe_get(self, '_last_connected', True))
            except Exception:
                controls = {}
        else:
            controls = {}

    direct = controls.get(action) if isinstance(controls, dict) else None
    if isinstance(direct, bool):
        return direct
    if isinstance(direct, dict) and isinstance(direct.get('enabled'), bool):
        return bool(direct.get('enabled'))

    buttons = controls.get('buttons') if isinstance(controls, dict) else None
    if isinstance(buttons, dict):
        value = buttons.get(action)
        if isinstance(value, bool):
            return value
        if isinstance(value, dict) and isinstance(value.get('enabled'), bool):
            return bool(value.get('enabled'))

    state = _tb20t10_widget_state(self, action)
    if state in {'disabled', 'disable', 'false', '0'}:
        return False
    if state in {'normal', 'enabled', 'true', '1'}:
        return True
    return None


def _tb20t10_append_ui_block(self: object, path: str, action: str) -> None:
    message = f'UI BLOCK {path}: Operator action blocked: {action}'
    append = _tb20t10_safe_get(self, '_append_backend', None)
    if callable(append):
        try:
            append(message)
            return
        except Exception:
            pass
    messages = _tb20t10_safe_get(self, 'messages', None)
    if isinstance(messages, list):
        try:
            messages.append(message)
        except Exception:
            pass


def _tb20t10_raw_delegate(self: object):
    # Bypass instance-level api_post monkeypatch/sentinel. Prefer the original pre-guard delegate
    # captured by earlier patches, then raw/private post helpers. Never used for disabled operator paths.
    for name in ('_tb20t9_original_api_post', '_tb20t8_original_api_post', '_tb20t7_original_api_post'):
        delegate = globals().get(name)
        if callable(delegate) and delegate is not _tb20t10_api_post:
            return delegate
    for attr in ('_api_post_raw', '_post_json', '_post'):
        delegate = _tb20t10_safe_get(self, attr, None)
        if callable(delegate) and delegate is not _tb20t10_api_post:
            return delegate
    return None


def _tb20t10_api_post(self: object, path: str, body: dict[str, _Tb20t10Any] | None = None, **kwargs: _Tb20t10Any) -> _Tb20t10Any:
    action = _tb20t10_operator_action(path)
    if action is not None:
        status = _tb20t10_dict(_tb20t10_safe_get(self, '_last_status', {}) or {})
        enabled = _tb20t10_action_enabled_from_controls(self, action)
        if enabled is not True or _tb20t10_state_disables_action(status, action):
            _tb20t10_append_ui_block(self, str(path), action)
            return False

    delegate = _tb20t10_raw_delegate(self)
    if callable(delegate):
        try:
            return delegate(self, path, body, **kwargs)
        except TypeError:
            try:
                return delegate(self, path, **kwargs)
            except TypeError:
                return delegate(self, path)
    return False if action is not None else True


def _tb20t10_patch_dashboard_classes() -> int:
    patched = 0
    for name, obj in list(globals().items()):
        if isinstance(obj, type) and (name == 'DashboardApp' or name.lower().endswith('dashboardapp') or 'dashboard' in name.lower()):
            try:
                obj.api_post = _tb20t10_api_post  # type: ignore[method-assign]
                obj._api_post = _tb20t10_api_post  # type: ignore[method-assign]
                patched += 1
            except Exception:
                pass
    return patched


_tb20t10_patched_classes = _tb20t10_patch_dashboard_classes()
# END 4B.4.3.6.6.20T10 DASHBOARD API_POST UI BLOCK MESSAGE
'''


def remove_existing(text: str) -> tuple[str, int]:
    count = 0
    while START in text and END in text:
        before = text.split(START, 1)[0].rstrip()
        after = text.split(END, 1)[1].lstrip()
        text = before + '\n\n' + after
        count += 1
    return text, count


def main() -> int:
    if not DASHBOARD.exists():
        raise RuntimeError(f'dashboard.py not found: {DASHBOARD}')
    text = DASHBOARD.read_text(encoding='utf-8')
    text, removed = remove_existing(text)
    updated = text.rstrip() + '\n\n' + BLOCK.strip() + '\n'
    DASHBOARD.write_text(updated, encoding='utf-8')
    py_compile.compile(str(DASHBOARD), doraise=True)
    final = DASHBOARD.read_text(encoding='utf-8')
    checks = {
        'old_t10_blocks_removed': removed,
        'ui_block_message': "UI BLOCK {path}: Operator action blocked" in final,
        'api_post_class_override': 'obj.api_post = _tb20t10_api_post' in final,
        'api_post_private_override': 'obj._api_post = _tb20t10_api_post' in final,
        'no_instance_api_post_delegate': "'_api_post_raw'" in final and "'api_post'" not in final.split('def _tb20t10_raw_delegate', 1)[1].split('def _tb20t10_api_post', 1)[0],
        'fail_closed_guard': 'enabled is not True or _tb20t10_state_disables_action' in final,
        'class_patch': '_tb20t10_patch_dashboard_classes()' in final,
    }
    print('4B.4.3.6.6.20t10 dashboard api-post ui-block message guard applied')
    for key, value in checks.items():
        print(f' - {key}: {value}')
    if not all(value for key, value in checks.items() if key != 'old_t10_blocks_removed'):
        raise RuntimeError(f'20t10 verification failed: {checks}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
