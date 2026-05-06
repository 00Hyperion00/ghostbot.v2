from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def load_launcher():
    module_path = Path(__file__).resolve().parents[1] / 'tools' / 'desktop_launcher.py'
    spec = importlib.util.spec_from_file_location('desktop_launcher_for_test', module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_launcher_builds_api_and_dashboard_commands(tmp_path: Path) -> None:
    launcher = load_launcher()
    config = tmp_path / 'config.local.yaml'
    api_cmd = launcher.build_api_command(config, '127.0.0.1', 8000)
    dashboard_cmd = launcher.build_dashboard_command(config, '127.0.0.1', 8000)

    assert api_cmd[:3] == [sys.executable, '-m', 'tradebot.cli']
    assert 'api' in api_cmd
    assert '--config' in api_cmd
    assert str(config) in api_cmd
    assert dashboard_cmd[:3] == [sys.executable, '-m', 'tradebot.cli']
    assert 'dashboard' in dashboard_cmd
    assert '8000' in dashboard_cmd


def test_launcher_pythonpath_puts_src_first(tmp_path: Path) -> None:
    launcher = load_launcher()
    root = tmp_path
    existing = '/other/path'
    value = launcher.build_pythonpath(root, existing)
    parts = value.split(launcher.os.pathsep)

    assert parts[0] == str(root / 'src')
    assert '/other/path' in parts


def test_launcher_check_reports_missing_config_without_starting_process(tmp_path: Path, monkeypatch) -> None:
    launcher = load_launcher()
    (tmp_path / 'src').mkdir()
    monkeypatch.setattr(launcher, 'check_dependencies', lambda: [])
    monkeypatch.setattr(launcher, 'fetch_health', lambda *args, **kwargs: None)
    monkeypatch.setattr(launcher, 'port_is_open', lambda *args, **kwargs: False)

    check = launcher.run_check(tmp_path, 'missing.yaml', '127.0.0.1', 8000)

    assert check.contract_version == '4B.4.3.6.6.16'
    assert check.ok is False
    assert check.config_exists is False
    assert any(item.startswith('CONFIG_NOT_FOUND:') for item in check.errors)


def test_launcher_check_online_api(monkeypatch, tmp_path: Path) -> None:
    launcher = load_launcher()
    (tmp_path / 'src').mkdir()
    (tmp_path / 'config.local.yaml').write_text('symbol: ETHUSDT\n', encoding='utf-8')
    monkeypatch.setattr(launcher, 'check_dependencies', lambda: [])
    monkeypatch.setattr(launcher, 'fetch_health', lambda *args, **kwargs: {'ok': True, 'symbol': 'ETHUSDT'})
    monkeypatch.setattr(launcher, 'port_is_open', lambda *args, **kwargs: True)

    check = launcher.run_check(tmp_path, 'config.local.yaml', '127.0.0.1', 8000)

    assert check.ok is True
    assert check.api_online is True
    assert check.api_health == {'ok': True, 'symbol': 'ETHUSDT'}


def test_batch_files_call_desktop_launcher() -> None:
    root = Path(__file__).resolve().parents[1]
    expected = ['start_tradebot.bat', 'start_api.bat', 'start_dashboard.bat', 'check_tradebot_env.bat']
    for filename in expected:
        text = (root / filename).read_text(encoding='utf-8')
        assert 'tools\\desktop_launcher.py' in text
        assert 'PYTHONPATH=%CD%\\src' in text
    assert 'one-click' in (root / 'start_tradebot.bat').read_text(encoding='utf-8')
    assert 'api' in (root / 'start_api.bat').read_text(encoding='utf-8')
    assert 'dashboard' in (root / 'start_dashboard.bat').read_text(encoding='utf-8')
    assert 'check' in (root / 'check_tradebot_env.bat').read_text(encoding='utf-8')


def test_launcher_check_json_is_serializable(tmp_path: Path, monkeypatch) -> None:
    launcher = load_launcher()
    (tmp_path / 'src').mkdir()
    (tmp_path / 'config.local.yaml').write_text('symbol: ETHUSDT\n', encoding='utf-8')
    monkeypatch.setattr(launcher, 'check_dependencies', lambda: [])
    monkeypatch.setattr(launcher, 'fetch_health', lambda *args, **kwargs: None)
    monkeypatch.setattr(launcher, 'port_is_open', lambda *args, **kwargs: False)

    check = launcher.run_check(tmp_path, 'config.local.yaml', '127.0.0.1', 8000)
    encoded = json.dumps(launcher.asdict(check))

    assert '4B.4.3.6.6.16' in encoded
