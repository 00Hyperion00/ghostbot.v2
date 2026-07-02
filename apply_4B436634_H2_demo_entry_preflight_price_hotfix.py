from __future__ import annotations

import json
import py_compile
from pathlib import Path
from typing import Any

PATCH_VERSION = "4B.4.3.6.6.34-H2"
PATCH_NAME = "Demo Entry Preflight Readiness & Mark Price Fallback Hotfix"
ROOT = Path.cwd()


def _replace_once(text: str, old: str, new: str) -> tuple[str, bool]:
    if old not in text:
        return text, False
    return text.replace(old, new, 1), True


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def patch_orchestrator() -> dict[str, bool]:
    path = ROOT / "src" / "tradebot" / "cockpit" / "orchestrator.py"
    text = path.read_text(encoding="utf-8")
    results: dict[str, bool] = {}

    old_extract = '''def _extract_mark_price(status: dict[str, Any]) -> float | None:
    candidates: list[Any] = [
        status.get("mark_price"),
        status.get("price"),
        status.get("last_price"),
        status.get("current_price"),
    ]
    position = _as_dict(status.get("position_snapshot"))
    candidates.extend([position.get("mark_price"), position.get("entry_price")])
    ticker = _as_dict(status.get("ticker"))
    candidates.extend([ticker.get("lastPrice"), ticker.get("last_price"), ticker.get("price")])
    for candidate in candidates:
        value = _float_value(candidate, 0.0)
        if value > 0:
            return value
    return None
'''
    new_extract = '''def _extract_mark_price(status: dict[str, Any], spec: dict[str, Any] | None = None) -> float | None:
    spec = spec if isinstance(spec, dict) else {}
    candidates: list[Any] = [
        spec.get("mark_price"),
        spec.get("price"),
        spec.get("last_price"),
        spec.get("current_price"),
        status.get("mark_price"),
        status.get("price"),
        status.get("last_price"),
        status.get("current_price"),
    ]
    position = _as_dict(status.get("position_snapshot"))
    candidates.extend([position.get("mark_price"), position.get("entry_price")])
    ticker = _as_dict(status.get("ticker"))
    candidates.extend([ticker.get("lastPrice"), ticker.get("last_price"), ticker.get("price")])
    market = _as_dict(status.get("market"))
    candidates.extend([market.get("mark_price"), market.get("last_price"), market.get("price")])
    for candidate in candidates:
        value = _float_value(candidate, 0.0)
        if value > 0:
            return value
    return None
'''
    text, results["mark_price_spec_fallback_added"] = _replace_once(text, old_extract, new_extract)

    text, results["filter_review_uses_spec_mark_price"] = _replace_once(
        text,
        '    mark_price = _extract_mark_price(status)\n',
        '    mark_price = _extract_mark_price(status, spec)\n',
    )

    marker = '\ndef build_demo_entry_execution_gate_snapshot(*, settings: Any, status: dict[str, Any], entry_guard: dict[str, Any], source_gate: dict[str, Any], cache_reconciliation: dict[str, Any], state: dict[str, Any] | None) -> dict[str, Any]:\n'
    helper = '''
def _entry_guard_ready_for_demo_entry(*, entry_guard: dict[str, Any], cache_reconciliation: dict[str, Any]) -> bool:
    # 34-H2: recognize the 33M stabilized guard release while remaining fail-closed.
    entry_guard = entry_guard if isinstance(entry_guard, dict) else {}
    cache_reconciliation = cache_reconciliation if isinstance(cache_reconciliation, dict) else {}
    risk_badge = str(entry_guard.get("risk_badge") or "UNKNOWN").upper()
    explicit_available = bool(
        entry_guard.get("entry_actions_enabled", False)
        and not entry_guard.get("force_buy_disabled", False)
        and not entry_guard.get("entry_block_until_reconciled", False)
        and risk_badge == "GREEN"
    )
    explicit_release = bool(
        entry_guard.get("entry_guard_release_verified", False)
        or entry_guard.get("entry_guard_release_authorized", False)
        or entry_guard.get("manual_external_recovery_verified", False)
    )
    stabilized_release = bool(
        cache_reconciliation.get("runtime_snapshot_override_active", False)
        and cache_reconciliation.get("stale_engine_balance_invalidated", False)
        and cache_reconciliation.get("entry_guard_release_stabilized_after_safe_apply", False)
        and cache_reconciliation.get("no_mismatch_from_verified_fresh_source", False)
        and risk_badge == "GREEN"
    )
    return bool(explicit_available and (explicit_release or stabilized_release))

'''
    if "def _entry_guard_ready_for_demo_entry" not in text:
        if marker not in text:
            results["entry_guard_ready_helper_added"] = False
        else:
            text = text.replace(marker, helper + marker, 1)
            results["entry_guard_ready_helper_added"] = True
    else:
        results["entry_guard_ready_helper_added"] = True

    text, results["demo_gate_uses_33m_stabilized_entry_guard"] = _replace_once(
        text,
        '    entry_guard_ready = bool(entry_guard.get("entry_actions_enabled", False) and entry_guard.get("entry_guard_release_verified", False))\n',
        '    entry_guard_ready = _entry_guard_ready_for_demo_entry(entry_guard=entry_guard, cache_reconciliation=cache_reconciliation)\n',
    )

    if not all(results.values()):
        missing = [key for key, ok in results.items() if not ok]
        raise RuntimeError(f"34-H2 patch anchors not found: {missing}")
    path.write_text(text, encoding="utf-8")
    return results


