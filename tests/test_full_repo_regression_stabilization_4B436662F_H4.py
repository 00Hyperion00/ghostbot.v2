from __future__ import annotations

import py_compile


def test_62f_h4_hyp006_syntax_repair_and_script_markers() -> None:
    py_compile.compile("src/tradebot/hyp006_shadow_registration_operator_approval.py", doraise=True)
    from tradebot.hyp006_shadow_registration_operator_approval import build_registration_script

    script = build_registration_script(symbols=["ADAUSDT"])
    assert "$Python = (Get-Command python -ErrorAction Stop).Source" in script
    assert "$env:PYTHONPATH = 'src'" in script
    assert "--registration-approval-json" in script
    assert "--registration-json" in script
    assert "hyp006_scheduler_stdout.log" in script
    assert "hyp006_scheduler_stderr.log" in script
