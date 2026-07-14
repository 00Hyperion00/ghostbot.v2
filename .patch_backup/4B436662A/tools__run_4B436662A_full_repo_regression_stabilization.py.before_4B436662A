
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[1]; SRC=ROOT/'src'
if str(SRC) not in sys.path: sys.path.insert(0,str(SRC))
from tradebot.full_repo_regression_stabilization_62A import build_phase62a_report
def main(argv=None):
    p=argparse.ArgumentParser(); p.add_argument('--reports-dir',type=Path,default=ROOT/'reports'/'recovery'); p.add_argument('--once-json',action='store_true'); a=p.parse_args(argv); r=build_phase62a_report(ROOT); a.reports_dir.mkdir(parents=True,exist_ok=True); path=a.reports_dir/(f"4B436662A_full_repo_regression_stabilization_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ').lower()}_{'ready' if r.get('ok') else 'blocked'}.json"); r['report_path']=str(path); path.write_text(json.dumps(r,ensure_ascii=False,indent=2,sort_keys=True),encoding='utf-8'); print(json.dumps(r,ensure_ascii=False,sort_keys=True)); return 0 if r.get('ok') else 2
if __name__=='__main__': raise SystemExit(main())
