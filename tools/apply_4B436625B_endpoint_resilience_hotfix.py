from __future__ import annotations

import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKS = [
    ("tools/run_futures_funding_open_interest_edge_exploration_4B436625B.py", [
        "FUTURES_DATA_RETENTION_DAYS",
        "FUTURES_DATA_RETENTION_MS",
        "clamp_futures_data_start_ms",
        "safe_fetch_futures_data_series",
        "optional futures data endpoint failed",
        "HTTPError",
        "body_suffix",
    ]),
    ("tests/test_futures_funding_endpoint_resilience_4B436625B.py", [
        "test_clamps_futures_data_start_to_retention_window",
        "test_optional_futures_endpoint_failure_returns_empty",
    ]),
    ("docs/FUTURES_FUNDING_OPEN_INTEREST_EDGE_EXPLORATION_RUNBOOK_4B436625B_HOTFIX.md", [
        "25B endpoint resilience hotfix",
        "latest 30 days",
        "optional futures metrics",
    ]),
]

COMPILE_FILES = [
    "tools/run_futures_funding_open_interest_edge_exploration_4B436625B.py",
    "tests/test_futures_funding_endpoint_resilience_4B436625B.py",
]


def main() -> int:
    print("4B.4.3.6.6.25B futures endpoint resilience hotfix applied")
    for rel in COMPILE_FILES:
        path = ROOT / rel
        ok = path.exists()
        print(f" - {rel}_exists: {ok}")
        if not ok:
            raise SystemExit(1)
        try:
            py_compile.compile(str(path), doraise=True)
            print(f" - {rel}_py_compile_ok: True")
        except py_compile.PyCompileError as exc:
            print(f" - {rel}_py_compile_ok: False")
            print(exc)
            raise SystemExit(1)
    for rel, markers in CHECKS:
        text = (ROOT / rel).read_text(encoding="utf-8")
        for marker in markers:
            present = marker in text
            print(f" - {marker}_present: {present}")
            if not present:
                raise SystemExit(1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
