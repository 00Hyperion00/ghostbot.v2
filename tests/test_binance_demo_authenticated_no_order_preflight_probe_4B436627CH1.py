from __future__ import annotations
import asyncio, json, subprocess, sys
from pathlib import Path
import pytest
from tradebot.binance_demo_authenticated_no_order_preflight import *
from tradebot.config import Settings
from tradebot.enums import ExecutionMode, MarketType
from tradebot.models import SymbolRules

def settings(**kw):
    d=dict(market_type='spot_demo',base_url='https://demo-api.binance.com',execution_mode='live_demo',api_key='demo-key-not-exported',api_secret='demo-secret-not-exported',symbol='ETHUSDT',kline_interval='1m'); d.update(kw); return Settings(**d)
def rules(): return SymbolRules(symbol='ETHUSDT',base_asset='ETH',quote_asset='USDT',tick_size=0.01,step_size=0.0001,min_qty=0.0001,max_qty=1000.0,min_notional=10.0,price_precision=2,quantity_precision=4)
class Fake:
    def __init__(self,s,open_orders=None,fail=False): self.settings=s; self.open_orders=list(open_orders or []); self.fail=fail; self.events=[]; self.closed=False
    async def close(self): self.closed=True; self.events.append("close")
    async def sync_server_time(self): self.events.append("GET:/api/v3/time"); return {"serverTime":1}
    async def fetch_symbol_rules(self,symbol=None): self.events.append("GET:/api/v3/exchangeInfo"); return rules()
    async def public_test(self): self.events.append("GET:/api/v3/ticker/price"); return {"price":"3500.12"}
    async def fetch_open_orders(self,symbol=None): self.events.append("GET:/api/v3/openOrders"); return list(self.open_orders)
    async def create_limit_order(self,**kw):
        self.events.append("POST:/api/v3/order/test")
        assert kw["test"] is True and kw["side"]=="BUY"
        if self.fail: raise RuntimeError("order-test rejected")
        return {}
def run(c): return asyncio.run(c)
def test_contract():
    assert BINANCE_DEMO_AUTHENTICATED_NO_ORDER_PREFLIGHT_VERSION=='4B.4.3.6.6.27C-H1'; assert BINANCE_DEMO_AUTHENTICATED_NO_ORDER_ONLY and BINANCE_DEMO_AUTHENTICATED_FAIL_CLOSED and BINANCE_DEMO_REAL_ORDER_ENDPOINT_FORBIDDEN and BINANCE_DEMO_EVIDENCE_SECRETS_REDACTED
def test_parameters():
    o=build_safe_test_limit_order(symbol='ETHUSDT',ticker_price='3500.12',rules=rules(),requested_notional_usd='15'); assert float(o['price'])*float(o['quantity'])>=10
def test_success_and_redaction(tmp_path):
    box={}
    def fac(s): box['c']=Fake(s); return box['c']
    e=run(run_demo_authenticated_no_order_probe(settings(),client_factory=fac)); assert e.ok and not e.real_order_endpoint_used and not e.trading_action_performed; assert [x.path for x in e.network_requests]==['/api/v3/time','/api/v3/exchangeInfo','/api/v3/ticker/price','/api/v3/openOrders','/api/v3/order/test']; p=write_evidence_json(tmp_path/'e.json',e); t=p.read_text(); assert 'demo-key-not-exported' not in t and 'demo-secret-not-exported' not in t; assert validate_demo_probe_evidence(json.loads(t))[0]
def test_profile_gate_before_client():
    called=[]
    with pytest.raises(DemoAuthenticatedProbeError) as ex: run(run_demo_authenticated_no_order_probe(settings(market_type='spot_mainnet',base_url='https://api.binance.com'),client_factory=lambda s: called.append(1)))
    assert ex.value.code=='DEMO_PREFLIGHT_PROFILE_REQUIRED' and not called
def test_credentials_gate_before_client():
    called=[]
    with pytest.raises(DemoAuthenticatedProbeError) as ex: run(run_demo_authenticated_no_order_probe(settings(api_key='',api_secret=''),client_factory=lambda s: called.append(1)))
    assert ex.value.code=='DEMO_PREFLIGHT_API_CREDENTIALS_MISSING' and not called
def test_symbol_override_blocked():
    called=[]
    with pytest.raises(DemoAuthenticatedProbeError) as ex: run(run_demo_authenticated_no_order_probe(settings(),symbol='BTCUSDT',client_factory=lambda s: called.append(1)))
    assert ex.value.code=='DEMO_PREFLIGHT_SYMBOL_OVERRIDE_NOT_ALLOWED' and not called
def test_open_orders_blocks_test():
    box={}
    def fac(s): box['c']=Fake(s,[{'id':1}]); return box['c']
    with pytest.raises(DemoAuthenticatedProbeError) as ex: run(run_demo_authenticated_no_order_probe(settings(),client_factory=fac))
    assert ex.value.code=='DEMO_PREFLIGHT_EXISTING_OPEN_ORDERS_BLOCKED'; assert 'POST:/api/v3/order/test' not in box['c'].events
def test_order_test_failure():
    box={}
    def fac(s): box['c']=Fake(s,fail=True); return box['c']
    with pytest.raises(DemoAuthenticatedProbeError) as ex: run(run_demo_authenticated_no_order_probe(settings(),client_factory=fac))
    assert ex.value.code=='DEMO_PREFLIGHT_ORDER_TEST_FAILED' and ex.value.evidence.order_test_ok is False and box['c'].closed
def test_checker_accepts_and_rejects(tmp_path):
    root=Path(__file__).resolve().parents[1]; checker=root/'tools/check_binance_demo_authenticated_no_order_preflight_evidence_4B436627CH1.py'; e=run(run_demo_authenticated_no_order_probe(settings(),client_factory=lambda s:Fake(s))); good=write_evidence_json(tmp_path/'good.json',e); r=subprocess.run([sys.executable,str(checker),'--evidence-json',str(good),'--once-json'],cwd=root,text=True,capture_output=True); assert r.returncode==0
    p=json.loads(good.read_text()); p['network_requests'].append({'method':'POST','path':'/api/v3/order','purpose':'unsafe'}); p['real_order_endpoint_used']=True; bad=tmp_path/'bad.json'; bad.write_text(json.dumps(p)); r=subprocess.run([sys.executable,str(checker),'--evidence-json',str(bad),'--once-json'],cwd=root,text=True,capture_output=True); assert r.returncode==1
def test_runner_requires_flags(tmp_path):
    root=Path(__file__).resolve().parents[1]; cfg=tmp_path/'c.yaml'; cfg.write_text('market_type: spot_demo\nbase_url: https://demo-api.binance.com\nexecution_mode: live_demo\napi_key: x\napi_secret: y\nsymbol: ETHUSDT\n'); r=subprocess.run([sys.executable,str(root/'tools/run_binance_demo_authenticated_no_order_preflight_probe_4B436627CH1.py'),'--config',str(cfg),'--out-dir',str(tmp_path),'--once-json'],cwd=root,text=True,capture_output=True); assert r.returncode==2; assert json.loads(r.stdout)['reason_code']=='DEMO_PREFLIGHT_EXPLICIT_OPERATOR_APPROVAL_REQUIRED'
def test_secret_field_detected():
    p=run(run_demo_authenticated_no_order_probe(settings(),client_factory=lambda s:Fake(s))).to_dict(); p['api_secret']='bad'; valid,errs=validate_demo_probe_evidence(p); assert not valid and 'DEMO_PREFLIGHT_SECRET_MATERIAL_DETECTED' in errs
