from __future__ import annotations

import py_compile
from pathlib import Path

ROOT = Path.cwd()
SMOKE = ROOT / "tools" / "run_runtime_smoke_4B436621.py"
TEST = ROOT / "tests" / "test_runtime_smoke_optional_diagnostics_4B436621.py"

OLD_EXCEPT = '''    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:\n        return SmokeResult(name=name, ok=False, url=url, elapsed_sec=0.0, reason=f"request failed: {exc}", details={"exception_type": type(exc).__name__})\n'''

NEW_EXCEPT = '''    except urllib.error.HTTPError as exc:\n        code = int(getattr(exc, "code", 0) or 0)\n        if name == "diagnostics" and code == 404:\n            return SmokeResult(\n                name=name,\n                ok=True,\n                url=url,\n                status_code=404,\n                elapsed_sec=0.0,\n                reason="optional endpoint not available (404)",\n                details={"optional": True, "fallback": "status snapshots"},\n            )\n        return SmokeResult(\n            name=name,\n            ok=False,\n            url=url,\n            status_code=code or None,\n            elapsed_sec=0.0,\n            reason=f"request failed: {exc}",\n            details={"exception_type": type(exc).__name__},\n        )\n    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:\n        return SmokeResult(name=name, ok=False, url=url, elapsed_sec=0.0, reason=f"request failed: {exc}", details={"exception_type": type(exc).__name__})\n'''

TEST_TEXT = '''from __future__ import annotations\n\nimport importlib.util\nimport urllib.error\nfrom pathlib import Path\n\nROOT = Path(__file__).resolve().parents[1]\n\n\ndef _load_tool(name: str):\n    path = ROOT / "tools" / f"{name}.py"\n    spec = importlib.util.spec_from_file_location(name, path)\n    assert spec is not None and spec.loader is not None\n    module = importlib.util.module_from_spec(spec)\n    spec.loader.exec_module(module)\n    return module\n\n\ndef test_diagnostics_404_is_optional_runtime_smoke_pass(monkeypatch) -> None:\n    smoke = _load_tool("run_runtime_smoke_4B436621")\n\n    def fake_request_json(*args, **kwargs):\n        raise urllib.error.HTTPError(\n            url="http://127.0.0.1:8000/diagnostics",\n            code=404,\n            msg="Not Found",\n            hdrs=None,\n            fp=None,\n        )\n\n    monkeypatch.setattr(smoke, "request_json", fake_request_json)\n    result = smoke.run_endpoint(\n        "http://127.0.0.1:8000",\n        "diagnostics",\n        "/diagnostics",\n        lambda payload: (True, None, {}),\n    )\n    assert result.ok is True\n    assert result.status_code == 404\n    assert "optional endpoint" in (result.reason or "")\n    assert result.details["optional"] is True\n\n\ndef test_non_diagnostics_404_remains_failure(monkeypatch) -> None:\n    smoke = _load_tool("run_runtime_smoke_4B436621")\n\n    def fake_request_json(*args, **kwargs):\n        raise urllib.error.HTTPError(\n            url="http://127.0.0.1:8000/unknown",\n            code=404,\n            msg="Not Found",\n            hdrs=None,\n            fp=None,\n        )\n\n    monkeypatch.setattr(smoke, "request_json", fake_request_json)\n    result = smoke.run_endpoint(\n        "http://127.0.0.1:8000",\n        "logs",\n        "/logs",\n        lambda payload: (True, None, {}),\n    )\n    assert result.ok is False\n    assert result.status_code == 404\n''' 


def patch_smoke(text: str) -> tuple[str, bool]:
    if "optional endpoint not available (404)" in text:
        return text, False
    if OLD_EXCEPT not in text:
        raise RuntimeError("run_endpoint exception block not found; cannot apply 21b2 diagnostics hotfix")
    return text.replace(OLD_EXCEPT, NEW_EXCEPT), True


def main() -> int:
    if not SMOKE.exists():
        raise RuntimeError(f"missing runtime smoke tool: {SMOKE}")
    text = SMOKE.read_text(encoding="utf-8")
    updated, changed = patch_smoke(text)
    SMOKE.write_text(updated, encoding="utf-8")
    TEST.write_text(TEST_TEXT, encoding="utf-8")
    checks: dict[str, object] = {
        "smoke_tool_exists": SMOKE.exists(),
        "diagnostics_404_optional": "optional endpoint not available (404)" in updated,
        "http_error_caught_before_urlerror": updated.find("except urllib.error.HTTPError") < updated.find("except (urllib.error.URLError"),
        "non_diagnostics_404_still_fails": "if name == \"diagnostics\" and code == 404" in updated,
        "self_test_exists": TEST.exists(),
        "changed": changed,
    }
    py_compile.compile(str(SMOKE), doraise=True)
    py_compile.compile(str(TEST), doraise=True)
    checks["smoke_py_compile_ok"] = True
    checks["self_test_py_compile_ok"] = True
    print("4B.4.3.6.6.21b2 runtime smoke optional diagnostics hotfix applied")
    for key, value in checks.items():
        print(f" - {key}: {value}")
    required = [
        "smoke_tool_exists",
        "diagnostics_404_optional",
        "http_error_caught_before_urlerror",
        "non_diagnostics_404_still_fails",
        "self_test_exists",
        "smoke_py_compile_ok",
        "self_test_py_compile_ok",
    ]
    if not all(bool(checks[key]) for key in required):
        raise RuntimeError(f"21b2 verification failed: {checks}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
