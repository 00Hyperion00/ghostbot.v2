from __future__ import annotations
from typing import Any
SAFETY_FALSE={'paper_submit_enabled_by_patch':False,'paper_submit_performed':False,'paper_order_submit_performed':False,'network_request_performed':False,'network_order_submit_performed':False,'approved_for_live_real':False,'live_real_approved_by_patch':False,'approved_for_exchange_submit':False,'exchange_submit_performed':False,'runtime_start_performed':False,'training_performed':False,'reload_performed':False,'trading_action_performed':False,'private_api_access_allowed':False}
def build_phase62f_report(project_root=None)->dict[str,Any]:
    contracts=[]
    def add(n,o,d=''): contracts.append({'name':n,'ok':bool(o),'detail':d})
    try:
        from tradebot.release_audit_legacy_api_drift_compatibility_h7 import build_phase61_h7_report
        r=build_phase61_h7_report(project_root); add('phase61_h7_runtime_lock_export_present',r.get('runtime_lock_handle_export_present') is True)
    except Exception as e: add('phase61_h7_runtime_lock_export_present',False,repr(e))
    try:
        from tradebot.operator_cockpit_v2_read_only import DASHBOARD_HTML, collect_operator_cockpit_snapshot, _build_in_memory_evidence_pack
        s=collect_operator_cockpit_snapshot(project_root or '.'); add('operator_cockpit_26a_27g_snapshot_keys',all(k in s for k in ('mode','audit','safe_operator_actions','visualization_pack_version','risk_sizing_runtime_telemetry'))); add('operator_cockpit_evidence_pack_bytes',isinstance(_build_in_memory_evidence_pack(project_root or '.'),(bytes,bytearray))); add('operator_cockpit_dashboard_markers','Operator Cockpit V2' in DASHBOARD_HTML and 'Risk-Sizing Evidence ZIP İndir' in DASHBOARD_HTML)
    except Exception as e: add('operator_cockpit_contracts',False,repr(e))
    try:
        from tradebot.config_safety import build_config_safety_snapshot
        c=build_config_safety_snapshot(None); add('config_safety_safe_to_trade_contract',c.get('contract_version')=='4B.4.3.6.6.15' and 'safe_to_trade' in c)
    except Exception as e: add('config_safety_safe_to_trade_contract',False,repr(e))
    ready=sum(1 for c in contracts if c['ok']); ok=ready==len(contracts)
    return {'ok':ok,'status':'READY' if ok else 'BLOCKED','patch_id':'4B436662F','patch_version':'4B.4.3.6.6.62F','decision':'LEGACY_CONTRACT_PRESERVATION_OPERATOR_COCKPIT_HYP005_30O_FINAL_SWEEP_READY_NO_PAPER_SUBMIT_NO_NETWORK_ORDER_NO_LIVE_NO_EXCHANGE_SUBMIT_LOCKED' if ok else 'LEGACY_CONTRACT_PRESERVATION_OPERATOR_COCKPIT_HYP005_30O_FINAL_SWEEP_BLOCKED','contract_count':len(contracts),'contract_ready_count':ready,'contracts':contracts,'final_safety_violation_count':0 if ok else len(contracts)-ready,'final_safety_violations':[c for c in contracts if not c['ok']],**SAFETY_FALSE}
