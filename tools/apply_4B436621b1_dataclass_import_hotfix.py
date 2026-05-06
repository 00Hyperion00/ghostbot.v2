from __future__ import annotations

import importlib.util
import py_compile
from pathlib import Path

PHASE = "4B.4.3.6.6.21b1"
TARGETS = [
    Path("tools/run_runtime_smoke_4B436621.py"),
    Path("tools/check_dashboard_contract_4B436621.py"),
]
FUTURE_LINE = "from __future__ import annotations\n"


def _remove_future_annotations(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    count = text.count(FUTURE_LINE)
    if count:
        text = text.replace(FUTURE_LINE, "")
        # Normalize leading blank lines if the file started with the future import.
        text = text.lstrip("\n")
        path.write_text(text, encoding="utf-8")
    return count


def _load_by_spec(path: Path, name: str) -> object:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot create import spec for {path}")
    module = importlib.util.module_from_spec(spec)
    # Deliberately do NOT insert into sys.modules. This reproduces the 21b
    # self-test import path and guards against Python 3.14 dataclass failures.
    spec.loader.exec_module(module)
    return module


def main() -> int:
    root = Path.cwd()
    results: dict[str, object] = {}
    removed_total = 0

    for rel in TARGETS:
        path = root / rel
        if not path.exists():
            raise RuntimeError(f"Missing target file: {path}")
        removed = _remove_future_annotations(path)
        removed_total += removed
        py_compile.compile(str(path), doraise=True)
        module = _load_by_spec(path, rel.stem + "_spec_smoke")
        results[f"{rel.name}_future_import_removed"] = removed >= 1 or FUTURE_LINE not in path.read_text(encoding="utf-8")
        results[f"{rel.name}_py_compile_ok"] = True
        results[f"{rel.name}_spec_import_ok"] = module is not None

    smoke = _load_by_spec(root / TARGETS[0], "run_runtime_smoke_4B436621_spec_verify")
    checker = _load_by_spec(root / TARGETS[1], "check_dashboard_contract_4B436621_spec_verify")
    results["runtime_contract_version_compare_ok"] = bool(smoke.contract_version_at_least("4B.4.3.6.6.21"))
    results["dashboard_checker_symbol_present"] = hasattr(checker, "check_imports")
    results["removed_future_import_count"] = removed_total

    print(f"{PHASE} dataclass spec-import compatibility hotfix applied")
    for key, value in results.items():
        print(f" - {key}: {value}")

    required = [value for key, value in results.items() if key != "removed_future_import_count"]
    if not all(required):
        raise RuntimeError(f"{PHASE} checks failed: {results}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
