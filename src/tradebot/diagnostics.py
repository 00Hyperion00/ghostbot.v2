from __future__ import annotations

import json
import zipfile
from collections import Counter
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Iterable

from .utils import utc_ms

DIAGNOSTICS_CONTRACT_VERSION = '4B.4.3.6.6.17'
SECRET_KEYS = {'api_key', 'api_secret', 'secret', 'password', 'token', 'access_key', 'private_key'}
WARNING_LEVELS = {'WARN', 'WARNING', 'ERROR', 'CRITICAL'}
CRITICAL_CODES = {
    'SAFE_MODE_ACTIVATED',
    'KILL_SWITCH_ACTIVE',
    'BOOTSTRAP_FAILED',
    'RECOVERY_RECONCILE_FAILED',
    'ORDER_SUBMIT_FAILED',
    'ORDER_REJECTED',
    'RISK_EXIT_BLOCKED',
    'LIVE_PREFLIGHT_FAILED',
}


def _to_plain(value: Any) -> Any:
    if is_dataclass(value):
        return {k: _to_plain(v) for k, v in asdict(value).items()}
    if isinstance(value, dict):
        return {str(k): _to_plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_plain(v) for v in value]
    return value


def redact_value(value: Any) -> str:
    text = '' if value is None else str(value)
    if not text:
        return ''
    if len(text) <= 8:
        return '***'
    return f'{text[:4]}...{text[-4:]}'


def redact_payload(payload: Any) -> Any:
    payload = _to_plain(payload)
    if isinstance(payload, dict):
        out: dict[str, Any] = {}
        for key, value in payload.items():
            lowered = str(key).lower()
            if any(secret in lowered for secret in SECRET_KEYS):
                out[key] = redact_value(value)
            else:
                out[key] = redact_payload(value)
        return out
    if isinstance(payload, list):
        return [redact_payload(item) for item in payload]
    return payload


def normalize_event(event: dict[str, Any]) -> dict[str, Any]:
    data = event.get('data') if isinstance(event.get('data'), dict) else {}
    level = str(event.get('level') or data.get('level') or 'INFO').upper()
    code = str(event.get('code') or data.get('code') or '-')
    return {
        'ts': event.get('ts'),
        'level': level,
        'code': code,
        'message': str(event.get('message') or ''),
        'data': redact_payload(data),
    }


def _is_warning_event(event: dict[str, Any]) -> bool:
    level = str(event.get('level') or '').upper()
    code = str(event.get('code') or '')
    return level in WARNING_LEVELS or code in CRITICAL_CODES or code.endswith('_FAILED') or code.endswith('_BLOCKED')


def _safe_bool(value: Any) -> bool:
    return bool(value) if value is not None else False


