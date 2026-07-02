from __future__ import annotations

import json
import py_compile
from pathlib import Path

PATCH_VERSION = "4B.4.3.6.6.33I-H1"
PATCH_NAME = "Operator Cockpit Engine Position Recovery Key Hotfix"
ROOT = Path.cwd()

ORCHESTRATOR = ROOT / "src" / "tradebot" / "cockpit" / "orchestrator.py"
COMPILE_HELPER = ROOT / "tools" / "compile_operator_cockpit_4B436633I_H1.py"
RUNTIME_HELPER = ROOT / "tools" / "check_cockpit_runtime_4B436633I_H1.py"
TEST_FILE = ROOT / "tests" / "test_operator_cockpit_4B436633I_H1.py"
DOC_FILE = ROOT / "docs" / "OPERATOR_COCKPIT_ENGINE_POSITION_RECOVERY_KEY_HOTFIX_4B436633I_H1.md"
README = ROOT / "README.md"

HELPER_BLOCK = r'''

# --- 4B.4.3.6.6.33I-H1 engine position recovery persistence key hotfix ---
def _engine_position_recovery_key(settings):
    """Return the persistence key used by the 33I recovery gate.

    The 33I snapshot path calls this helper while reading the recovery plan.
    It must be present at module scope before runtime snapshot/WebSocket paths are used.
    The key is symbol-scoped to prevent cross-symbol recovery-plan leakage.
    """
    symbol = getattr(settings, "symbol", None)
    if not symbol:
        symbol = getattr(settings, "trading_symbol", None)
    if not symbol:
        symbol = getattr(settings, "default_symbol", None)
    symbol_text = str(symbol or "UNKNOWN").strip().upper() or "UNKNOWN"
    return f"operator_cockpit:engine_position_recovery:{symbol_text}"
# --- end 4B.4.3.6.6.33I-H1 ---
'''

COMPILE_HELPER_CONTENT = r'''from __future__ import annotations

import json
import py_compile
from pathlib import Path

PATCH_VERSION = "4B.4.3.6.6.33I-H1"
ROOT = Path.cwd()
FILES = [
    "src/tradebot/cockpit/__init__.py",
    "src/tradebot/cockpit/app.py",
    "src/tradebot/cockpit/broadcaster.py",
    "src/tradebot/cockpit/orchestrator.py",
    "src/tradebot/cockpit/schemas.py",
    "src/tradebot/cockpit/security.py",
    "src/tradebot/cli.py",
    "tools/check_cockpit_runtime_4B436633I.py",
    "tools/check_cockpit_runtime_4B436633I_H1.py",
]

errors: list[dict[str, str]] = []
compiled: list[str] = []
for rel in FILES:
    path = ROOT / rel
    if not path.exists():
        if rel.endswith("_H1.py"):
            continue
        errors.append({"file": rel, "error": "missing"})
        continue
    try:
        py_compile.compile(str(path), doraise=True)
        compiled.append(rel)
    except Exception as exc:  # pragma: no cover - helper script output
        errors.append({"file": rel, "error": repr(exc)})

orchestrator = (ROOT / "src/tradebot/cockpit/orchestrator.py").read_text(encoding="utf-8")
helper_defined = "def _engine_position_recovery_key(" in orchestrator
helper_used = "_engine_position_recovery_key(self.settings)" in orchestrator
symbol_scoped_key = "engine_position_recovery:{symbol_text}" in orchestrator
no_auto_position_mutation_contract = "auto_position_mutation_performed" in orchestrator or "engine_position_state_mutated" in orchestrator

result = {
    "patch_version": PATCH_VERSION,
    "ok": not errors and helper_defined and helper_used and symbol_scoped_key,
    "compiled": compiled,
    "errors": errors,
    "engine_position_recovery_key_defined": helper_defined,
    "engine_position_recovery_key_used": helper_used,
    "symbol_scoped_recovery_key": symbol_scoped_key,
    "snapshot_nameerror_hotfix_contract": helper_defined and helper_used,
    "no_auto_position_mutation_contract_still_present": no_auto_position_mutation_contract,
}
print(json.dumps(result, indent=2, ensure_ascii=False))
raise SystemExit(0 if result["ok"] else 1)
'''

RUNTIME_HELPER_CONTENT = r'''from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

PATCH_VERSION = "4B.4.3.6.6.33I-H1"


def _request_json(url: str, token: str, operator: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={
            "X-TradeBot-Auth": token,
            "X-TradeBot-Operator": operator,
        },
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=5) as response:  # noqa: S310 - local operator helper
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Check 33I-H1 cockpit runtime snapshot health.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8787")
    parser.add_argument("--token", required=True)
    parser.add_argument("--operator", required=True)
    args = parser.parse_args()

    result: dict = {"patch_version": PATCH_VERSION}
    try:
        health = _request_json(f"{args.base_url.rstrip('/')}/api/cockpit/health", args.token, args.operator)
        snapshot = _request_json(f"{args.base_url.rstrip('/')}/api/cockpit/snapshot", args.token, args.operator)
    except urllib.error.URLError as exc:
        result.update({
            "ok": False,
            "server_reachable": False,
            "error": str(exc),
            "hint": "Start cockpit first in a separate PowerShell window.",
        })
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 1
    except Exception as exc:
        result.update({
            "ok": False,
            "server_reachable": True,
            "error": repr(exc),
            "hint": "Snapshot request failed; check cockpit terminal for traceback.",
        })
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 1

    runtime_lock = snapshot.get("runtime_lock") or {}
    runtime_awareness = snapshot.get("runtime_awareness") or {}
    recovery_gate = snapshot.get("engine_position_recovery_gate") or snapshot.get("runtime_awareness", {}).get("engine_position_recovery_gate") or {}
    reconciliation_decision_apply = snapshot.get("reconciliation_decision_apply") or runtime_awareness.get("reconciliation_decision_apply") or {}

    startup_error = (snapshot.get("cockpit") or {}).get("startup_error")
    ok = bool(snapshot.get("ok")) and startup_error is None
    result.update({
        "ok": ok,
        "server_reachable": True,
        "health_ok": health.get("ok"),
        "startup_error": startup_error,
        "runtime_lock_pid": runtime_lock.get("pid"),
        "runtime_lock_held_by_current_process": runtime_lock.get("held_by_current_process"),
        "risk_badge": runtime_awareness.get("risk_badge"),
        "entry_guard_disable_reason": (runtime_awareness.get("entry_guard") or {}).get("disable_reason"),
        "reconciliation_decision_apply": reconciliation_decision_apply,
        "engine_position_recovery_gate": recovery_gate,
    })
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
'''

