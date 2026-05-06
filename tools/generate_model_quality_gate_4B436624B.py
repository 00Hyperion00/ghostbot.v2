from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tradebot.model_quality_gate import (
    MODEL_QUALITY_GATE_CONTRACT_VERSION,
    build_runtime_model_quality_gate,
    evaluate_training_result_quality,
)


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(payload, dict):
        raise TypeError(f'{path} must contain a JSON object')
    return payload


def _runtime_snapshot_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if isinstance(payload.get('model_quality_snapshot'), dict):
        return dict(payload['model_quality_snapshot'])
    return dict(payload)


def _write_markdown(path: Path, *, mode: str, gate: dict[str, Any], source: Path) -> None:
    metrics = gate.get('metrics') or {}
    reason_codes = gate.get('reason_codes') or []
    warnings = gate.get('warnings') or []
    lines = [
        f'# 4B.4.3.6.6.24B Model Quality Gate',
        '',
        f'- Contract: `{gate.get("contract_version", MODEL_QUALITY_GATE_CONTRACT_VERSION)}`',
        f'- Mode: `{mode}`',
        f'- Source: `{source.as_posix()}`',
        f'- Decision: `{gate.get("decision")}`',
        f'- OK: `{gate.get("ok")}`',
        f'- Reload allowed: `{gate.get("reload_allowed")}`',
    ]
    if 'live_demo_allowed' in gate:
        lines.append(f'- Live-demo allowed: `{gate.get("live_demo_allowed")}`')
    if 'live_real_allowed' in gate:
        lines.append(f'- Live-real allowed: `{gate.get("live_real_allowed")}`')
    lines.extend([
        f'- Reason codes: `{reason_codes}`',
        f'- Warnings: `{warnings}`',
        '',
        '## Metrics',
        '',
        '```json',
        json.dumps(metrics, ensure_ascii=False, indent=2, sort_keys=True),
        '```',
        '',
        '## Risk Manager Note',
        '',
    ])
    if gate.get('decision') == 'BLOCK':
        lines.append('Model kalite kapısı BLOCK üretti. Bu durumda aday model reload edilmemeli ve canlı/demo arming yapılmamalıdır.')
    elif gate.get('decision') == 'WARN':
        lines.append('Model kalite kapısı WARN üretti. Demo gözlem yapılabilir; gerçek canlı işlem için ek örneklem ve manuel onay gerekir.')
    else:
        lines.append('Model kalite kapısı PASS üretti. Bu tek başına canlı işlem izni değildir; risk/config/soak kapıları da PASS olmalıdır.')
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main() -> None:
    parser = argparse.ArgumentParser(description='Generate 4B.4.3.6.6.24B model quality gate report')
    parser.add_argument('--mode', choices=('runtime', 'training'), required=True)
    parser.add_argument('--input', required=True, help='JSON status/snapshot or training result file')
    parser.add_argument('--out-dir', default='reports')
    args = parser.parse_args()

    source = Path(args.input)
    payload = _load_json(source)
    gate = build_runtime_model_quality_gate(_runtime_snapshot_from_payload(payload)) if args.mode == 'runtime' else evaluate_training_result_quality(payload)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = _utc_stamp()
    json_path = out_dir / f'4B436624B_model_quality_gate_{args.mode}_{stamp}.json'
    md_path = out_dir / f'4B436624B_model_quality_gate_{args.mode}_{stamp}.md'
    report = {
        'ok': bool(gate.get('ok')),
        'contract_version': MODEL_QUALITY_GATE_CONTRACT_VERSION,
        'mode': args.mode,
        'source': source.as_posix(),
        'gate': gate,
    }
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding='utf-8')
    _write_markdown(md_path, mode=args.mode, gate=gate, source=source)
    print(json.dumps({'ok': bool(gate.get('ok')), 'decision': gate.get('decision'), 'json_path': json_path.as_posix(), 'md_path': md_path.as_posix(), 'reason_codes': gate.get('reason_codes') or []}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