def build_diagnostics_snapshot(*, status: dict[str, Any] | None, logs: Iterable[dict[str, Any]] | None, generated_at: int | None = None) -> dict[str, Any]:
    status = status or {}
    event_list = [normalize_event(item) for item in (logs or [])]
    warning_events = [event for event in event_list if _is_warning_event(event)]
    latest_critical = sorted(warning_events, key=lambda item: int(item.get('ts') or 0), reverse=True)[:20]
    counts_by_code = Counter(str(event.get('code') or '-') for event in event_list)
    counts_by_level = Counter(str(event.get('level') or 'INFO').upper() for event in event_list)

    health = status.get('health_snapshot') if isinstance(status.get('health_snapshot'), dict) else {}
    risk = status.get('risk_snapshot') if isinstance(status.get('risk_snapshot'), dict) else {}
    config = status.get('config_safety_snapshot') if isinstance(status.get('config_safety_snapshot'), dict) else {}
    model_quality = status.get('model_quality_snapshot') if isinstance(status.get('model_quality_snapshot'), dict) else {}
    model_quality_gate = status.get('model_quality_gate_snapshot') if isinstance(status.get('model_quality_gate_snapshot'), dict) else {}
    performance = status.get('performance_snapshot') if isinstance(status.get('performance_snapshot'), dict) else {}
    recovery = status.get('recovery_snapshot') if isinstance(status.get('recovery_snapshot'), dict) else {}
    reconciliation = status.get('reconciliation_snapshot') if isinstance(status.get('reconciliation_snapshot'), dict) else {}

    reason_codes: list[str] = []
    hints: list[str] = []

    engine_running = _safe_bool(status.get('engine_running'))
    ws_connected = str(status.get('ws_status') or health.get('ws_status') or '').upper() == 'CONNECTED' or _safe_bool(health.get('ws_connected'))
    if not engine_running:
        reason_codes.append('ENGINE_NOT_RUNNING')
        hints.append('API çalışıyor olabilir ama engine running=false; start API veya /start akışını kontrol et.')
    if not ws_connected:
        reason_codes.append('WS_DISCONNECTED')
        hints.append('Websocket bağlantısı kopuk; ağ ve Binance endpoint erişimini kontrol et.')
    if health.get('account_consistency') not in (None, 'HEALTHY'):
        reason_codes.append('ACCOUNT_CONSISTENCY_WARNING')
        hints.append('Account/position tutarlılığı warning; recovery_snapshot ve position_snapshot alanlarını kontrol et.')
    if health.get('pending_consistency') not in (None, 'HEALTHY'):
        reason_codes.append('PENDING_CONSISTENCY_WARNING')
        hints.append('Bekleyen emir tutarlılığı warning; open order ve local pending mutabakatını kontrol et.')
    if risk.get('safe_mode') or risk.get('kill_switch_active'):
        reason_codes.append('SAFE_MODE_OR_KILL_SWITCH_ACTIVE')
        hints.append('Safe mode/kill switch aktif; risk_snapshot.safe_mode_reason_code alanını kontrol et.')
    if config and not config.get('safe_to_trade', True):
        reason_codes.append('CONFIG_NOT_SAFE_TO_TRADE')
        hints.append('Config safety critical/warning üretiyor; config_safety_snapshot.reason_codes alanını kontrol et.')
    if model_quality.get('severity') in ('warning', 'critical'):
        reason_codes.append('MODEL_QUALITY_WARNING')
        hints.append('Model quality warning; model_quality_snapshot.reason_codes ve retrain önerisini kontrol et.')
    if model_quality_gate.get('decision') == 'BLOCK':
        reason_codes.append('MODEL_QUALITY_GATE_BLOCK')
        hints.append('Model quality gate BLOCK; canlı/demo arming öncesi retrain veya daha uzun paper/live-demo örneklemi gerekli.')
    if recovery.get('warnings'):
        reason_codes.append('RECOVERY_WARNINGS_PRESENT')
        hints.append('Restart recovery warning üretti; recovery_snapshot.warnings alanını incele.')
    if reconciliation.get('severity') in ('warning', 'critical') or reconciliation.get('state') in ('ORPHAN_MISSING', 'DEFERRED', 'DEFER_CANDIDATE', 'ERROR'):
        reason_codes.append('ORDER_RECONCILIATION_WARNING')
        hints.append('Canlı emir uzlaşması warning üretiyor; reconciliation_snapshot alanını incele.')
    if latest_critical:
        reason_codes.append('RECENT_WARNING_EVENTS_PRESENT')
        hints.append('Son warning/error eventleri var; diagnostics_snapshot.latest_critical_events alanını incele.')

    severity = 'ok'
    if any(code in reason_codes for code in ('ENGINE_NOT_RUNNING', 'CONFIG_NOT_SAFE_TO_TRADE', 'SAFE_MODE_OR_KILL_SWITCH_ACTIVE', 'MODEL_QUALITY_GATE_BLOCK')):
        severity = 'critical'
    elif reason_codes:
        severity = 'warning'

    checklist = {
        'engine_running': engine_running,
        'ws_connected': ws_connected,
        'account_consistency': health.get('account_consistency', 'UNKNOWN'),
        'position_consistency': health.get('position_consistency', 'UNKNOWN'),
        'pending_consistency': health.get('pending_consistency', 'UNKNOWN'),
        'safe_mode': bool(risk.get('safe_mode', status.get('safe_mode', False))),
        'kill_switch_active': bool(risk.get('kill_switch_active', status.get('kill_switch_active', False))),
        'config_safe_to_trade': bool(config.get('safe_to_trade', True)) if config else None,
        'model_quality_severity': model_quality.get('severity'),
        'model_quality_gate_decision': model_quality_gate.get('decision'),
        'recovery_available': bool(recovery),
        'performance_available': bool(performance),
        'reconciliation_state': reconciliation.get('state'),
        'reconciliation_available': bool(reconciliation),
    }

    return {
        'contract_version': DIAGNOSTICS_CONTRACT_VERSION,
        'generated_at': generated_at or utc_ms(),
        'severity': severity,
        'ready_to_operate': severity != 'critical',
        'reason_codes': sorted(set(reason_codes)),
        'hints': hints,
        'health_checklist': checklist,
        'runtime': {
            'contract_version': status.get('contract_version'),
            'state': str(status.get('state') or ''),
            'symbol': status.get('symbol'),
            'engine_running': engine_running,
            'ws_status': status.get('ws_status'),
            'has_pending': bool((status.get('pending_snapshot') or {}).get('present')) if isinstance(status.get('pending_snapshot'), dict) else False,
            'has_position': bool((status.get('position_snapshot') or {}).get('present')) if isinstance(status.get('position_snapshot'), dict) else False,
        },
        'event_summary': {
            'total_events': len(event_list),
            'warning_event_count': len(warning_events),
            'counts_by_level': dict(counts_by_level),
            'top_codes': dict(counts_by_code.most_common(12)),
        },
        'latest_critical_events': latest_critical,
        'snapshots_available': {
            'health': bool(health),
            'risk': bool(risk),
            'recovery': bool(recovery),
            'model_quality': bool(model_quality),
            'model_quality_gate': bool(model_quality_gate),
            'performance': bool(performance),
            'config_safety': bool(config),
            'reconciliation': bool(reconciliation),
            'decision_audit': bool(status.get('decision_audit_snapshot')),
            'event_audit': bool(status.get('event_audit_snapshot')),
        },
    }


