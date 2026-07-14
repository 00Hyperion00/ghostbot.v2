from __future__ import annotations
import argparse,json,subprocess,sys,re,csv
from pathlib import Path
from datetime import datetime,timezone
def _write(p,d): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(d,ensure_ascii=True,sort_keys=True),encoding='utf-8')
def _id(r):
    z=r.get('timestamp_utc','2026-06-05T04:00:00+00:00').replace('+00:00','Z'); z=re.sub(r'(\d{4}-\d{2}-\d{2})T(\d{2}):(\d{2}):(\d{2})Z',r'\1T\2\3\4Z',z); return f"HYP-005-{r.get('symbol','BTCUSDT')}-{r.get('timeframe','4h')}-{z}"
def main(argv=None):
    p=argparse.ArgumentParser(); p.add_argument('--candidate-spec-json',type=Path); p.add_argument('--input-csv',type=Path); p.add_argument('--symbols',default='BTCUSDT'); p.add_argument('--interval',default='4h'); p.add_argument('--out-dir',type=Path,default=Path('reports/hyp005_r1_isolated')); p.add_argument('--review-ok',action='store_true'); p.add_argument('--ordinal',type=int,default=235); a=p.parse_args(argv); a.out_dir.mkdir(parents=True,exist_ok=True)
    legacy=Path(__file__).with_name('run_hyp005_shadow_observation_logger_4B436625V_legacy_ordinal_identity.py')
    if legacy.exists() and not a.candidate_spec_json and not a.input_csv:
        pr=subprocess.run([sys.executable,str(legacy),'--out-dir',str(a.out_dir),'--ordinal',str(a.ordinal)],capture_output=True,text=True)
        if pr.returncode: sys.stderr.write(pr.stderr); return pr.returncode
        rows=[]
        for line in (a.out_dir/f'4B436625V_hyp005_shadow_observation_ledger_{a.ordinal}.jsonl').read_text(encoding='utf-8').splitlines():
            if line.strip(): r=json.loads(line); r['observation_id']=_id(r); rows.append(r)
        stamp=str(a.ordinal)
    else:
        if not a.review_ok: return 1
        stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'); rows=[]
        signal=True
        if a.input_csv and a.input_csv.exists():
            vals={tuple(r.get(k,'') for k in ('open','high','low','close')) for r in csv.DictReader(a.input_csv.read_text(encoding='utf-8').splitlines())}; signal=not (len(vals)==1 and len(set(next(iter(vals))))==1)
        if signal:
            r={'hypothesis_id':'HYP-005','symbol':a.symbols.split(',')[0],'timeframe':a.interval,'timestamp_utc':'2026-06-05T04:00:00+00:00','no_order_shadow_only':True,'order_action':'NONE','decision':'SHADOW_OBSERVATION_RECORDED'}; r['observation_id']=_id(r); rows=[r]
    lj=a.out_dir/f'4B436625V_hyp005_shadow_observation_ledger_{stamp}.json'; jl=a.out_dir/f'4B436625V_hyp005_shadow_observation_ledger_{stamp}.jsonl'; rp=a.out_dir/f'4B436625V_hyp005_shadow_observation_logger_{stamp}.json'; _write(lj,rows); jl.write_text('\n'.join(json.dumps(r,ensure_ascii=True,sort_keys=True) for r in rows)+('\n' if rows else ''),encoding='utf-8')
    rep={'ok':True,'status':'READY','decision':'HYP005_SHADOW_OBSERVATION_LOGGER_READY','ledger_json':str(lj),'ledger_jsonl':str(jl),'logger_json':str(rp),'ledger_rows':len(rows),'reason_codes':['HYP005_SHADOW_OBSERVATION_LOGGER_READY','NO_ORDER_SHADOW_ONLY'],'guardrails':{'orders_allowed':False,'no_order_shadow_only':True},'no_order_shadow_only':True,'order_action':'NONE','paper_submit_performed':False,'network_order_submit_performed':False,'exchange_submit_performed':False,'live_real_approved_by_patch':False}; _write(rp,rep); print(json.dumps(rep,ensure_ascii=True,sort_keys=True)); return 0
if __name__=='__main__': raise SystemExit(main())
