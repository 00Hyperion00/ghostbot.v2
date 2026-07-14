from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'src'))
from tradebot.full_repo_regression_stabilization_62F import build_phase62f_report
def main(argv=None)->int:
    p=argparse.ArgumentParser(); p.add_argument('--once-json',action='store_true'); p.parse_args(argv); r=build_phase62f_report(ROOT); print(json.dumps(r,ensure_ascii=False,sort_keys=True)); return 0 if r.get('ok') else 2
if __name__=='__main__': raise SystemExit(main())
