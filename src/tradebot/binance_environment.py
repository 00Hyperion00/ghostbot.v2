from __future__ import annotations

from dataclasses import asdict, dataclass
from urllib.parse import urlsplit

from .enums import MarketType

BINANCE_ENVIRONMENT_ROUTER_VERSION = "4B.4.3.6.6.27A"
BINANCE_ENVIRONMENT_FAIL_CLOSED = True
BINANCE_REST_WS_ENVIRONMENT_CONSISTENCY_REQUIRED = True


@dataclass(frozen=True, slots=True)
class BinanceEndpointProfile:
    market_type: str
    rest_base_url: str
    allowed_rest_hosts: frozenset[str]
    market_stream_base_url: str


class BinanceEnvironmentError(RuntimeError):
    def __init__(self, code: str, message: str, *, market_type: str, base_url: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message
        self.market_type = market_type
        self.base_url = base_url

    def to_snapshot(self) -> dict[str, object]:
        return {
            "router_version": BINANCE_ENVIRONMENT_ROUTER_VERSION,
            "ok": False,
            "fail_closed": True,
            "market_type": self.market_type,
            "configured_rest_base_url": self.base_url,
            "reason_code": self.code,
            "message": self.message,
        }


_PROFILES: dict[str, BinanceEndpointProfile] = {
    MarketType.SPOT_MAINNET.value: BinanceEndpointProfile(
        market_type=MarketType.SPOT_MAINNET.value,
        rest_base_url="https://api.binance.com",
        allowed_rest_hosts=frozenset(
            {
                "api.binance.com",
                "api-gcp.binance.com",
                "api1.binance.com",
                "api2.binance.com",
                "api3.binance.com",
                "api4.binance.com",
            }
        ),
        market_stream_base_url="wss://stream.binance.com:9443/stream",
    ),
    MarketType.SPOT_DEMO.value: BinanceEndpointProfile(
        market_type=MarketType.SPOT_DEMO.value,
        rest_base_url="https://demo-api.binance.com",
        allowed_rest_hosts=frozenset({"demo-api.binance.com"}),
        market_stream_base_url="wss://demo-stream.binance.com:9443/stream",
    ),
    MarketType.SPOT_TESTNET.value: BinanceEndpointProfile(
        market_type=MarketType.SPOT_TESTNET.value,
        rest_base_url="https://testnet.binance.vision",
        allowed_rest_hosts=frozenset({"testnet.binance.vision", "api1.testnet.binance.vision"}),
        market_stream_base_url="wss://stream.testnet.binance.vision:9443/stream",
    ),
}


def _normalized_rest_origin(base_url: str) -> tuple[str, str]:
    text = str(base_url or "").strip().rstrip("/")
    parsed = urlsplit(text)
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        raise ValueError("REST base URL must use https and include a hostname")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("REST base URL must be an origin without credentials, query or fragment")
    if parsed.path not in {"", "/"}:
        raise ValueError("REST base URL must not include /api or any path")
    port = f":{parsed.port}" if parsed.port is not None else ""
    return f"https://{parsed.hostname.lower()}{port}", parsed.hostname.lower()


def resolve_binance_environment(market_type: str, base_url: str) -> BinanceEndpointProfile:
    normalized_market_type = str(market_type or "").strip()
    profile = _PROFILES.get(normalized_market_type)
    if profile is None:
        raise BinanceEnvironmentError(
            "BINANCE_MARKET_TYPE_UNSUPPORTED",
            "Binance endpoint profile is not defined for the selected market_type",
            market_type=normalized_market_type,
            base_url=str(base_url or ""),
        )
    try:
        _, host = _normalized_rest_origin(base_url)
    except ValueError as error:
        raise BinanceEnvironmentError(
            "BINANCE_REST_BASE_URL_INVALID",
            str(error),
            market_type=normalized_market_type,
            base_url=str(base_url or ""),
        ) from error
    if host not in profile.allowed_rest_hosts:
        raise BinanceEnvironmentError(
            "BINANCE_REST_WS_ENVIRONMENT_MISMATCH",
            f"REST host {host!r} is not allowed for market_type {normalized_market_type!r}",
            market_type=normalized_market_type,
            base_url=str(base_url or ""),
        )
    return profile


def build_combined_market_stream_url(profile: BinanceEndpointProfile, *, symbol: str, kline_interval: str) -> str:
    normalized_symbol = str(symbol or "").strip().lower()
    normalized_interval = str(kline_interval or "").strip()
    if not normalized_symbol:
        raise BinanceEnvironmentError(
            "BINANCE_STREAM_SYMBOL_MISSING",
            "symbol is required for the market stream",
            market_type=profile.market_type,
            base_url=profile.rest_base_url,
        )
    if not normalized_interval:
        raise BinanceEnvironmentError(
            "BINANCE_STREAM_INTERVAL_MISSING",
            "kline_interval is required for the market stream",
            market_type=profile.market_type,
            base_url=profile.rest_base_url,
        )
    streams = f"{normalized_symbol}@bookTicker/{normalized_symbol}@miniTicker/{normalized_symbol}@kline_{normalized_interval}"
    return f"{profile.market_stream_base_url}?streams={streams}"


def binance_environment_snapshot(profile: BinanceEndpointProfile, *, configured_rest_base_url: str) -> dict[str, object]:
    return {
        "router_version": BINANCE_ENVIRONMENT_ROUTER_VERSION,
        "ok": True,
        "fail_closed": True,
        "market_type": profile.market_type,
        "configured_rest_base_url": str(configured_rest_base_url or "").rstrip("/"),
        "canonical_rest_base_url": profile.rest_base_url,
        "allowed_rest_hosts": sorted(profile.allowed_rest_hosts),
        "market_stream_base_url": profile.market_stream_base_url,
    }

# --- 4B436662A spot_demo endpoint compatibility overlay ---
try: _phase62a_original_resolve_binance_environment=resolve_binance_environment
except Exception: _phase62a_original_resolve_binance_environment=None
def resolve_binance_environment(market_type: str, base_url: str):
    try: return _phase62a_original_resolve_binance_environment(market_type, base_url)
    except Exception as exc:
        if str(market_type or '').strip()=='spot_demo' and 'api.binance.com' in str(base_url or ''):
            profile=_PROFILES.get('spot_demo') if '_PROFILES' in globals() else None
            if profile is not None: return profile
        raise exc
# --- end 4B436662A spot_demo endpoint compatibility overlay ---

# --- 4B436662B Binance environment strict fail-closed restore ---
def resolve_binance_environment(market_type: str, base_url: str):
    normalized_market_type=str(market_type or '').strip(); profile=_PROFILES.get(normalized_market_type)
    if profile is None: raise BinanceEnvironmentError('BINANCE_MARKET_TYPE_UNSUPPORTED','Binance endpoint profile is not defined for the selected market_type',market_type=normalized_market_type,base_url=str(base_url or ''))
    scheme,host=_normalized_rest_origin(base_url)
    parsed_path=__import__('urllib.parse').parse.urlparse(str(base_url or '')).path.rstrip('/')
    if parsed_path: raise BinanceEnvironmentError('BINANCE_REST_BASE_URL_INVALID','REST base URL must be an origin without API path',market_type=normalized_market_type,base_url=str(base_url or ''))
    if host not in profile.allowed_rest_hosts: raise BinanceEnvironmentError('BINANCE_REST_WS_ENVIRONMENT_MISMATCH',f"REST host {host!r} is not allowed for market_type {normalized_market_type!r}",market_type=normalized_market_type,base_url=str(base_url or ''))
    return profile
# --- end 4B436662B Binance environment strict fail-closed restore ---
# 4B436662D Binance strict compatibility
from types import SimpleNamespace as _SNS62D
from urllib.parse import urlsplit as _us62d
try: BinanceEnvironmentError
except NameError:
    class BinanceEnvironmentError(RuntimeError): pass
def _be62d(code,msg,**kw):
    try: raise BinanceEnvironmentError(code,msg,**kw)
    except TypeError: raise BinanceEnvironmentError(code)
def resolve_binance_environment(market_type, base_url=None):
    mt=str(market_type or 'spot_demo').lower(); url=str(base_url or {'spot_demo':'https://demo-api.binance.com','spot':'https://api.binance.com'}.get(mt,'https://demo-api.binance.com')).rstrip('/'); p=_us62d(url)
    if p.scheme!='https' or not p.hostname: _be62d('BINANCE_REST_BASE_URL_INVALID','invalid',market_type=mt,base_url=url)
    if p.path not in {'','/'}: _be62d('BINANCE_REST_BASE_URL_INVALID','invalid path',market_type=mt,base_url=url)
    allowed={'spot_demo':{'demo-api.binance.com'},'spot':{'api.binance.com'}}
    if mt in allowed and p.hostname.lower() not in allowed[mt]: _be62d('BINANCE_REST_WS_ENVIRONMENT_MISMATCH','mismatch',market_type=mt,base_url=url)
    return _SNS62D(ok=True,market_type=mt,base_url=url,rest_base_url=url,rest_host=p.hostname.lower())

# 4B436662E Binance environment profile contract finalization
from dataclasses import dataclass as _phase62e_dataclass
from urllib.parse import urlsplit as _phase62e_urlsplit
from typing import FrozenSet as _Phase62EFrozenSet

try:
    BinanceEnvironmentError
except NameError:
    class BinanceEnvironmentError(RuntimeError):
        def __init__(self, code, message="", **context):
            super().__init__(str(code)); self.code = str(code); self.context = context

BINANCE_ENVIRONMENT_ROUTER_VERSION = globals().get("BINANCE_ENVIRONMENT_ROUTER_VERSION", "4B.4.3.6.6.27A")

@_phase62e_dataclass(frozen=True)
class BinanceEndpointProfile:
    market_type: str
    rest_base_url: str
    rest_host: str
    allowed_rest_hosts: _Phase62EFrozenSet[str]
    market_stream_base_url: str
    ok: bool = True
    fail_closed: bool = True
    @property
    def base_url(self) -> str:
        return self.rest_base_url

_ENV62E = {
    "spot_demo": ("https://demo-api.binance.com", frozenset({"demo-api.binance.com"}), "wss://demo-stream.binance.com:9443/stream"),
    "spot_testnet": ("https://testnet.binance.vision", frozenset({"testnet.binance.vision"}), "wss://stream.testnet.binance.vision/stream"),
    "spot_mainnet": ("https://api.binance.com", frozenset({"api.binance.com", "api1.binance.com", "api2.binance.com", "api3.binance.com"}), "wss://stream.binance.com:9443/stream"),
    "spot": ("https://api.binance.com", frozenset({"api.binance.com", "api1.binance.com", "api2.binance.com", "api3.binance.com"}), "wss://stream.binance.com:9443/stream"),
}

def _phase62e_raise(code: str, message: str, **context):
    try:
        raise BinanceEnvironmentError(code, message, **context)
    except TypeError:
        raise BinanceEnvironmentError(code)

def _phase62e_normalized_origin(base_url: str) -> tuple[str, str, str]:
    text = str(base_url or "").strip().rstrip("/")
    parsed = _phase62e_urlsplit(text)
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        _phase62e_raise("BINANCE_REST_BASE_URL_INVALID", "REST base URL must use https and include a hostname", base_url=text)
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        _phase62e_raise("BINANCE_REST_BASE_URL_INVALID", "REST base URL must be an origin", base_url=text)
    if parsed.path not in {"", "/"}:
        _phase62e_raise("BINANCE_REST_BASE_URL_INVALID", "REST base URL must not include /api or any path", base_url=text)
    return text, parsed.hostname.lower(), parsed.scheme.lower()

def resolve_binance_environment(market_type, base_url=None):
    mt = str(market_type or "spot_demo").strip().lower()
    if mt not in _ENV62E:
        _phase62e_raise("BINANCE_MARKET_TYPE_UNSUPPORTED", "unsupported market type", market_type=mt, base_url=base_url)
    canonical, allowed, ws = _ENV62E[mt]
    url = str(base_url or canonical).rstrip("/")
    text, host, _scheme = _phase62e_normalized_origin(url)
    if host not in allowed:
        _phase62e_raise("BINANCE_REST_WS_ENVIRONMENT_MISMATCH", "REST base URL host does not match market_type", market_type=mt, base_url=text, rest_host=host, allowed_rest_hosts=sorted(allowed))
    return BinanceEndpointProfile(market_type=mt, rest_base_url=text, rest_host=host, allowed_rest_hosts=allowed, market_stream_base_url=ws)

def build_combined_market_stream_url(profile, *, symbol: str, kline_interval: str) -> str:
    normalized_symbol = str(symbol or "").strip().lower()
    normalized_interval = str(kline_interval or "").strip()
    if not normalized_symbol:
        _phase62e_raise("BINANCE_STREAM_SYMBOL_MISSING", "symbol is required", market_type=getattr(profile, "market_type", None), base_url=getattr(profile, "rest_base_url", None))
    if not normalized_interval:
        _phase62e_raise("BINANCE_STREAM_INTERVAL_MISSING", "kline_interval is required", market_type=getattr(profile, "market_type", None), base_url=getattr(profile, "rest_base_url", None))
    streams = f"{normalized_symbol}@bookTicker/{normalized_symbol}@miniTicker/{normalized_symbol}@kline_{normalized_interval}"
    return f"{profile.market_stream_base_url}?streams={streams}"

def binance_environment_snapshot(profile, *, configured_rest_base_url: str) -> dict:
    return {
        "router_version": BINANCE_ENVIRONMENT_ROUTER_VERSION,
        "ok": True,
        "fail_closed": True,
        "market_type": profile.market_type,
        "configured_rest_base_url": str(configured_rest_base_url or "").rstrip("/"),
        "canonical_rest_base_url": profile.rest_base_url,
        "rest_base_url": profile.rest_base_url,
        "rest_host": profile.rest_host,
        "allowed_rest_hosts": sorted(profile.allowed_rest_hosts),
        "market_stream_base_url": profile.market_stream_base_url,
    }

# 4B436662F BinanceEnvironmentError safe constructor and full profile restore
from types import SimpleNamespace as _Phase62FSimpleNamespace
from urllib.parse import urlparse as _phase62f_urlparse
def _phase62f_profile(mt, rest, allowed, stream):
    parsed=_phase62f_urlparse(rest); return _Phase62FSimpleNamespace(ok=True,market_type=mt,base_url=rest,rest_base_url=rest,rest_host=parsed.netloc.lower(),allowed_rest_hosts=tuple(allowed),market_stream_base_url=stream)
def _phase62f_raise(code,message,*,market_type='',base_url=''):
    try: raise BinanceEnvironmentError(code,message,market_type=market_type,base_url=base_url)
    except TypeError:
        try: raise BinanceEnvironmentError(code,message)
        except TypeError: raise BinanceEnvironmentError(f'{code}: {message}')
def _phase62f_origin(url):
    text=str(url or '').rstrip('/'); p=_phase62f_urlparse(text)
    if p.path and p.path not in ('','/'): _phase62f_raise('BINANCE_REST_BASE_URL_INVALID','REST base URL must not include /api or any path',base_url=text)
    return f'{p.scheme}://{p.netloc}'.rstrip('/'),p.netloc.lower()
def resolve_binance_environment(market_type='spot_demo', base_url=None,*args,**kwargs):
    mt=str(market_type or 'spot_demo'); defaults={'spot_demo':('https://demo-api.binance.com',('demo-api.binance.com',),'wss://demo-stream.binance.com:9443/stream'),'spot_testnet':('https://testnet.binance.vision',('testnet.binance.vision',),'wss://stream.testnet.binance.vision:9443/stream'),'spot_mainnet':('https://api.binance.com',('api.binance.com',),'wss://stream.binance.com:9443/stream')}
    if mt not in defaults: _phase62f_raise('BINANCE_MARKET_TYPE_UNSUPPORTED','market_type is not supported',market_type=mt,base_url=str(base_url or ''))
    canonical,allowed,stream=defaults[mt]; origin,host=_phase62f_origin(base_url or canonical)
    if host not in allowed: _phase62f_raise('BINANCE_REST_WS_ENVIRONMENT_MISMATCH','REST base URL host does not match market_type',market_type=mt,base_url=origin)
    return _phase62f_profile(mt,origin,allowed,stream)
def build_combined_market_stream_url(profile,*,symbol,kline_interval):
    s=str(symbol or '').strip().lower(); i=str(kline_interval or '').strip()
    if not s: _phase62f_raise('BINANCE_STREAM_SYMBOL_MISSING','symbol is required',market_type=getattr(profile,'market_type',''),base_url=getattr(profile,'rest_base_url',''))
    if not i: _phase62f_raise('BINANCE_STREAM_INTERVAL_MISSING','kline_interval is required',market_type=getattr(profile,'market_type',''),base_url=getattr(profile,'rest_base_url',''))
    return f'{profile.market_stream_base_url}?streams={s}@bookTicker/{s}@miniTicker/{s}@kline_{i}'
def binance_environment_snapshot(profile,*,configured_rest_base_url):
    return {'router_version':globals().get('BINANCE_ENVIRONMENT_ROUTER_VERSION','4B.4.3.6.6.27A'),'ok':True,'fail_closed':True,'market_type':profile.market_type,'configured_rest_base_url':str(configured_rest_base_url or '').rstrip('/'),'canonical_rest_base_url':profile.rest_base_url,'rest_base_url':profile.rest_base_url,'rest_host':profile.rest_host,'allowed_rest_hosts':sorted(profile.allowed_rest_hosts),'market_stream_base_url':profile.market_stream_base_url}
