from __future__ import annotations

import json
from pathlib import Path

from tradebot.hyp006_shadow_registration_operator_approval import build_registration_script
from tradebot.hyp006_scheduler_health_verify import (
    PROPOSED_SCHEDULER_TASK_NAME,
    _decode_subprocess_bytes,
    load_json,
    validate_scheduler_task_health,
)


def test_registration_script_uses_unicode_literal_not_json_escape(tmp_path: Path) -> None:
    root = tmp_path / "Masaüstü" / "trade_botV2"
    reports = root / "reports" / "hyp006_r1_canonical"
    approval = reports / "approval.json"
    script = build_registration_script(
        project_root=root,
        approval_json=approval,
        reports_dir=reports,
        symbols=["ADAUSDT", "BTCUSDT"],
    )
    assert "Masaüstü" in script
    assert "\\u00" not in script
    assert "$ProjectRoot = '" in script


def test_registration_script_emits_powershell_wrapper_with_full_contract(tmp_path: Path) -> None:
    root = tmp_path / "trade_botV2"
    reports = root / "reports" / "hyp006_r1_canonical"
    approval = reports / "approval.json"
    script = build_registration_script(
        project_root=root,
        approval_json=approval,
        reports_dir=reports,
        symbols=["ADAUSDT"],
    )
    assert "$Python = (Get-Command python -ErrorAction Stop).Source" in script
    assert "$env:PYTHONPATH = 'src'" in script
    assert "--registration-approval-json" in script
    assert "--registration-json" in script
    assert "hyp006_scheduler_stdout.log" in script
    assert "hyp006_scheduler_stderr.log" in script
    assert "System.Text.UTF8Encoding($false)" in script
    assert "New-ScheduledTaskAction -Execute 'powershell.exe'" in script
    assert "Register-ScheduledTask" in script


def test_scheduler_health_accepts_powershell_wrapper_action() -> None:
    ok, reasons, probe = validate_scheduler_task_health(
        {
            "task_name": PROPOSED_SCHEDULER_TASK_NAME,
            "state": "Ready",
            "last_task_result": 0,
            "number_of_missed_runs": 0,
            "action_execute": "powershell.exe",
            "action_arguments": '-NoProfile -ExecutionPolicy Bypass -File "C:\\trade_botV2\\reports\\hyp006_r1_canonical\\run_hyp006_r1_canonical_shadow_scheduler.ps1"',
            "working_directory": "C:\\trade_botV2",
        }
    )
    assert ok is True
    assert reasons == []
    assert probe["last_task_result"] == 0


def test_scheduler_health_still_rejects_failed_last_task_result() -> None:
    ok, reasons, _ = validate_scheduler_task_health(
        {
            "task_name": PROPOSED_SCHEDULER_TASK_NAME,
            "state": "Ready",
            "last_task_result": 1,
            "number_of_missed_runs": 0,
            "action_execute": "powershell.exe",
            "action_arguments": '-NoProfile -ExecutionPolicy Bypass -File "C:\\trade_botV2\\reports\\hyp006_r1_canonical\\run_hyp006_r1_canonical_shadow_scheduler.ps1"',
            "working_directory": "C:\\trade_botV2",
        }
    )
    assert ok is False
    assert "SCHEDULER_LAST_TASK_RESULT_NOT_ZERO" in reasons


def test_load_json_accepts_utf8_bom(tmp_path: Path) -> None:
    path = tmp_path / "probe.json"
    path.write_bytes(b"\xef\xbb\xbf" + json.dumps({"ok": True}).encode("utf-8"))
    assert load_json(path) == {"ok": True}


def test_subprocess_decode_handles_non_utf8_bytes() -> None:
    text = _decode_subprocess_bytes("Görev hazır".encode("cp1254"))
    assert "Görev" in text
