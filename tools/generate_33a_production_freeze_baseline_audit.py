from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PHASE = "33A"
CONTRACT_VERSION = "4B.4.3.6.6.33A"
REPORT_DIR = Path("reports") / "production_hardening"
REPORT_JSON = REPORT_DIR / "4B436633A_production_freeze_baseline_audit.json"
REPORT_MD = REPORT_DIR / "4B436633A_production_freeze_baseline_audit.md"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8-sig")
    except OSError:
        return ""


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_md(path: Path, payload: dict[str, Any]) -> None:
    blockers = payload.get("blockers", [])
    lines = [
        f"# {CONTRACT_VERSION} Production Freeze Baseline Audit",
        "",
        f"- generated_at: `{payload['generated_at']}`",
        f"- decision: `{payload['decision']}`",
        f"- status: `{payload['status']}`",
        f"- repo_root: `{payload['repo_root']}`",
        "",
        "## Blockers",
        "",
    ]
    if blockers:
        for item in blockers:
            lines.append(f"- `{item}`")
    else:
        lines.append("- none")
    lines.extend(["", "## Key Checks", ""])
    for key, value in payload.get("checks", {}).items():
        lines.append(f"- `{key}`: `{value}`")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _git(args: list[str]) -> tuple[int, str]:
    try:
        completed = subprocess.run(["git", *args], text=True, capture_output=True, check=False)
    except OSError as exc:
        return 127, str(exc)
    return completed.returncode, (completed.stdout + completed.stderr).strip()


def _find_api_routes(api_source: str) -> list[dict[str, str]]:
    routes: list[dict[str, str]] = []
    for match in re.finditer(r"@app\.(get|post|put|delete|patch)\(\s*['\"]([^'\"]+)['\"]", api_source):
        routes.append({"method": match.group(1).upper(), "path": match.group(2)})
    return routes


def _settings_defaults(repo_root: Path) -> dict[str, Any]:
    config_path = repo_root / "src" / "tradebot" / "config.py"
    source = _read(config_path)
    defaults: dict[str, Any] = {}
    for name in [
        "execution_mode",
        "live_trading_armed",
        "live_real_double_confirm",
        "auto_trade_on_signal",
        "api_auth_enabled",
        "api_auth_token",
        "destructive_action_confirmation_required",
        "runtime_lock_enabled",
        "strict_config_validation",
    ]:
        pattern = rf"^\s*{re.escape(name)}\s*:\s*[^=]+?=\s*(.+?)\s*$"
        match = re.search(pattern, source, flags=re.MULTILINE)
        if not match:
            defaults[name] = None
            continue
        raw = match.group(1).strip()
        try:
            defaults[name] = ast.literal_eval(raw)
        except Exception:
            if raw == "True":
                defaults[name] = True
            elif raw == "False":
                defaults[name] = False
            else:
                defaults[name] = raw
    return defaults


def _duplicate_test_basenames(repo_root: Path) -> list[dict[str, Any]]:
    paths = [
        path for path in repo_root.rglob("test_*.py")
        if ".venv" not in path.parts and ".git" not in path.parts
    ]
    by_name: dict[str, list[str]] = {}
    for path in paths:
        by_name.setdefault(path.name, []).append(str(path.relative_to(repo_root)))
    return [
        {"basename": name, "paths": sorted(items)}
        for name, items in sorted(by_name.items())
        if len(items) > 1
    ]


