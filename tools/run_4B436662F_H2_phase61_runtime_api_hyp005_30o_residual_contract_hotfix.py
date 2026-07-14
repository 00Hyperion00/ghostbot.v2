import argparse,json,sys
from pathlib import Path
sys.path.insert(0,'src')
from tradebot.full_repo_regression_stabilization_62F_H2 import build_phase62f_h2_snapshot
p=argparse.ArgumentParser(); p.add_argument('--reports-dir',default='reports/recovery'); p.add_argument('--once-json',action='store_true'); a=p.parse_args(); payload=build_phase62f_h2_snapshot(); payload['decision']='PHASE61_RUNTIME_API_HYP005_30O_RESIDUAL_CONTRACT_READY_NO_PAPER_SUBMIT_NO_NETWORK_ORDER_NO_LIVE_NO_EXCHANGE_SUBMIT_LOCKED' if payload.get('ok') else 'BLOCKED'; d=Path(a.reports_dir); d.mkdir(parents=True,exist_ok=True); path=d/'4B436662F_H2_phase61_runtime_api_hyp005_30o_residual_ready.json'; path.write_text(json.dumps(payload,ensure_ascii=False,sort_keys=True,indent=2),encoding='utf-8'); payload['report_path']=str(path.resolve()); print(json.dumps(payload,ensure_ascii=False,sort_keys=True)); raise SystemExit(0 if payload.get('ok') else 1)
