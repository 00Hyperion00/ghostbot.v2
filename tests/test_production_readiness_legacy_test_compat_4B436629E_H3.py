from __future__ import annotations

import json
from pathlib import Path

from tradebot.production_readiness_gate import REQUIRED_EVIDENCE, build_consolidated_readiness_snapshot, load_production_hardening_evidence


def _write_report(base: Path, name: str, *, contract: str, decision: str, ok: bool = True) -> None:
    payload = {
        "ok": ok,
        "contract_version": contract,
        "decision": decision,
        "approved_for_live_real": False,
        "approved_for_paper_candidate": False,
        "runtime_overlay_activation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
    }
    (base / name).write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def test_29a_h1_actual_decision_is_the_contract_value() -> None:
    assert REQUIRED_EVIDENCE["29A-H1"]["decision"] == "PRODUCTION_REPORT_PATH_HYGIENE_READY"


def test_legacy_h1_refresh_sample_uses_actual_29a_h1_decision(tmp_path: Path) -> None:
    _write_report(tmp_path, "4B436629A_production_hardening_p0_decision_20260619T192825Z.json", contract="4B.4.3.6.6.29A", decision="PRODUCTION_HARDENING_P0_NOT_READY", ok=False)
    _write_report(tmp_path, "4B436629A_production_hardening_p0_decision_20260619T202500Z.json", contract="4B.4.3.6.6.29A", decision="PRODUCTION_HARDENING_P0_READY_LIVE_REAL_STILL_BLOCKED")
    _write_report(tmp_path, "4B436629A_H1_production_report_path_hygiene_decision_20260619T202501Z.json", contract="4B.4.3.6.6.29A-H1", decision="PRODUCTION_REPORT_PATH_HYGIENE_READY")
    _write_report(tmp_path, "4B436629B_api_operator_security_hardening_decision_20260619T202502Z.json", contract="4B.4.3.6.6.29B", decision="API_OPERATOR_SECURITY_HARDENING_READY_LIVE_REAL_STILL_BLOCKED")
    _write_report(tmp_path, "4B436629C_sqlite_audit_ledger_upgrade_decision_20260619T202503Z.json", contract="4B.4.3.6.6.29C", decision="SQLITE_AUDIT_LEDGER_UPGRADE_READY_LIVE_REAL_STILL_BLOCKED")
    _write_report(tmp_path, "4B436629C_H2_sqlite_probe_explicit_connection_close_decision_20260619T202504Z.json", contract="4B.4.3.6.6.29C-H2", decision="SQLITE_PROBE_EXPLICIT_CONNECTION_CLOSE_READY_LIVE_REAL_STILL_BLOCKED")
    _write_report(tmp_path, "4B436629D_replay_backtest_walkforward_gate_decision_20260619T202505Z.json", contract="4B.4.3.6.6.29D", decision="REPLAY_BACKTEST_WALKFORWARD_GATE_READY_LIVE_REAL_STILL_BLOCKED")

    evidence = load_production_hardening_evidence(tmp_path)
    assert evidence["29A"].ok is True
    assert evidence["29A-H1"].ok is True
    snapshot = build_consolidated_readiness_snapshot(tmp_path)
    assert snapshot["evidence_complete"] is True
    assert snapshot["approved_for_paper_candidate_preflight"] is True
    assert snapshot["approved_for_paper_candidate"] is False
    assert snapshot["approved_for_live_real"] is False
