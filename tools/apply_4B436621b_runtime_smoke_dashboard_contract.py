from __future__ import annotations

import py_compile
from pathlib import Path

ROOT = Path.cwd()
FILES = [
    ROOT / "tools" / "run_runtime_smoke_4B436621.py",
    ROOT / "tools" / "check_dashboard_contract_4B436621.py",
    ROOT / "tests" / "test_runtime_smoke_dashboard_contract_4B436621.py",
]


def main() -> int:
    checks: dict[str, bool] = {}
    (ROOT / "reports").mkdir(exist_ok=True)
    for path in FILES:
        checks[f"{path.name}_exists"] = path.exists()
        if path.exists():
            py_compile.compile(str(path), doraise=True)
            checks[f"{path.name}_py_compile_ok"] = True
        else:
            checks[f"{path.name}_py_compile_ok"] = False
    checks["reports_dir_exists"] = (ROOT / "reports").exists()
    print("4B.4.3.6.6.21b runtime smoke + dashboard contract tooling applied")
    for key, value in checks.items():
        print(f" - {key}: {value}")
    if not all(checks.values()):
        raise RuntimeError(f"21b verification failed: {checks}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
