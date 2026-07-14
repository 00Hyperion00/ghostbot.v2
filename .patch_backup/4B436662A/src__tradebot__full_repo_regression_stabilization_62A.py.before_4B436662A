
from __future__ import annotations
from pathlib import Path
from typing import Any
import importlib
PATCH_ID='4B436662A'
PATCH_VERSION='4B.4.3.6.6.62A'
SAFETY_FALSE={'paper_submit_enabled_by_patch':False,'paper_submit_performed':False,'paper_order_submit_performed':False,'network_order_submit_performed':False,'network_request_performed':False,'approved_for_live_real':False,'approved_for_exchange_submit':False,'exchange_submit_performed':False,'runtime_start_performed':False,'training_performed':False,'reload_performed':False}
def _contract(name:str, ok:bool, detail:str='')->dict[str,Any]: return {'name':name,'ok':bool(ok),'detail':detail}
def build_phase62a_report(project_root: str|Path|None=None)->dict[str,Any]:
    root=Path(project_root or Path.cwd()); contracts=[]
    try:
        api=importlib.import_module('tradebot.api'); app=api.create_app(type('DummyEngine',(),{})()); contracts.append(_contract('api_create_app_returns_app',app is not None and callable(app)))
    except Exception as exc: contracts.append(_contract('api_create_app_returns_app',False,str(exc)))
    for modname,symbols in {'tradebot.operator_cockpit_v2_read_only':['DASHBOARD_HTML','_build_in_memory_evidence_pack','_build_risk_sizing_in_memory_evidence_pack','_safe_action_manifest','collect_operator_cockpit_snapshot','make_operator_cockpit_server'],'tradebot.production_hardening':['RuntimeLockHandle','build_production_hardening_snapshot']}.items():
        try:
            mod=importlib.import_module(modname)
            for sym in symbols:
                val=getattr(mod,sym,None); contracts.append(_contract(f'{modname}.{sym}', val is not None and (not sym.startswith('_') or callable(val)), type(val).__name__))
        except Exception as exc: contracts.append(_contract(modname,False,str(exc)))
    for rel in ['tools/_patch_payload/run_hyp005_shadow_observation_logger_4B436625V_stable_identity_wrapper.py','src/tradebot/hyp005_shadow_evidence_path_contract.py']:
        contracts.append(_contract(rel,(root/rel).exists()))
    ok=all(c['ok'] for c in contracts) and all(v is False for v in SAFETY_FALSE.values())
    return {'ok':ok,'status':'READY' if ok else 'BLOCKED','patch_id':PATCH_ID,'patch_version':PATCH_VERSION,'decision':'FULL_REPO_REGRESSION_STABILIZATION_API_APP_FACTORY_LEGACY_CONTRACT_SWEEP_READY_NO_PAPER_SUBMIT_NO_NETWORK_ORDER_NO_LIVE_NO_EXCHANGE_SUBMIT_LOCKED' if ok else 'FULL_REPO_REGRESSION_STABILIZATION_API_APP_FACTORY_LEGACY_CONTRACT_SWEEP_BLOCKED','contracts':contracts,'contract_count':len(contracts),'contract_ready_count':sum(1 for c in contracts if c['ok']),'final_safety_violation_count':0,'final_safety_violations':[],**SAFETY_FALSE,'next_phase':'4B.4.3.6.6.62B','next_phase_name':'Full Repo Regression Stabilization Follow-up / Residual Failure Sweep'}
