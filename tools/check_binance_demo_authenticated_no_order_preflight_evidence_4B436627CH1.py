from __future__ import annotations
import argparse, json, sys
from pathlib import Path
PROJECT_ROOT=Path(__file__).resolve().parents[1]; SRC_DIR=PROJECT_ROOT/'src'
if str(SRC_DIR) not in sys.path: sys.path.insert(0, str(SRC_DIR))
from tradebot.binance_demo_authenticated_no_order_preflight import BINANCE_DEMO_AUTHENTICATED_NO_ORDER_PREFLIGHT_VERSION, validate_demo_probe_evidence

def _latest(directory: Path) -> Path:
    items=sorted(directory.glob('4B436627CH1_binance_demo_authenticated_no_order_preflight_probe_*.json'), key=lambda p:(p.stat().st_mtime_ns,p.name), reverse=True)
    if not items: raise FileNotFoundError('DEMO_PREFLIGHT_EVIDENCE_NOT_FOUND')
    return items[0]
def main() -> int:
    p=argparse.ArgumentParser(description='Read-only Binance Demo authenticated no-order evidence checker'); p.add_argument('--evidence-json', type=Path); p.add_argument('--reports-dir', type=Path, default=Path('reports/execution_safety')); p.add_argument('--once-json', action='store_true'); a=p.parse_args()
    path=a.evidence_json.resolve() if a.evidence_json else _latest(a.reports_dir.resolve()); payload=json.loads(path.read_text(encoding='utf-8')); valid, errors=validate_demo_probe_evidence(payload)
    result={'contractVersion':BINANCE_DEMO_AUTHENTICATED_NO_ORDER_PREFLIGHT_VERSION,'ok':bool(valid and payload.get('ok') is True),'readOnly':True,'evidence_json':str(path),'evidence_reason_code':payload.get('reason_code'),'evidence_ok':payload.get('ok'),'validation_errors':errors,'profile_verified':payload.get('profile_verified'),'open_orders_check_performed':payload.get('open_orders_check_performed'),'open_orders_count':payload.get('open_orders_count'),'order_test_performed':payload.get('order_test_performed'),'order_test_ok':payload.get('order_test_ok'),'real_order_endpoint_used':payload.get('real_order_endpoint_used'),'trading_action_performed':payload.get('trading_action_performed'),'config_mutation_performed':False,'scheduler_mutation_performed':False}
    print(json.dumps(result, ensure_ascii=False, indent=2)); return 0 if result['ok'] else 1
if __name__ == '__main__': raise SystemExit(main())
