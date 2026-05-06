from __future__ import annotations

import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKS = [
    Path('src/tradebot/model_quality_gate.py'),
    Path('src/tradebot/api.py'),
    Path('src/tradebot/engine.py'),
    Path('src/tradebot/diagnostics.py'),
    Path('src/tradebot/ui/dashboard.py'),
    Path('tools/generate_model_quality_gate_4B436624B.py'),
    Path('tests/test_model_quality_gate_4B436624B.py'),
    Path('tests/test_model_retrain_reload_workflow.py'),
    Path('docs/MODEL_QUALITY_GATE_RUNBOOK_4B436624B.md'),
    Path('config.local.example.yaml'),
]


def _contains(path: Path, needle: str) -> bool:
    return needle in path.read_text(encoding='utf-8')


def main() -> None:
    print('4B.4.3.6.6.24B model quality recovery / retrain gate patch applied')
    for rel in CHECKS:
        path = ROOT / rel
        print(f' - {rel.as_posix()}_exists: {path.exists()}')
        if path.suffix == '.py' and path.exists():
            py_compile.compile(str(path), doraise=True)
            print(f' - {rel.as_posix()}_py_compile_ok: True')

    checks = {
        'model_quality_gate_contract_present': _contains(ROOT / 'src/tradebot/model_quality_gate.py', 'MODEL_QUALITY_GATE_CONTRACT_VERSION = "4B.4.3.6.6.24B"'),
        'api_train_quality_gate_present': _contains(ROOT / 'src/tradebot/api.py', 'AI_RELOAD_BLOCKED_MODEL_QUALITY_GATE'),
        'engine_runtime_gate_snapshot_present': _contains(ROOT / 'src/tradebot/engine.py', 'model_quality_gate_snapshot'),
        'diagnostics_gate_block_present': _contains(ROOT / 'src/tradebot/diagnostics.py', 'MODEL_QUALITY_GATE_BLOCK'),
        'dashboard_gate_decision_present': _contains(ROOT / 'src/tradebot/ui/dashboard.py', 'Gate decision'),
        'config_gate_defaults_present': _contains(ROOT / 'src/tradebot/config.py', 'model_quality_gate_min_action_coverage'),
        'report_tool_present': _contains(ROOT / 'tools/generate_model_quality_gate_4B436624B.py', 'Generate 4B.4.3.6.6.24B model quality gate report'),
    }
    for key, value in checks.items():
        print(f' - {key}: {value}')
    if not all(checks.values()):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
