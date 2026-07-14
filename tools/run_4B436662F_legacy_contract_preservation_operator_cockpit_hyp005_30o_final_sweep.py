from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'src'))
from tradebot.full_repo_regression_stabilization_62F import build_phase62f_report
def main(argv=None)->int:
    p=argparse.ArgumentParser(); p.add_argument('--reports-dir',default='reports/recovery'); p.add_argument('--once-json',action='store_true'); a=p.parse_args(argv); r=build_phase62f_report(ROOT); out=ROOT/a.reports_dir; out.mkdir(parents=True,exist_ok=True); path=out/('4B436662F_legacy_contract_preservation_final_sweep_'+('ready' if r.get('ok') else 'blocked')+'.json'); r['report_path']=str(path); path.write_text(json.dumps(r,ensure_ascii=False,indent=2,sort_keys=True),encoding='utf-8'); print(json.dumps(r,ensure_ascii=False,sort_keys=True)); return 0 if r.get('ok') else 2
if __name__=='__main__': raise SystemExit(main())