def build_support_bundle_payload(*, status: dict[str, Any], logs: Iterable[dict[str, Any]] | None, config: dict[str, Any] | None = None) -> dict[str, Any]:
    status_payload = redact_payload(status)
    log_payload = [normalize_event(item) for item in (logs or [])]
    config_payload = redact_payload(config or {})
    return {
        'contract_version': DIAGNOSTICS_CONTRACT_VERSION,
        'generated_at': utc_ms(),
        'status': status_payload,
        'logs': log_payload,
        'config': config_payload,
    }


def write_support_bundle(path: str | Path, *, status: dict[str, Any], logs: Iterable[dict[str, Any]] | None = None, config: dict[str, Any] | None = None) -> Path:
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = build_support_bundle_payload(status=status, logs=logs, config=config)
    with zipfile.ZipFile(out_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('status.redacted.json', json.dumps(payload['status'], ensure_ascii=False, indent=2, sort_keys=True))
        zf.writestr('logs.redacted.json', json.dumps(payload['logs'], ensure_ascii=False, indent=2, sort_keys=True))
        zf.writestr('config.redacted.json', json.dumps(payload['config'], ensure_ascii=False, indent=2, sort_keys=True))
        zf.writestr('bundle_manifest.json', json.dumps({
            'contract_version': payload['contract_version'],
            'generated_at': payload['generated_at'],
            'files': ['status.redacted.json', 'logs.redacted.json', 'config.redacted.json'],
        }, ensure_ascii=False, indent=2, sort_keys=True))
    return out_path
