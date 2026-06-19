from __future__ import annotations

import json
from pathlib import Path

from tradebot.production_readiness_gate import REQUIRED_EVIDENCE, build_consolidated_readiness_snapshot


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def _payload(contract_version: str, decision: str) -> dict:
    return {
        "contract_version": contract_version,
        "decision": decision,
        "approved_for_live_real": False,
        "approved_for_paper_candidate": False,
        "runtime_overlay_activation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
    }


def test_29a_h1_actual_decision_is_accepted() -> None:
    assert REQUIRED_EVIDENCE["29A-H1"]["decision"] == "PRODUCTION_REPORT_PATH_HYGIENE_READY"


def test_consolidation_accepts_29a_h1_actual_report_decision(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    _write(reports / "4B436629A_production_hardening_p0_decision_20260619T1.json", _payload("4B.4.3.6.6.29A", "PRODUCTION_HARDENING_P0_READY_LIVE_REAL_STILL_BLOCKED"))
    _write(reports / "4B436629A_H1_production_report_path_hygiene_decision_20260619T1.json", _payload("4B.4.3.6.6.29A-H1", "PRODUCTION_REPORT_PATH_HYGIENE_READY"))
    _write(reports / "4B436629B_api_operator_security_hardening_decision_20260619T1.json", _payload("4B.4.3.6.6.29B", "API_OPERATOR_SECURITY_HARDENING_READY_LIVE_REAL_STILL_BLOCKED"))
    _write(reports / "4B436629C_sqlite_audit_ledger_upgrade_decision_20260619T1.json", _payload("4B.4.3.6.6.29C", "SQLITE_AUDIT_LEDGER_UPGRADE_READY_LIVE_REAL_STILL_BLOCKED"))
    _write(reports / "4B436629C_H2_sqlite_probe_explicit_connection_close_decision_20260619T1.json", _payload("4B.4.3.6.6.29C-H2", "SQLITE_PROBE_EXPLICIT_CONNECTION_CLOSE_READY_LIVE_REAL_STILL_BLOCKED"))
    _write(reports / "4B436629D_replay_backtest_walkforward_gate_decision_20260619T1.json", _payload("4B.4.3.6.6.29D", "REPLAY_BACKTEST_WALKFORWARD_GATE_READY_LIVE_REAL_STILL_BLOCKED"))

    snapshot = build_consolidated_readiness_snapshot(reports)

    assert snapshot["decision"] == "PRODUCTION_READINESS_CONSOLIDATION_READY_LIVE_REAL_STILL_BLOCKED"
    assert snapshot["evidence_complete"] is True
    assert snapshot["approved_for_paper_candidate_preflight"] is True
    assert snapshot["approved_for_paper_candidate"] is False
    assert snapshot["approved_for_live_real"] is False
    assert snapshot["evidence"]["29A-H1"]["ok"] is True


def test_consolidation_still_rejects_live_real_approval(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    bad = _payload("4B.4.3.6.6.29A-H1", "PRODUCTION_REPORT_PATH_HYGIENE_READY")
    bad["approved_for_live_real"] = True
    _write(reports / "4B436629A_H1_production_report_path_hygiene_decision_20260619T1.json", bad)
    snapshot = build_consolidated_readiness_snapshot(reports)
    assert snapshot["approved_for_live_real"] is False
    assert snapshot["approved_for_paper_candidate"] is False
