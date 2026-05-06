from __future__ import annotations

import importlib.util
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_tool(name: str):
    path = ROOT / "tools" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_diagnostics_404_is_optional_runtime_smoke_pass(monkeypatch) -> None:
    smoke = _load_tool("run_runtime_smoke_4B436621")

    def fake_request_json(*args, **kwargs):
        raise urllib.error.HTTPError(
            url="http://127.0.0.1:8000/diagnostics",
            code=404,
            msg="Not Found",
            hdrs=None,
            fp=None,
        )

    monkeypatch.setattr(smoke, "request_json", fake_request_json)
    result = smoke.run_endpoint(
        "http://127.0.0.1:8000",
        "diagnostics",
        "/diagnostics",
        lambda payload: (True, None, {}),
    )
    assert result.ok is True
    assert result.status_code == 404
    assert "optional endpoint" in (result.reason or "")
    assert result.details["optional"] is True


def test_non_diagnostics_404_remains_failure(monkeypatch) -> None:
    smoke = _load_tool("run_runtime_smoke_4B436621")

    def fake_request_json(*args, **kwargs):
        raise urllib.error.HTTPError(
            url="http://127.0.0.1:8000/unknown",
            code=404,
            msg="Not Found",
            hdrs=None,
            fp=None,
        )

    monkeypatch.setattr(smoke, "request_json", fake_request_json)
    result = smoke.run_endpoint(
        "http://127.0.0.1:8000",
        "logs",
        "/logs",
        lambda payload: (True, None, {}),
    )
    assert result.ok is False
    assert result.status_code == 404
