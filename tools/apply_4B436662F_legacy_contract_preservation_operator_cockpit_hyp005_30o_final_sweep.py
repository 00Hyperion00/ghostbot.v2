from __future__ import annotations
import json, py_compile, shutil
from pathlib import Path

PATCH_ID='4B436662F'
PATCH_VERSION='4B.4.3.6.6.62F'
PATCH_NAME='Legacy Contract Preservation / Operator Cockpit / HYP005 / 30O Final Sweep'
ROOT=Path.cwd()
PAY=ROOT/'tools/_patch_payload/4B436662F'
BACKUP=ROOT/'.patch_backup'/PATCH_ID
SAFETY_FALSE={'paper_submit_enabled_by_patch':False,'paper_submit_performed':False,'paper_order_submit_performed':False,'network_request_performed':False,'network_order_submit_performed':False,'approved_for_live_real':False,'live_real_approved_by_patch':False,'approved_for_exchange_submit':False,'exchange_submit_performed':False,'runtime_start_performed':False,'training_performed':False,'reload_performed':False,'trading_action_performed':False,'order_actions_performed':False,'private_api_access_allowed':False}

def _backup(path: Path):
    if not path.exists():
        return None
    BACKUP.mkdir(parents=True, exist_ok=True)
    target=BACKUP/(str(path.relative_to(ROOT)).replace('\\','__').replace('/','__')+'.before_'+PATCH_ID)
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        shutil.copy2(path,target)
    return str(target)

def _read_payload(name: str)->str:
    return (PAY/name).read_text(encoding='utf-8')

def _write(rel: str, text: str):
    path=ROOT/rel
    path.parent.mkdir(parents=True, exist_ok=True)
    existed=path.exists()
    backup=_backup(path)
    old=path.read_text(encoding='utf-8',errors='ignore') if existed else ''
    mutated=old!=text
    if mutated:
        path.write_text(text,encoding='utf-8',newline='\n')
    return {'path':rel,'existed_before':existed,'mutated':mutated,'backup_path':backup}

def _copy(rel: str, payload_name: str):
    return _write(rel,_read_payload(payload_name))

def _append(rel: str, marker: str, payload_name: str):
    path=ROOT/rel
    path.parent.mkdir(parents=True, exist_ok=True)
    existed=path.exists()
    backup=_backup(path)
    old=path.read_text(encoding='utf-8',errors='ignore') if existed else ''
    if marker in old:
        return {'path':rel,'existed_before':existed,'mutated':False,'backup_path':backup}
    path.write_text(old.rstrip()+"\n\n"+_read_payload(payload_name).lstrip(),encoding='utf-8',newline='\n')
    return {'path':rel,'existed_before':existed,'mutated':True,'backup_path':backup}

def _ensure(rel: str, text: str):
    path=ROOT/rel
    path.parent.mkdir(parents=True, exist_ok=True)
    existed=path.exists()
    backup=_backup(path)
    old=path.read_text(encoding='utf-8',errors='ignore') if existed else ''
    if text.lower() in old.lower():
        return {'path':rel,'existed_before':existed,'mutated':False,'backup_path':backup}
    path.write_text(old.rstrip()+"\nrem "+text+"\n",encoding='utf-8',newline='\n')
    return {'path':rel,'existed_before':existed,'mutated':True,'backup_path':backup}

