
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; SRC=ROOT/'src'
if str(SRC) not in sys.path: sys.path.insert(0,str(SRC))
from tradebot.full_repo_regression_stabilization_62A import build_phase62a_report
def main(argv=None):
    p=argparse.ArgumentParser(); p.add_argument('--once-json',action='store_true'); p.parse_args(argv); r=build_phase62a_report(ROOT); print(json.dumps(r,ensure_ascii=False,sort_keys=True)); return 0 if r.get('ok') else 2
if __name__=='__main__': raise SystemExit(main())
