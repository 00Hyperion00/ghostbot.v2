import json,sys
sys.path.insert(0,'src')
from tradebot.full_repo_regression_stabilization_62F_H2 import build_phase62f_h2_snapshot
p=build_phase62f_h2_snapshot(); p['decision']='PHASE61_RUNTIME_API_HYP005_30O_RESIDUAL_CONTRACT_READY_NO_PAPER_SUBMIT_NO_NETWORK_ORDER_NO_LIVE_NO_EXCHANGE_SUBMIT_LOCKED' if p.get('ok') else 'BLOCKED'; print(json.dumps(p,ensure_ascii=False,sort_keys=True)); raise SystemExit(0 if p.get('ok') else 1)