def write_support_files() -> list[str]:
    written: list[str] = []
    compile_tool = '''from __future__ import annotations

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
            compiled.append(rel.replace("/", "\\\\"))
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
'''
    _write(ROOT / "tools" / "compile_operator_cockpit_4B436634_H2.py", compile_tool)
    written.append("tools/compile_operator_cockpit_4B436634_H2.py")

    test_file = '''from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORCH = ROOT / "src" / "tradebot" / "cockpit" / "orchestrator.py"


def _text() -> str:
    return ORCH.read_text(encoding="utf-8")


def test_demo_entry_mark_price_spec_fallback_present() -> None:
    text = _text()
    assert "def _extract_mark_price(status: dict[str, Any], spec: dict[str, Any] | None = None)" in text
    assert 'spec.get("mark_price")' in text
    assert "mark_price = _extract_mark_price(status, spec)" in text


def test_demo_entry_gate_uses_33m_stabilized_entry_guard() -> None:
    text = _text()
    assert "def _entry_guard_ready_for_demo_entry" in text
    assert 'entry_guard.get("entry_guard_release_authorized", False)' in text
    assert 'cache_reconciliation.get("entry_guard_release_stabilized_after_safe_apply", False)' in text
    assert "entry_guard_ready = _entry_guard_ready_for_demo_entry(entry_guard=entry_guard, cache_reconciliation=cache_reconciliation)" in text


def test_h2_remains_fail_closed_and_no_live_real_enablement() -> None:
    text = _text()
    helper = text.split("def _entry_guard_ready_for_demo_entry", 1)[1].split("def build_demo_entry_execution_gate_snapshot", 1)[0]
    assert 'risk_badge == "GREEN"' in helper
    assert 'not entry_guard.get("force_buy_disabled", False)' in helper
    assert 'not entry_guard.get("entry_block_until_reconciled", False)' in helper
    assert '"live_real_enablement_performed": False' in text
    assert '"auto_position_mutation_performed": False' in text
'''
    _write(ROOT / "tests" / "test_operator_cockpit_4B436634_H2.py", test_file)
    written.append("tests/test_operator_cockpit_4B436634_H2.py")

    doc = """# 4B.4.3.6.6.34-H2 Demo Entry Preflight Readiness & Mark Price Fallback Hotfix

Fixes two 34 runtime blockers after H1:

- Demo-entry gate did not recognize the 33M stabilized entry guard release when the legacy 33F guard payload omitted `entry_guard_release_verified`.
- Demo-entry dry-run could not compute quantity/notional when engine status did not expose `mark_price`.

34-H2 remains fail-closed for RED risk, unreconciled guards, missing filters, and missing price. It does not enable live-real trading and does not mutate engine position state. Operators may provide `mark_price` in the dry-run/filter body if the runtime status has no ticker price.
"""
    _write(ROOT / "docs" / "OPERATOR_COCKPIT_DEMO_ENTRY_PREFLIGHT_PRICE_HOTFIX_4B436634_H2.md", doc)
    written.append("docs/OPERATOR_COCKPIT_DEMO_ENTRY_PREFLIGHT_PRICE_HOTFIX_4B436634_H2.md")
    return written


def main() -> int:
    patch_results = patch_orchestrator()
    support_written = write_support_files()
    compiled: list[str] = []
    compile_errors: list[dict[str, str]] = []
    for rel in ["src/tradebot/cockpit/orchestrator.py", "src/tradebot/cockpit/app.py", "src/tradebot/cockpit/schemas.py", "tools/compile_operator_cockpit_4B436634_H2.py", "tests/test_operator_cockpit_4B436634_H2.py"]:
        path = ROOT / rel
        try:
            py_compile.compile(str(path), doraise=True)
            compiled.append(rel)
        except Exception as exc:
            compile_errors.append({"file": rel, "error": str(exc)})
    payload: dict[str, Any] = {
        "patch_version": PATCH_VERSION,
        "patch_name": PATCH_NAME,
        "written": ["src/tradebot/cockpit/orchestrator.py", *support_written],
        "compiled": compiled,
        "compile_errors": compile_errors,
        **patch_results,
        "runtime_mutation_performed": False,
        "order_path_mutation_performed": False,
        "live_real_enablement_performed": False,
        "auth_policy_relaxation_performed": False,
        "auto_position_mutation_performed": False,
    }
    print(json.dumps(payload, indent=2))
    return 0 if not compile_errors and all(patch_results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
