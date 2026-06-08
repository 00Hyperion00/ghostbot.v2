from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path


def _write_fake_tradebot_module(project_root: Path) -> None:
    package = project_root / "src" / "tradebot"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "operator_cockpit_v2_read_only.py").write_text(
        '''from __future__ import annotations\n\nOPERATOR_COCKPIT_V2_SAFE_ACTIONS_VERSION = "4B.4.3.6.6.26C"\n\ndef collect_operator_cockpit_snapshot(project_root):\n    return {\n        "read_only": True,\n        "safe_operator_actions": {"get_only": True},\n        "project_root": str(project_root),\n        "turkish_path": r"C:\\\\Users\\\\muhas\\\\OneDrive\\\\Masaüstü\\\\trade_botV2\\\\reports\\\\oluşmadı.json",\n        "message": "MAE / MFE verisi henüz oluşmadı.",\n    }\n\ndef make_operator_cockpit_server(project_root, *, host="127.0.0.1", port=8090):\n    raise AssertionError("server must not start during --once-json")\n''',
        encoding="utf-8",
    )


def _copy_runner(project_root: Path) -> Path:
    source = Path(__file__).resolve().parents[1] / "tools" / "run_operator_cockpit_v2_4B436626C.py"
    target = project_root / "tools" / source.name
    target.parent.mkdir(parents=True)
    target.write_bytes(source.read_bytes())
    return target


def test_26ch1_runner_declares_utf8_stdout_contract_markers() -> None:
    runner = Path(__file__).resolve().parents[1] / "tools" / "run_operator_cockpit_v2_4B436626C.py"
    text = runner.read_text(encoding="utf-8")
    assert 'OPERATOR_COCKPIT_V2_WINDOWS_UTF8_ONCE_JSON_RUNNER_HOTFIX_VERSION = "4B.4.3.6.6.26C-H1"' in text
    assert "OPERATOR_COCKPIT_V2_ONCE_JSON_UTF8_STDOUT_CONTRACT = True" in text
    assert "stdout_buffer.write(encoded)" in text
    assert '.encode("utf-8")' in text


def test_26ch1_once_json_emits_utf8_bytes_independent_of_console_locale(tmp_path: Path) -> None:
    root = tmp_path / "Trade Bot Masaüstü"
    _write_fake_tradebot_module(root)
    runner = _copy_runner(root)
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "cp1252"
    completed = subprocess.run(
        [sys.executable, str(runner), "--project-root", str(root), "--once-json"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        check=False,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stderr.decode("utf-8", errors="replace")
    decoded = completed.stdout.decode("utf-8", errors="strict")
    payload = json.loads(decoded)
    assert payload["read_only"] is True
    assert payload["safe_operator_actions"]["get_only"] is True
    assert "Masaüstü" in payload["turkish_path"]
    assert "oluşmadı" in payload["turkish_path"]
    assert payload["message"] == "MAE / MFE verisi henüz oluşmadı."


def test_26ch1_once_json_output_is_not_cp1252_encoded(tmp_path: Path) -> None:
    root = tmp_path / "trade_botV2"
    _write_fake_tradebot_module(root)
    runner = _copy_runner(root)
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "cp1252"
    completed = subprocess.run(
        [sys.executable, str(runner), "--project-root", str(root), "--once-json"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        check=False,
        timeout=10,
    )
    assert completed.returncode == 0
    assert "Masaüstü".encode("utf-8") in completed.stdout
    assert "oluşmadı".encode("utf-8") in completed.stdout


def test_26ch1_once_json_is_compatible_with_existing_text_mode_utf8_regression(tmp_path: Path) -> None:
    root = tmp_path / "Trade Bot Masaüstü"
    _write_fake_tradebot_module(root)
    runner = _copy_runner(root)
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "cp1252"
    completed = subprocess.run(
        [sys.executable, str(runner), "--project-root", str(root), "--once-json"],
        text=True,
        encoding="utf-8",
        errors="strict",
        capture_output=True,
        env=env,
        check=False,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["read_only"] is True
    assert "Masaüstü" in payload["turkish_path"]
    assert payload["message"] == "MAE / MFE verisi henüz oluşmadı."


def test_26ch1_utf8_writer_fallback_without_stdout_buffer(monkeypatch, tmp_path: Path) -> None:
    root = tmp_path / "fixture"
    _write_fake_tradebot_module(root)
    runner = _copy_runner(root)
    sys.path.insert(0, str(root / "src"))
    try:
        spec = importlib.util.spec_from_file_location("runner_26ch1", runner)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        class _TextOnlyStdout:
            def __init__(self) -> None:
                self.text = ""
            def write(self, value: str) -> None:
                self.text += value
            def flush(self) -> None:
                return None
        stdout = _TextOnlyStdout()
        monkeypatch.setattr(module.sys, "stdout", stdout)
        module._write_utf8_json_stdout({"message": "Masaüstü oluşmadı"})
        assert json.loads(stdout.text)["message"] == "Masaüstü oluşmadı"
    finally:
        sys.path.remove(str(root / "src"))


def test_26ch1_runner_py_compile() -> None:
    runner = Path(__file__).resolve().parents[1] / "tools" / "run_operator_cockpit_v2_4B436626C.py"
    completed = subprocess.run([sys.executable, "-m", "py_compile", str(runner)], capture_output=True, check=False)
    assert completed.returncode == 0, completed.stderr.decode("utf-8", errors="replace")
