from __future__ import annotations
import json, os, py_compile, shutil, subprocess, sys
from pathlib import Path
CONTRACT_VERSION='4B.4.3.6.6.30O-H4'
PAYLOAD=Path('_patch_payload')/CONTRACT_VERSION
ARTIFACT_DIRS=['_patch_payload','tools/_patch_payload','_patch_backup','tools/_patch_backup','tests/_patch_backup','docs/_patch_backup']
def repo_root()->Path:
    s=Path.cwd().resolve()
    for p in [s,*s.parents]:
        if (p/'src/tradebot').is_dir() and (p/'tools').is_dir(): return p
    return s
def copy_payload(root:Path)->dict[str,bool]:
    src=root/PAYLOAD
    if not src.exists(): raise FileNotFoundError(f'payload missing: {src}')
    out={}
    for f in src.rglob('*'):
        if f.is_file() and '__pycache__' not in f.parts and not f.name.endswith(('.pyc','.pyo')):
            rel=f.relative_to(src); dst=root/rel; dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(f,dst); out[rel.as_posix()]=dst.exists()
    return out
def remove_artifacts(root:Path)->dict[str,bool]:
    out={}
    for rel in ARTIFACT_DIRS:
        p=root/rel
        if p.exists(): shutil.rmtree(p,ignore_errors=True)
        out[rel]=not p.exists()
    return out
def compile_py(root:Path)->dict[str,dict[str,str|bool]]:
    out={}
    for p in list((root/'tools').glob('check_4B436630O*.py'))+list((root/'tools').glob('run_4B436630O*.py'))+list((root/'tools').glob('apply_4B436630O_H4*.py'))+list((root/'tests').glob('test_paper_sandbox_execution_reconciliation_gate_4B436630O_H4.py')):
        try: py_compile.compile(str(p),doraise=True); out[str(p.relative_to(root))]={'ok':True,'error':''}
        except Exception as e: out[str(p.relative_to(root))]={'ok':False,'error':str(e)}
    return out
def run_checker(root:Path)->dict:
    env=os.environ.copy(); env['PYTHONPATH']=str(root/'src')
    r=subprocess.run([sys.executable,str(root/'tools/check_4B436630O_H4_reconciliation_sqlite_mirror_finalize.py'),'--once-json'],cwd=root,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env,timeout=300)
    try: d=json.loads(r.stdout)
    except Exception: d={'ok':False,'stdout_tail':r.stdout[-2000:],'stderr_tail':r.stderr[-2000:]}
    d['returncode']=r.returncode; return d
def main()->int:
    root=repo_root(); copied=copy_payload(root); compiled=compile_py(root); removed=remove_artifacts(root); checker=run_checker(root)
    payload={'ok':bool(checker.get('ok')) and all(v.get('ok') for v in compiled.values()) and all(removed.values()),'contract_version':CONTRACT_VERSION,'copied':copied,'compiled':compiled,'removed_patch_artifacts_before_check':removed,'checker_report':checker,'read_only':True,'exchange_submit_performed':False,'trading_action_performed':False,'order_actions_performed':False,'runtime_overlay_activation_performed':False,'scheduler_mutation_performed':False,'strategy_parameter_mutation_performed':False,'training_performed':False,'reload_performed':False,'hyp006_strategy_threshold_mutation_performed':False}
    print(json.dumps(payload,ensure_ascii=False,indent=2,sort_keys=True)); print('4B.4.3.6.6.30O-H4 reconciliation sqlite mirror finalize applied')
    for k in ('target_30o_checker_ok','h1_checker_ok','h2_checker_ok','h3_checker_ok','target_sqlite_mirror_ok','target_exchange_submit_blocked','target_live_real_blocked'): print(f' - {k}: {checker.get("checks",{}).get(k)}')
    return 0 if payload['ok'] else 2
if __name__=='__main__': raise SystemExit(main())
