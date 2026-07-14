from __future__ import annotations
import json, sys, argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'src'))
from tradebot.full_repo_regression_stabilization_62D import build_phase62d_report
def main(argv=None):
    parser=argparse.ArgumentParser(); parser.add_argument('--reports-dir',default='reports/recovery'); parser.add_argument('--once-json',action='store_true'); args=parser.parse_args(argv); r=build_phase62d_report(ROOT); out=ROOT/args.reports_dir; out.mkdir(parents=True,exist_ok=True); path=out/'4B436662D_full_repo_regression_stabilization_consolidated_residual_sweep_ready.json'; r['report_path']=str(path); path.write_text(json.dumps(r,ensure_ascii=False,indent=2,sort_keys=True),encoding='utf-8'); print(json.dumps(r,ensure_ascii=False,sort_keys=True)); return 0 if r.get('ok') else 2
if __name__=='__main__': raise SystemExit(main())
