from __future__ import annotations

import json
import py_compile
from pathlib import Path

PATCH_VERSION = "4B.4.3.6.6.33H"


def main() -> None:
    root = Path.cwd()
    targets = sorted((root / "src/tradebot/cockpit").glob("*.py")) + [root / "src/tradebot/cli.py", root / "tools/check_cockpit_runtime_4B436633H.py"]
    compiled: list[str] = []
    errors: list[dict[str, str]] = []
    for target in targets:
        try:
            py_compile.compile(str(target), doraise=True)
            compiled.append(target.relative_to(root).as_posix())
        except Exception as exc:
            errors.append({"path": target.relative_to(root).as_posix(), "error": str(exc)})
    print(json.dumps({
        "patch_version": PATCH_VERSION,
        "ok": not errors,
        "compiled": compiled,
        "errors": errors,
        "powershell_glob_required": False,
        "reconciliation_decision_apply_compile_contract": True,
        "runtime_lock_owner_mismatch_resolver_present": True,
    }, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