def build_audit(repo_root: Path) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    api_path = repo_root / "src" / "tradebot" / "api.py"
    api_security_path = repo_root / "src" / "tradebot" / "api_security.py"
    persistence_path = repo_root / "src" / "tradebot" / "persistence.py"
    pyproject_path = repo_root / "pyproject.toml"
    pytest_ini_path = repo_root / "pytest.ini"
    cockpit_path = repo_root / "src" / "tradebot" / "operator_cockpit_v2_read_only.py"
    paper_gate_path = repo_root / "src" / "tradebot" / "paper_sandbox_execution_reconciliation_gate.py"

    code, branch = _git(["branch", "--show-current"])
    _, commit = _git(["rev-parse", "--short", "HEAD"])
    _, status_short = _git(["status", "--short"])

    api_source = _read(api_path)
    api_security_source = _read(api_security_path)
    persistence_source = _read(persistence_path)
    pytest_ini = _read(pytest_ini_path)
    cockpit_source = _read(cockpit_path)
    paper_source = _read(paper_gate_path)

    routes = _find_api_routes(api_source)
    destructive_paths = {
        "/start",
        "/stop",
        "/force-buy",
        "/force-sell",
        "/cancel-pending",
        "/risk-reset",
        "/safe-mode/toggle",
        "/ai/train",
        "/ai/reload",
    }
    destructive_routes = [route for route in routes if route["path"] in destructive_paths]

    defaults = _settings_defaults(repo_root)
    duplicate_tests = _duplicate_test_basenames(repo_root)

    checks: dict[str, Any] = {
        "git_branch": branch if code == 0 else "UNKNOWN",
        "git_commit": commit,
        "working_tree_dirty": bool(status_short),
        "python_version": sys.version.split()[0],
        "pyproject_requires_python": "requires-python" in _read(pyproject_path),
        "pytest_testpaths_limited_to_tests": "testpaths" in pytest_ini and re.search(r"(?im)^\s*testpaths\s*=\s*tests\s*$", pytest_ini) is not None,
        "duplicate_test_basenames_count": len(duplicate_tests),
        "api_route_count": len(routes),
        "destructive_route_count": len(destructive_routes),
        "api_security_middleware_present": "install_api_security" in api_source,
        "destructive_confirmations_declared": "DESTRUCTIVE_CONFIRMATIONS" in api_security_source,
        "api_auth_default_safe": defaults.get("api_auth_enabled") is True,
        "destructive_confirmation_default_safe": defaults.get("destructive_action_confirmation_required") is True,
        "execution_mode_default": defaults.get("execution_mode"),
        "live_trading_armed_default": defaults.get("live_trading_armed"),
        "live_real_double_confirm_default": defaults.get("live_real_double_confirm"),
        "auto_trade_on_signal_default": defaults.get("auto_trade_on_signal"),
        "strict_config_validation_default": defaults.get("strict_config_validation"),
        "runtime_lock_enabled_default": defaults.get("runtime_lock_enabled"),
        "api_lifecycle_starts_engine_on_startup": "await engine.start()" in api_source,
        "sqlite_wal_declared": "journal_mode=WAL" in persistence_source,
        "sqlite_backup_uses_sqlite_backup_api": ".backup(" in persistence_source,
        "sqlite_backup_copy2_detected": "shutil.copy2(self.path, target)" in persistence_source,
        "paper_gate_sqlite_mirror_required_export_present": "SQLITE_MIRROR_REQUIRED_DECISION" in paper_source,
        "cockpit_risk_sizing_audit_parity_export_present": "OPERATOR_COCKPIT_V2_RISK_SIZING_AUDIT_PARITY" in cockpit_source,
        "cockpit_risk_sizing_evidence_builder_present": "_build_risk_sizing_in_memory_evidence_pack" in cockpit_source,
    }

    blockers: list[str] = []
    if checks["duplicate_test_basenames_count"]:
        blockers.append("PYTEST_COLLECTION_DUPLICATE_TEST_BASENAME")
    if not checks["pytest_testpaths_limited_to_tests"]:
        blockers.append("PYTEST_DISCOVERY_NOT_LIMITED_TO_TESTS")
    if not checks["api_auth_default_safe"]:
        blockers.append("API_AUTH_DEFAULT_OPEN")
    if not checks["destructive_confirmation_default_safe"]:
        blockers.append("DESTRUCTIVE_CONFIRMATION_DEFAULT_OPEN")
    if checks["api_lifecycle_starts_engine_on_startup"]:
        blockers.append("API_STARTUP_ENGINE_AUTOSTART_DETECTED")
    if checks["sqlite_backup_copy2_detected"] and not checks["sqlite_backup_uses_sqlite_backup_api"]:
        blockers.append("SQLITE_WAL_BACKUP_UNSAFE_COPY2")
    if not checks["paper_gate_sqlite_mirror_required_export_present"]:
        blockers.append("MISSING_SQLITE_MIRROR_REQUIRED_DECISION_EXPORT")
    if not checks["cockpit_risk_sizing_audit_parity_export_present"]:
        blockers.append("MISSING_RISK_SIZING_COCKPIT_AUDIT_PARITY_EXPORT")
    if not checks["cockpit_risk_sizing_evidence_builder_present"]:
        blockers.append("MISSING_RISK_SIZING_EVIDENCE_PACK_BUILDER")
    if checks["destructive_route_count"] > 0 and not checks["api_auth_default_safe"]:
        blockers.append("DESTRUCTIVE_API_SURFACE_WITH_DEFAULT_OPEN_AUTH")

    return {
        "contract_version": CONTRACT_VERSION,
        "phase": PHASE,
        "generated_at": _utc_now(),
        "repo_root": str(repo_root),
        "decision": "BLOCK_PRODUCTION_HARDENING_REQUIRED" if blockers else "BASELINE_READY",
        "status": "FAIL" if blockers else "PASS",
        "approved_for_live_real": False,
        "approved_for_paper_candidate": False,
        "approved_for_paper_transition_candidate": False,
        "approved_for_runtime_overlay_activation_candidate": False,
        "approved_for_parameter_relaxation_candidate": False,
        "live_real_enabled": False,
        "paper_live_enabled": False,
        "runtime_overlay_enabled": False,
        "training_reload_performed": False,
        "trading_action_performed": False,
        "order_actions_performed": False,
        "exchange_submit_performed": False,
        "network_request_performed": False,
        "config_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "checks": checks,
        "blockers": blockers,
        "destructive_routes": destructive_routes,
        "duplicate_tests": duplicate_tests,
        "next_required_phase": "33B_API_FAIL_CLOSED_SECURITY_HARDENING",
    }


def main() -> int:
    repo_root = Path.cwd()
    payload = build_audit(repo_root)
    _write_json(REPORT_JSON, payload)
    _write_md(REPORT_MD, payload)
    print(f"{CONTRACT_VERSION} production freeze baseline audit written")
    print(f" - json: {REPORT_JSON}")
    print(f" - md  : {REPORT_MD}")
    print(f" - status: {payload['status']}")
    print(f" - blockers: {len(payload['blockers'])}")
    for blocker in payload["blockers"]:
        print(f"   - {blocker}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
