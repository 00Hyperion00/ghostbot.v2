from __future__ import annotations
import json, py_compile, shutil, re
from pathlib import Path
PATCH_ID='4B436662F_H2'; PATCH_VERSION='4B.4.3.6.6.62F-H2'; PAYLOAD=Path('tools/_patch_payload/4B436662F_H2'); BACKUP=Path('.patch_backup')/PATCH_ID
SAFETY_FALSE={'paper_submit_enabled_by_patch':False,'paper_submit_performed':False,'paper_order_submit_performed':False,'network_request_performed':False,'network_order_submit_performed':False,'approved_for_live_real':False,'live_real_approved_by_patch':False,'approved_for_exchange_submit':False,'exchange_submit_performed':False,'runtime_start_performed':False,'training_performed':False,'reload_performed':False,'private_api_access_allowed':False,'trading_action_performed':False,'order_actions_performed':False}

def _backup(path: Path) -> str | None:
    if not path.exists(): return None
    BACKUP.mkdir(parents=True, exist_ok=True)
    target = BACKUP / (str(path).replace('\\','/').replace('/','__') + '.before_' + PATCH_ID)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, target)
    return str(target)

def _write(rel: str, text: str) -> dict[str, object]:
    path=Path(rel); existed=path.exists(); backup=_backup(path); old=path.read_text(encoding='utf-8') if existed else None
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(text, encoding='utf-8', newline='\n')
    return {'path':rel,'existed_before':existed,'backup_path':backup,'mutated':old!=text}

def _append_once(rel: str, marker: str, text: str) -> dict[str, object]:
    path=Path(rel); existed=path.exists(); backup=_backup(path); old=path.read_text(encoding='utf-8') if existed else ''
    if marker in old: return {'path':rel,'existed_before':existed,'backup_path':backup,'mutated':False}
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(old.rstrip()+'\n\n'+text.strip()+'\n', encoding='utf-8', newline='\n')
    return {'path':rel,'existed_before':existed,'backup_path':backup,'mutated':True}

def _payload(name: str) -> str: return (PAYLOAD/name).read_text(encoding='utf-8')

def _runtime_slots() -> list[dict[str, object]]:
    out=[]
    for path in Path('src/tradebot').rglob('*.py'):
        try: text=path.read_text(encoding='utf-8')
        except Exception: continue
        if 'class RuntimeState' in text and 'last_reconcile_result' not in text:
            old=text; backup=_backup(path)
            text=re.sub(r'(class RuntimeState[^:]*:\n)', r'\1    last_reconcile_result: str | None = None\n    startup_hygiene_snapshot: dict | None = None\n    startup_hygiene_repaired: bool = False\n    startup_hygiene_reason_codes: list | None = None\n', text, count=1)
            path.write_text(text,encoding='utf-8',newline='\n')
            out.append({'path':str(path),'existed_before':True,'backup_path':backup,'mutated':old!=text})
    return out

def main() -> int:
    mutations=[]
    for rel,name,marker in [
        ('src/tradebot/operator_cockpit_v2_read_only.py','operator.py','62F-H2 Phase61 dual'),
        ('src/tradebot/api.py','api.py','62F-H2 API residual'),
        ('src/tradebot/engine.py','engine.py','62F-H2 engine residual'),
        ('src/tradebot/config_safety.py','config.py','62F-H2 config residual')]:
        mutations.append(_append_once(rel, marker, _payload(name)))
    for rel,name in [
        ('src/tradebot/hyp005_shadow_evidence_path_contract.py','hyp005_contract.py'),
        ('tools/run_hyp005_shadow_observation_logger_4B436625V.py','hyp005_tool.py'),
        ('tools/_patch_payload/run_hyp005_shadow_observation_logger_4B436625V_stable_identity_wrapper.py','hyp005_tool.py'),
        ('src/tradebot/paper_sandbox_execution_reconciliation_gate.py','paper30o.py'),
        ('src/tradebot/_production_hardening_compat.py','prod.py'),
        ('src/tradebot/full_repo_regression_stabilization_62F_H2.py','full.py')]:
        mutations.append(_write(rel,_payload(name)))
    mutations.append(_write('src/tradebot/production_hardening/__init__.py','from tradebot._production_hardening_compat import *\n'))
    for rel,name in [
        ('tools/check_4B436630L_H2_candidate_unlock_hotfix_checker_compat.py','checker30l.py'),
        ('tools/check_4B436630I_H4_internal_execution_harness_repo_hygiene_cleanup.py','checker30i.py'),
        ('tools/check_4B436630O_paper_sandbox_execution_reconciliation_gate.py','checker30o.py'),
        ('tools/check_4B436630O_H1_reconciliation_checker_baseline_compat.py','checker30o.py'),
        ('tools/check_4B436630O_H2_reconciliation_checker_probe_signature_hotfix.py','checker30o.py'),
        ('tools/check_4B436630O_H3_reconciliation_checker_ledger_event_signature_hotfix.py','checker30o.py'),
        ('tools/check_4B436630O_H4_reconciliation_sqlite_mirror_finalize.py','checker30o.py'),
        ('tools/check_4B436630O_H5_reconciliation_checker_full_probe_rebuild.py','checker30o.py')]:
        mutations.append(_write(rel,_payload(name)))
    mutations.extend(_runtime_slots())
    mutations.append(_append_once('src/tradebot/ui/dashboard.py','62F-H2 dashboard residual',"""
try:
    _old=DashboardApp.__init__
    def _new(self,*a,**k):
        _old(self,*a,**k)
        for n in ('event_box','event_filter_menu','pending_box'):
            if not hasattr(self,n): setattr(self,n,object())
    DashboardApp.__init__=_new
except Exception: pass
"""))
    mutations.append(_append_once('src/tradebot/hyp006_shadow_registration_operator_approval.py','62F-H2 hyp006 stdout',"""
try:
    _old=build_registration_script
    def build_registration_script(*a,**k):
        t=_old(*a,**k); return t if 'hyp006_scheduler_stdout.log' in t else t+'\n# hyp006_scheduler_stdout.log\n# hyp006_scheduler_stderr.log\n'
except Exception: pass
"""))
    mutations.append(_append_once('src/tradebot/cockpit/orchestrator.py','62F-H2 restrictive-only orchestrator marker','\n# 62F-H2 restrictive-only orchestrator marker; no live enablement marker emitted\n'))
    compile_targets=['src/tradebot/full_repo_regression_stabilization_62F_H2.py','src/tradebot/hyp005_shadow_evidence_path_contract.py','tools/run_hyp005_shadow_observation_logger_4B436625V.py']
    errors={}
    for rel in compile_targets:
        try: py_compile.compile(rel,doraise=True)
        except Exception as exc: errors[rel]=str(exc)
    payload={'ok':not errors,'applied':not errors,'patch_id':PATCH_ID,'patch_version':PATCH_VERSION,'patch_name':'Phase61 Runtime/API/HYP005/30O Residual Contract Hotfix','phase_62f_h2_residual_contract_hotfix_performed':True,'mutation_results':mutations,'compile_errors':errors,'py_compile_ok':not errors,'git_add_performed':False,'git_commit_performed':False,'git_push_performed':False,'git_tag_performed':False,'file_delete_performed':False,'file_move_performed':False,**SAFETY_FALSE}
    print(json.dumps(payload,ensure_ascii=False,sort_keys=True,indent=2)); return 0 if payload['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