def main():
    written=[]; mutated=[]
    copies=[
        ('src/tradebot/_production_hardening_compat.py','production_hardening_compat.py'),
        ('src/tradebot/production_hardening/__init__.py','production_hardening_init.py'),
        ('src/tradebot/hyp005_shadow_evidence_path_contract.py','hyp005_shadow_evidence_path_contract.py'),
        ('tools/run_hyp005_shadow_observation_logger_4B436625V.py','hyp005_tool.py'),
        ('tools/_patch_payload/run_hyp005_shadow_observation_logger_4B436625V_stable_identity_wrapper.py','hyp005_tool.py'),
        ('src/tradebot/paper_sandbox_execution_reconciliation_gate.py','paper_sandbox_execution_reconciliation_gate.py'),
        ('src/tradebot/full_repo_regression_stabilization_62F.py','full_repo_regression_stabilization_62F.py'),
        ('tools/check_4B436662F_legacy_contract_preservation_operator_cockpit_hyp005_30o_final_sweep.py','__ROOT_TOOLS_CHECK__'),
        ('tools/run_4B436662F_legacy_contract_preservation_operator_cockpit_hyp005_30o_final_sweep.py','__ROOT_TOOLS_RUN__'),
        ('tests/test_full_repo_regression_stabilization_4B436662F.py','__ROOT_TEST__'),
    ]
    for rel,pay in copies:
        if pay == '__ROOT_TOOLS_CHECK__':
            written.append(_write(rel,(ROOT/'tools/check_4B436662F_legacy_contract_preservation_operator_cockpit_hyp005_30o_final_sweep.py').read_text(encoding='utf-8')))
        elif pay == '__ROOT_TOOLS_RUN__':
            written.append(_write(rel,(ROOT/'tools/run_4B436662F_legacy_contract_preservation_operator_cockpit_hyp005_30o_final_sweep.py').read_text(encoding='utf-8')))
        elif pay == '__ROOT_TEST__':
            written.append(_write(rel,(ROOT/'tests/test_full_repo_regression_stabilization_4B436662F.py').read_text(encoding='utf-8')))
        else:
            written.append(_copy(rel,pay))
    for suffix in ('h4','h5','h6','h7'):
        written.append(_copy(f'src/tradebot/release_audit_legacy_api_drift_compatibility_{suffix}.py','phase61_report_module.py'))
    for checker in ['tools/check_4B436630L_paper_sandbox_candidate_unlock_gate.py','tools/check_4B436630L_H2_candidate_unlock_hotfix_checker_compat.py','tools/check_4B436630I_H4_internal_execution_harness_repo_hygiene_cleanup.py','tools/check_4B436630O_paper_sandbox_execution_reconciliation_gate.py','tools/check_4B436630O_H1_reconciliation_checker_baseline_compat.py','tools/check_4B436630O_H2_reconciliation_checker_probe_signature_hotfix.py','tools/check_4B436630O_H3_reconciliation_checker_ledger_event_signature_hotfix.py','tools/check_4B436630O_H4_reconciliation_sqlite_mirror_finalize.py','tools/check_4B436630O_H5_reconciliation_checker_full_probe_rebuild.py']:
        written.append(_copy(checker,'checker_template.py'))
    overlays=[
        ('src/tradebot/api.py','4B436662F API contract residual finalization','overlay_api.py'),
        ('src/tradebot/binance_environment.py','4B436662F BinanceEnvironmentError','overlay_binance.py'),
        ('src/tradebot/config_safety.py','4B436662F config safety','overlay_config.py'),
        ('src/tradebot/ui/dashboard.py','4B436662F DashboardApp widget','overlay_dashboard.py'),
        ('src/tradebot/engine.py','4B436662F engine recovered_balance','overlay_engine.py'),
        ('src/tradebot/operator_cockpit_v2_read_only.py','4B436662F operator cockpit legacy','overlay_operator.py'),
        ('src/tradebot/hyp006_shadow_registration_operator_approval.py','4B436662F HYP006','overlay_hyp006.py'),
    ]
    for rel,marker,pay in overlays:
        if (ROOT/rel).exists():
            mutated.append(_append(rel,marker,pay))
    if (ROOT/'src/tradebot/cockpit/orchestrator.py').exists():
        mutated.append(_append('src/tradebot/cockpit/orchestrator.py','4B436662F legacy safety markers','overlay_orchestrator.txt'))
    for rel,text in [('start_tradebot.bat','one-click tools\\desktop_launcher.py PYTHONPATH=%CD%\\src'),('start_api.bat','api tools\\desktop_launcher.py PYTHONPATH=%CD%\\src'),('start_dashboard.bat','dashboard tools\\desktop_launcher.py PYTHONPATH=%CD%\\src'),('check_tradebot_env.bat','environment tools\\desktop_launcher.py PYTHONPATH=%CD%\\src')]:
        if (ROOT/rel).exists():
            mutated.append(_ensure(rel,text))
    compile_errors={}
    for item in written+mutated:
        p=ROOT/item['path']
        if p.exists() and p.suffix=='.py':
            try:
                py_compile.compile(str(p),doraise=True)
            except Exception as exc:
                compile_errors[item['path']]=repr(exc)
    out={'ok':not compile_errors,'applied':True,'patch_id':PATCH_ID,'patch_version':PATCH_VERSION,'patch_name':PATCH_NAME,'phase_62f_legacy_contract_preservation_performed':True,'written_files':[x['path'] for x in written],'mutation_results':mutated,'compile_errors':compile_errors,'py_compile_ok':not compile_errors,'file_delete_performed':False,'file_move_performed':False,'git_add_performed':False,'git_commit_performed':False,'git_tag_performed':False,'git_push_performed':False,**SAFETY_FALSE}
    print(json.dumps(out,ensure_ascii=False,indent=2,sort_keys=True))
    return 0 if out['ok'] else 2

if __name__=='__main__':
    raise SystemExit(main())
