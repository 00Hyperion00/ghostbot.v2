from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tradebot.strict_config_unknown_key_fail_closed import ConfigSchemaError, evaluate, validate_yaml_text_strict

READY_SOURCE = {
    "status": "READY",
    "decision": "REPO_HYGIENE_EVIDENCE_RETENTION_READY_NO_SUBMIT_PRODUCTION_HARDENING_P0_2_LOCKED",
    "p0_repo_hygiene_evidence_retention_closed": True,
    "p0_repo_hygiene_evidence_retention_closed_by": "4B.4.3.6.6.37C",
    "p0_hardening_closed_gap_count_after_37c": 2,
    "p0_hardening_open_gap_count_after_37c": 8,
    "phase_37_planning_only": True,
    "network_request_performed": False,
    "exchange_submit_performed": False,
    "order_submit_performed": False,
}


def seed_source(root: Path, payload: dict[str, object] | None = None) -> Path:
    reports = root / "reports" / "recovery"
    reports.mkdir(parents=True, exist_ok=True)
    path = reports / "4B436637C_repo_hygiene_evidence_retention_20260703T130049Z_ready.json"
    path.write_text(json.dumps(payload or READY_SOURCE), encoding="utf-8")
    return path


def test_ready_strict_config_unknown_key_fail_closed(tmp_path: Path) -> None:
    seed_source(tmp_path)
    payload = evaluate(tmp_path)
    assert payload["status"] == "READY"
    assert payload["decision"] == "STRICT_CONFIG_UNKNOWN_KEY_FAIL_CLOSED_READY_NO_SUBMIT_PRODUCTION_HARDENING_P0_3_LOCKED"
    assert payload["source_37c_status"] == "SOURCE_37C_READY"
    assert payload["strict_config_schema_guard_complete"] is True
    assert payload["yaml_unknown_key_hard_error_probe_passed"] is True
    assert payload["strict_config_unknown_root_key_rejected"] is True
    assert payload["strict_config_unknown_nested_key_rejected"] is True
    assert payload["p0_strict_config_unknown_key_fail_closed"] is True
    assert payload["p0_hardening_closed_gap_count_after_37d"] == 3
    assert payload["p0_hardening_open_gap_count_after_37d"] == 7
    assert payload["strict_config_runtime_loader_mutation_performed"] is False
    assert payload["network_request_performed"] is False
    assert payload["exchange_submit_performed"] is False


def test_missing_source_is_not_ready(tmp_path: Path) -> None:
    payload = evaluate(tmp_path)
    assert payload["status"] == "NOT_READY"
    assert payload["source_37c_status"] == "SOURCE_37C_MISSING"
    assert "SOURCE_37C_READY_REPORT_NOT_FOUND" in payload["errors"]


def test_unknown_yaml_keys_raise_hard_error() -> None:
    with pytest.raises(ConfigSchemaError):
        validate_yaml_text_strict("schema_version: 1\nunknown_key: true\n")
    with pytest.raises(ConfigSchemaError):
        validate_yaml_text_strict("risk:\n  risk_per_trade_pct: 0.25\n  typo_risk_key: true\n")
    accepted = validate_yaml_text_strict("schema_version: 1\nrisk:\n  risk_per_trade_pct: 0.25\n")
    assert accepted["schema_version"] == 1


def test_run_script_writes_reports_without_runtime_mutation(tmp_path: Path) -> None:
    seed_source(tmp_path)
    script = ROOT / "tools" / "run_4B436637D_strict_config_unknown_key_fail_closed.py"
    result = subprocess.run(
        [sys.executable, str(script), "--repo-root", str(tmp_path), "--reports-dir", str(tmp_path / "reports" / "recovery"), "--once-json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "READY"
    assert Path(payload["report_path"]).exists()
    assert Path(payload["strict_config_schema_guard_path"]).exists()
    assert Path(payload["strict_config_unknown_key_probe_path"]).exists()
    assert payload["strict_config_runtime_loader_mutation_performed"] is False
    assert payload["reload_performed"] is False
    assert payload["order_submit_performed"] is False
