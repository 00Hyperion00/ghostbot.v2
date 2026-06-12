from __future__ import annotations
import argparse, asyncio, json, sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path: sys.path.insert(0, str(SRC_DIR))
from tradebot.binance_demo_authenticated_no_order_preflight import (BINANCE_DEMO_AUTHENTICATED_NO_ORDER_PREFLIGHT_VERSION, DemoAuthenticatedProbeError, DemoProbeEvidence, run_demo_authenticated_no_order_probe, utc_artifact_stamp, utc_now_text, write_evidence_json)
from tradebot.config import Settings
from tradebot.exchange.binance import BinanceSpotClient

def _failure(settings: Settings, symbol: str, code: str, message: str) -> DemoProbeEvidence:
    return DemoProbeEvidence(ok=False, reason_code=code, message=message, generated_at_utc=utc_now_text(), market_type=str(settings.market_type), execution_mode=str(settings.execution_mode), configured_rest_base_url=str(settings.base_url).rstrip('/'), symbol=symbol.upper(), api_key_present=bool(settings.api_key), api_secret_present=bool(settings.api_secret))
def _emit(payload: dict[str, object], once_json: bool) -> None:
    if once_json: print(json.dumps(payload, ensure_ascii=False, indent=2)); return
    print(f"{BINANCE_DEMO_AUTHENTICATED_NO_ORDER_PREFLIGHT_VERSION} Binance Demo authenticated no-order preflight probe")
    for key, value in payload.items(): print(f" - {key}: {value}")
def main() -> int:
    p=argparse.ArgumentParser(description='Authenticated Binance Demo no-order preflight probe')
    p.add_argument('--config', type=Path, default=Path('config.local.yaml')); p.add_argument('--out-dir', type=Path, default=Path('reports/execution_safety'))
    p.add_argument('--symbol'); p.add_argument('--probe-notional-usd', default='15'); p.add_argument('--allow-authenticated-demo-network-probe', action='store_true'); p.add_argument('--review-ok', action='store_true'); p.add_argument('--once-json', action='store_true')
    a=p.parse_args(); settings=Settings.from_yaml(a.config); symbol=str(a.symbol or settings.symbol).upper()
    if not a.allow_authenticated_demo_network_probe or not a.review_ok:
        evidence=_failure(settings, symbol, 'DEMO_PREFLIGHT_EXPLICIT_OPERATOR_APPROVAL_REQUIRED', 'Pass --allow-authenticated-demo-network-probe and --review-ok to run authenticated demo no-order probe'); code=2
    else:
        try: evidence=asyncio.run(run_demo_authenticated_no_order_probe(settings, client_factory=BinanceSpotClient, symbol=symbol, requested_notional_usd=a.probe_notional_usd)); code=0
        except DemoAuthenticatedProbeError as error: evidence=error.evidence; code=1
    path=a.out_dir / f"4B436627CH1_binance_demo_authenticated_no_order_preflight_probe_{utc_artifact_stamp()}.json"; write_evidence_json(path, evidence)
    payload=evidence.to_dict(); payload['evidence_json']=str(path.resolve()); _emit(payload, a.once_json); return code
if __name__ == '__main__': raise SystemExit(main())
