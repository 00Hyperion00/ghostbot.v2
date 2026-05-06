from __future__ import annotations

import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.build_release_archive_4B436624A import (
    build_release_archive,
    is_excluded,
    scan_file_for_plain_secrets,
)
from tradebot.config import Settings


def test_settings_to_dict_redacts_api_credentials_by_default() -> None:
    settings = Settings(api_key="A" * 32, api_secret="B" * 64, symbol="ETHUSDT")

    redacted = settings.to_dict()
    raw = settings.to_dict(include_secrets=True)

    assert redacted["api_key"] == "[REDACTED]"
    assert redacted["api_secret"] == "[REDACTED]"
    assert raw["api_key"] == "A" * 32
    assert raw["api_secret"] == "B" * 64
    assert "api_host" not in redacted
    assert "api_port" not in redacted


def test_release_exclusion_patterns_cover_runtime_and_secrets() -> None:
    patterns = [".venv/**", "config.local.yaml", "**/__pycache__/**", "*.bak", "logs/**"]

    assert is_excluded(".venv/Lib/site-packages/x.py", patterns)
    assert is_excluded("config.local.yaml", patterns)
    assert is_excluded("src/tradebot/__pycache__/api.pyc", patterns)
    assert is_excluded("src/tradebot/api.py.bak", patterns)
    assert is_excluded("logs/tradebot.log", patterns)
    assert not is_excluded("src/tradebot/api.py", patterns)
    assert not is_excluded("config.local.example.yaml", patterns)


def test_secret_scanner_flags_plain_config_values(tmp_path: Path) -> None:
    secret_file = tmp_path / "config.yaml"
    secret_file.write_text(
        "api_key: " + "A" * 32 + "\napi_secret: " + "B" * 64 + "\n",
        encoding="utf-8",
    )
    example_file = tmp_path / "config.local.example.yaml"
    example_file.write_text('api_key: ""\napi_secret: "${TRADEBOT_API_SECRET}"\n', encoding="utf-8")

    hits = scan_file_for_plain_secrets(secret_file, tmp_path)
    example_hits = scan_file_for_plain_secrets(example_file, tmp_path)

    assert "config.yaml:api_key" in hits
    assert "config.yaml:api_secret" in hits
    assert example_hits == []


def test_build_release_archive_excludes_runtime_state_and_config_local(tmp_path: Path) -> None:
    root = tmp_path / "project"
    (root / "src" / "tradebot").mkdir(parents=True)
    (root / ".venv" / "Lib").mkdir(parents=True)
    (root / ".tradebot").mkdir()
    (root / "logs").mkdir()
    (root / "src" / "tradebot" / "api.py").write_text("print('ok')\n", encoding="utf-8")
    (root / ".venv" / "Lib" / "x.py").write_text("bad\n", encoding="utf-8")
    (root / ".tradebot" / "tradebot.db").write_text("db\n", encoding="utf-8")
    (root / "logs" / "tradebot.log").write_text("log\n", encoding="utf-8")
    (root / "config.local.yaml").write_text("api_key: " + "A" * 32 + "\n", encoding="utf-8")
    (root / "config.local.example.yaml").write_text('api_key: ""\n', encoding="utf-8")

    result = build_release_archive(root, root / "dist")

    assert result.ok is True
    assert result.secret_hits == []
    with zipfile.ZipFile(result.archive_path) as zf:
        names = set(zf.namelist())
    assert "src/tradebot/api.py" in names
    assert "config.local.example.yaml" in names
    assert "config.local.yaml" not in names
    assert ".venv/Lib/x.py" not in names
    assert ".tradebot/tradebot.db" not in names
    assert "logs/tradebot.log" not in names
