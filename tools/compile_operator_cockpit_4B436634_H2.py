from __future__ import annotations

import json
import py_compile
from pathlib import Path

PATCH_VERSION = "4B.4.3.6.6.34-H2"
ROOT = Path(__file__).resolve().parents[1]
FILES = [
    "src/tradebot/cockpit/schemas.py",
    "src/tradebot/cockpit/security.py",
    "src/tradebot/cockpit/orchestrator.py",
    "src/tradebot/cockpit/app.py",
    "tools/check_cockpit_runtime_4B436634.py",
    "tools/compile_operator_cockpit_4B436634_H2.py",
]


def main() -> int:
    compiled = []
    errors = []
    for rel in FILES:
        path = ROOT / rel
        try:
            py_compile.compile(str(path), doraise=True)
            compiled.append(rel.replace("/", "\\"))
        except Exception as exc:
            errors.append({"file": rel, "error": str(exc)})
    orchestrator_text = (ROOT / "src/tradebot/cockpit/orchestrator.py").read_text(encoding="utf-8")
    checks = {
        "entry_guard_ready_helper_present": "def _entry_guard_ready_for_demo_entry" in orchestrator_text,
        "mark_price_spec_fallback_present": 'spec.get("mark_price")' in orchestrator_text,
        "filter_review_uses_spec_mark_price": "mark_price = _extract_mark_price(status, spec)" in orchestrator_text,
        "demo_gate_uses_33m_stabilized_entry_guard": "_entry_guard_ready_for_demo_entry(entry_guard=entry_guard" in orchestrator_text,
        "no_engine_position_mutation_contract": '"engine_position_state_mutated": False' in orchestrator_text and '"auto_position_mutation_performed": False' in orchestrator_text,
    }
    payload = {"patch_version": PATCH_VERSION, "ok": not errors and all(checks.values()), "compiled": compiled, "errors": errors, **checks}
    print(json.dumps(payload, indent=2))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