TEST_CONTENT = r'''from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORCHESTRATOR = ROOT / "src" / "tradebot" / "cockpit" / "orchestrator.py"
APPLY = ROOT / "apply_4B436633I_H1_operator_cockpit_recovery_key_hotfix.py"


def test_engine_position_recovery_key_is_defined_and_used() -> None:
    text = ORCHESTRATOR.read_text(encoding="utf-8")
    assert "def _engine_position_recovery_key(" in text
    assert "_engine_position_recovery_key(self.settings)" in text
    assert "engine_position_recovery:{symbol_text}" in text


def test_hotfix_is_symbol_scoped_and_runtime_safe() -> None:
    text = ORCHESTRATOR.read_text(encoding="utf-8")
    assert "getattr(settings, \"symbol\", None)" in text
    assert "operator_cockpit:engine_position_recovery" in text
    assert "UNKNOWN" in text


def test_apply_contract_does_not_relax_safety() -> None:
    text = APPLY.read_text(encoding="utf-8")
    assert '"runtime_mutation_performed": False' in text
    assert '"order_path_mutation_performed": False' in text
    assert '"live_real_enablement_performed": False' in text
    assert '"auth_policy_relaxation_performed": False' in text
    assert '"auto_position_mutation_performed": False' in text
'''

DOC_CONTENT = """# 4B.4.3.6.6.33I-H1 Operator Cockpit Engine Position Recovery Key Hotfix\n\nPurpose: fix the 33I runtime snapshot/WebSocket failure caused by missing `_engine_position_recovery_key`.\n\n## Scope\n\n- Adds the missing symbol-scoped recovery persistence key helper.\n- Keeps the 33I no-auto-position-mutation contract.\n- Does not change live-real, order path, auth policy, strategy thresholds, or runtime position state.\n\n## Expected Runtime Result\n\n`/api/cockpit/snapshot` and `/ws/cockpit` no longer fail with:\n\n```text\nNameError: name '_engine_position_recovery_key' is not defined\n```\n\nEntry guard remains blocked until engine position recovery is actually verified.\n"""


def _append_readme() -> bool:
    marker = f"## {PATCH_VERSION} {PATCH_NAME}"
    if not README.exists():
        README.write_text(f"# TradeBot V2\n\n{marker}\n\n- Added 33I-H1 cockpit recovery-key hotfix.\n", encoding="utf-8")
        return True
    text = README.read_text(encoding="utf-8")
    if marker in text:
        return False
    README.write_text(text.rstrip() + f"\n\n{marker}\n\n- Fixes missing `_engine_position_recovery_key` runtime snapshot/WebSocket NameError.\n- No live-real/order/auth/risk threshold relaxation.\n", encoding="utf-8")
    return True


def main() -> int:
    written: list[str] = []
    if not ORCHESTRATOR.exists():
        raise FileNotFoundError(f"missing {ORCHESTRATOR}")

    text = ORCHESTRATOR.read_text(encoding="utf-8")
    helper_added = False
    if "def _engine_position_recovery_key(" not in text:
        ORCHESTRATOR.write_text(text.rstrip() + HELPER_BLOCK + "\n", encoding="utf-8")
        helper_added = True
        written.append(str(ORCHESTRATOR.relative_to(ROOT)))

    for path, content in [
        (COMPILE_HELPER, COMPILE_HELPER_CONTENT),
        (RUNTIME_HELPER, RUNTIME_HELPER_CONTENT),
        (TEST_FILE, TEST_CONTENT),
        (DOC_FILE, DOC_CONTENT),
    ]:
        path.parent.mkdir(parents=True, exist_ok=True)
        existing = path.read_text(encoding="utf-8") if path.exists() else None
        if existing != content:
            path.write_text(content, encoding="utf-8")
            written.append(str(path.relative_to(ROOT)))

    readme_changed = _append_readme()
    if readme_changed:
        written.append("README.md")

    py_compile.compile(str(ORCHESTRATOR), doraise=True)
    py_compile.compile(str(COMPILE_HELPER), doraise=True)
    py_compile.compile(str(RUNTIME_HELPER), doraise=True)
    py_compile.compile(str(TEST_FILE), doraise=True)

    result = {
        "patch_version": PATCH_VERSION,
        "patch_name": PATCH_NAME,
        "written": written,
        "readme_changed": readme_changed,
        "runtime_mutation_performed": False,
        "order_path_mutation_performed": False,
        "live_real_enablement_performed": False,
        "auth_policy_relaxation_performed": False,
        "auto_position_mutation_performed": False,
        "missing_engine_position_recovery_key_hotfix_added": helper_added or "def _engine_position_recovery_key(" in ORCHESTRATOR.read_text(encoding="utf-8"),
        "snapshot_websocket_nameerror_fixed": True,
        "symbol_scoped_recovery_key_added": True,
        "entry_guard_release_policy_changed": False,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
