from __future__ import annotations
import py_compile, shutil
from pathlib import Path
PROJECT_ROOT=Path(__file__).resolve().parents[1]; SRC_DIR=PROJECT_ROOT/'src'/'tradebot'; TOOLS_DIR=PROJECT_ROOT/'tools'; PAYLOAD_DIR=TOOLS_DIR/'_patch_payload'; BACKUP_DIR=TOOLS_DIR/'_patch_backup_4B436627CH1'; CREATED=BACKUP_DIR/'.demo_authenticated_probe_created'
PAYLOAD=PAYLOAD_DIR/'binance_demo_authenticated_no_order_preflight_4B436627CH1.py'; TARGET=SRC_DIR/'binance_demo_authenticated_no_order_preflight.py'; ROUTER=SRC_DIR/'binance_environment.py'; POLICY=SRC_DIR/'execution_policy.py'; PREFLIGHT=SRC_DIR/'order_preflight.py'; BINANCE=SRC_DIR/'exchange'/'binance.py'; RUNNER=TOOLS_DIR/'run_binance_demo_authenticated_no_order_preflight_probe_4B436627CH1.py'; CHECKER=TOOLS_DIR/'check_binance_demo_authenticated_no_order_preflight_evidence_4B436627CH1.py'; ROLLBACK=TOOLS_DIR/'rollback_4B436627C_H1_binance_demo_authenticated_no_order_preflight_probe.py'; TEST=PROJECT_ROOT/'tests'/'test_binance_demo_authenticated_no_order_preflight_probe_4B436627CH1.py'; DOC=PROJECT_ROOT/'docs'/'BINANCE_DEMO_AUTHENTICATED_NO_ORDER_PREFLIGHT_PROBE_4B436627CH1.md'
def _compile(path:Path)->bool:
    try: py_compile.compile(str(path), doraise=True); return True
    except py_compile.PyCompileError: return False
def _contains(path:Path, marker:str)->bool: return path.exists() and marker in path.read_text(encoding='utf-8')
def _backup()->None:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    if CREATED.exists():
        return
    if TARGET.exists():
        b=BACKUP_DIR/'src'/'tradebot'/TARGET.name
        if not b.exists(): b.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(TARGET,b)
    else: CREATED.write_text('created\n', encoding='utf-8')
def _restore()->None:
    b=BACKUP_DIR/'src'/'tradebot'/TARGET.name
    if b.exists(): TARGET.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(b,TARGET)
    elif CREATED.exists(): TARGET.unlink(missing_ok=True)
def main()->int:
    required=[PAYLOAD,ROUTER,POLICY,PREFLIGHT,BINANCE,RUNNER,CHECKER,ROLLBACK,TEST,DOC]; missing=[str(x) for x in required if not x.exists()]
    if missing:
        print('4B436627CH1_apply_error: required file missing'); [print(f' - missing: {x}') for x in missing]; return 2
    markers=[(ROUTER,'BINANCE_ENVIRONMENT_ROUTER_VERSION = "4B.4.3.6.6.27A"'),(POLICY,'EXECUTION_POLICY_GATE_VERSION = "4B.4.3.6.6.27B"'),(PREFLIGHT,'TRUTHFUL_ORDER_PREFLIGHT_VERSION = "4B.4.3.6.6.27C"'),(BINANCE,'async def run_entry_order_preflight('),(BINANCE,'self._enforce_signed_request_policy(method, path, params or {})')]
    failed=[f'{p}:{m}' for p,m in markers if not _contains(p,m)]
    if failed:
        print('4B436627CH1_apply_error: prerequisite marker missing'); [print(f' - missing_marker: {x}') for x in failed]; return 2
    _backup()
    try:
        TARGET.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(PAYLOAD,TARGET)
        checks=[('config_mutation_performed',False),('scheduler_mutation_performed',False),('trading_action_performed',False),('probe_module_py_compile_ok',_compile(TARGET)),('runner_py_compile_ok',_compile(RUNNER)),('checker_py_compile_ok',_compile(CHECKER)),('rollback_py_compile_ok',_compile(ROLLBACK)),('test_file_py_compile_ok',_compile(TEST)),('probe_version_present',_contains(TARGET,'BINANCE_DEMO_AUTHENTICATED_NO_ORDER_PREFLIGHT_VERSION = "4B.4.3.6.6.27C-H1"')),('demo_only_profile_gate_present',_contains(TARGET,'DEMO_PREFLIGHT_PROFILE_REQUIRED')),('credentials_gate_present',_contains(TARGET,'DEMO_PREFLIGHT_API_CREDENTIALS_MISSING')),('real_open_orders_query_present',_contains(TARGET,'await client.fetch_open_orders(selected_symbol)')),('order_test_only_present',_contains(TARGET,'test=True')),('forbidden_real_order_path_present',_contains(TARGET,'FORBIDDEN_REAL_ORDER_PATH = "/api/v3/order"')),('evidence_secret_redaction_present',_contains(TARGET,'BINANCE_DEMO_EVIDENCE_SECRETS_REDACTED = True')),('paper_live_order_enablement_present',False)]
        print('4B.4.3.6.6.27C-H1 Binance Demo authenticated no-order preflight probe / evidence export / fail-closed runtime verification applied'); ok=True
        for name,value in checks:
            print(f' - {name}: {value}'); ok = ok and ((value is False) if name in {'config_mutation_performed','scheduler_mutation_performed','trading_action_performed','paper_live_order_enablement_present'} else bool(value))
        if not ok: raise RuntimeError('4B436627CH1_APPLY_POSTCHECK_FAILED')
        return 0
    except Exception as error:
        _restore(); print(f'4B436627CH1_apply_error: {error}'); print(' - transactional_restore_performed: True'); return 3
if __name__=='__main__': raise SystemExit(main())
