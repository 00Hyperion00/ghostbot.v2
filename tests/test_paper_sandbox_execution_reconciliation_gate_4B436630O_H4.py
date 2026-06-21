from __future__ import annotations
import json, os, subprocess, sys
from pathlib import Path
from typing import Any

def repo_root()->Path:
    s=Path.cwd().resolve()
    for p in [s,*s.parents]:
        if (p/'src/tradebot').is_dir() and (p/'tools').is_dir(): return p
    return s

def run_json(rel:str)->dict[str,Any]:
    root=repo_root(); env=os.environ.copy(); env['PYTHONPATH']=str(root/'src')
    r=subprocess.run([sys.executable,str(root/rel),'--once-json'],cwd=root,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env,timeout=300)
    assert r.returncode==0, r.stdout[-4000:]+r.stderr[-4000:]
    payload=json.loads(r.stdout)
    assert payload.get('ok') is True, json.dumps(payload.get('checks',{}),indent=2,sort_keys=True)
    return payload

def test_30o_h4_checker_ok()->None:
    payload=run_json('tools/check_4B436630O_H4_reconciliation_sqlite_mirror_finalize.py')
    assert payload['checks']['target_30o_checker_ok'] is True
    assert payload['checks']['target_sqlite_mirror_ok'] is True

def test_30o_h4_legacy_hotfix_checkers_now_ok()->None:
    assert run_json('tools/check_4B436630O_H1_reconciliation_checker_baseline_compat.py')['ok'] is True
    assert run_json('tools/check_4B436630O_H2_reconciliation_checker_probe_signature_hotfix.py')['ok'] is True
    assert run_json('tools/check_4B436630O_H3_reconciliation_checker_ledger_event_signature_hotfix.py')['ok'] is True

def test_30o_h4_keeps_no_exchange_submit_no_live_real()->None:
    payload=run_json('tools/check_4B436630O_paper_sandbox_execution_reconciliation_gate.py')
    checks=payload['checks']
    assert checks['exchange_submit_still_blocked'] is True
    assert checks['live_real_still_blocked'] is True
    assert payload['exchange_submit_performed'] is False
    assert payload['trading_action_performed'] is False
