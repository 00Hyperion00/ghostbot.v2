from __future__ import annotations

import json
import py_compile
from pathlib import Path

PATCH_VERSION = "4B.4.3.6.6.33I"


def main() -> None:
    root = Path.cwd()
    targets = [
        root / "src/tradebot/cockpit/__init__.py",
        root / "src/tradebot/cockpit/app.py",
        root / "src/tradebot/cockpit/broadcaster.py",
        root / "src/tradebot/cockpit/orchestrator.py",
        root / "src/tradebot/cockpit/schemas.py",
        root / "src/tradebot/cockpit/security.py",
        root / "src/tradebot/cli.py",
        root / "tools/check_cockpit_runtime_4B436633I.py",
    ]
    compiled: list[str] = []
    errors: list[dict[str, str]] = []
    for path in targets:
        if not path.exists():
            errors.append({"file": str(path.relative_to(root)), "error": "missing"})
            continue
        try:
            py_compile.compile(str(path), doraise=True)
            compiled.append(str(path.relative_to(root)))
        except Exception as exc:
            errors.append({"file": str(path.relative_to(root)), "error": str(exc)})
    orchestrator = (root / "src/tradebot/cockpit/orchestrator.py").read_text(encoding="utf-8")
    app = (root / "src/tradebot/cockpit/app.py").read_text(encoding="utf-8")
    result = {
        "patch_version": PATCH_VERSION,
        "ok": not errors,
        "compiled": compiled,
        "errors": errors,
        "powershell_glob_required": False,
        "engine_position_recovery_gate_compile_contract": "build_engine_position_recovery_gate_snapshot" in orchestrator,
        "no_auto_position_mutation_contract": "auto_position_mutation_performed" in orchestrator and "engine_position_state_mutated" in orchestrator,
        "recovery_routes_present": "/api/cockpit/engine-position-recovery/create-plan" in app and "/api/cockpit/engine-position-recovery/verify-completion" in app,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
