from __future__ import annotations
import json, sys, argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'src'))
from tradebot.full_repo_regression_stabilization_62D import build_phase62d_report
def main(argv=None):
    parser=argparse.ArgumentParser(); parser.add_argument('--once-json',action='store_true'); parser.parse_args(argv); r=build_phase62d_report(ROOT); print(json.dumps(r,ensure_ascii=False,sort_keys=True)); return 0 if r.get('ok') else 2
if __name__=='__main__': raise SystemExit(main())
