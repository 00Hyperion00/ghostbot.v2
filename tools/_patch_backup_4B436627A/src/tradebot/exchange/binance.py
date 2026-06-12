from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any, AsyncIterator


from ..config import Settings
from ..models import Balance, Candle, SymbolRules
from ..utils import utc_ms


class BinanceSpotClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.base_url = settings.base_url.rstrip('/')
        import httpx
        self.rest = httpx.AsyncClient(timeout=15)
        self._time_offset_ms = 0
        self._exchange_info: dict[str, Any] | None = None

    async def close(self) -> None:
        await self.rest.aclose()

    def _market_ws_url(self) -> str:
        symbol = self.settings.symbol.lower()
        return f"wss://stream.binance.com:9443/stream?streams={symbol}@bookTicker/{symbol}@miniTicker/{symbol}@kline_{self.settings.kline_interval}"

    def _sign(self, payload: str) -> str:
        return hmac.new(self.settings.api_secret.encode('utf-8'), payload.encode('utf-8'), hashlib.sha256).hexdigest()

    async def sync_server_time(self) -> dict[str, Any]:
        resp = await self.rest.get(f"{self.base_url}/api/v3/time")
        resp.raise_for_status()
        data = resp.json()
        self._time_offset_ms = int(data['serverTime']) - utc_ms()
        return data

    async def public_test(self) -> dict[str, Any]:
        resp = await self.rest.get(f"{self.base_url}/api/v3/ticker/price", params={"symbol": self.settings.symbol})
        resp.raise_for_status()
        return resp.json()

    async def _signed_request(self, method: str, path: str, params: dict[str, Any] | None = None) -> Any:
        if not self.settings.api_key or not self.settings.api_secret:
            raise RuntimeError('API key/secret missing')
        params = dict(params or {})
        params.setdefault('recvWindow', 5000)
        params['timestamp'] = utc_ms() + self._time_offset_ms
        import httpx
        query = str(httpx.QueryParams(params))
        signature = self._sign(query)
        url = f"{self.base_url}{path}?{query}&signature={signature}"
        headers = {"X-MBX-APIKEY": self.settings.api_key}
        resp = await self.rest.request(method, url, headers=headers)
        if resp.status_code == 400 and '"code":-1021' in resp.text:
            await self.sync_server_time()
            return await self._signed_request(method, path, params)
        resp.raise_for_status()
        if not resp.text:
            return {}
        return resp.json()

    async def private_test(self) -> dict[str, Any]:
        await self.sync_server_time()
        return await self._signed_request('GET', '/api/v3/account')

    async def fetch_exchange_info(self) -> dict[str, Any]:
        if self._exchange_info is None:
            resp = await self.rest.get(f"{self.base_url}/api/v3/exchangeInfo")
            resp.raise_for_status()
            self._exchange_info = resp.json()
        return self._exchange_info

    async def fetch_symbol_rules(self, symbol: str | None = None) -> SymbolRules:
        symbol = symbol or self.settings.symbol
        info = await self.fetch_exchange_info()
        found = next((item for item in info.get('symbols', []) if item['symbol'] == symbol), None)
        if not found:
            raise RuntimeError(f'symbol rules not found: {symbol}')
        filters = {flt['filterType']: flt for flt in found.get('filters', [])}
        price_filter = filters.get('PRICE_FILTER', {})
        lot_filter = filters.get('LOT_SIZE', filters.get('MARKET_LOT_SIZE', {}))
        notional = filters.get('MIN_NOTIONAL', filters.get('NOTIONAL', {}))
        return SymbolRules(
            symbol=symbol,
            base_asset=found['baseAsset'],
            quote_asset=found['quoteAsset'],
            tick_size=float(price_filter.get('tickSize', 0)),
            step_size=float(lot_filter.get('stepSize', 0)),
            min_qty=float(lot_filter.get('minQty', 0)),
            max_qty=float(lot_filter.get('maxQty', 0)),
            min_notional=float(notional.get('notional', notional.get('minNotional', 0))),
            price_precision=found.get('pricePrecision'),
            quantity_precision=found.get('quantityPrecision'),
        )

    async def fetch_balances(self) -> dict[str, Balance]:
        account = await self.private_test()
        out: dict[str, Balance] = {}
        for row in account.get('balances', []):
            out[row['asset']] = Balance(free=float(row.get('free', 0)), locked=float(row.get('locked', 0)))
        return out

    async def fetch_open_orders(self, symbol: str | None = None) -> list[dict[str, Any]]:
        params = {'symbol': symbol or self.settings.symbol}
        return await self._signed_request('GET', '/api/v3/openOrders', params)

    async def fetch_order(self, symbol: str, order_id: str | int | None = None, client_order_id: str | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {'symbol': symbol}
        if order_id is not None:
            params['orderId'] = order_id
        if client_order_id:
            params['origClientOrderId'] = client_order_id
        return await self._signed_request('GET', '/api/v3/order', params)

    async def fetch_my_trades(self, symbol: str, order_id: str | int | None = None, limit: int = 50) -> list[dict[str, Any]]:
        params: dict[str, Any] = {'symbol': symbol, 'limit': limit}
        if order_id is not None:
            params['orderId'] = order_id
        return await self._signed_request('GET', '/api/v3/myTrades', params)

    async def create_limit_order(
        self,
        *,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        client_order_id: str,
        time_in_force: str = 'GTC',
        test: bool = False,
    ) -> dict[str, Any]:
        path = '/api/v3/order/test' if test else '/api/v3/order'
        params = {
            'symbol': symbol,
            'side': side,
            'type': 'LIMIT',
            'timeInForce': time_in_force,
            'quantity': quantity,
            'price': price,
            'newClientOrderId': client_order_id,
        }
        return await self._signed_request('POST', path, params)

    async def cancel_order(self, *, symbol: str, order_id: str | int | None = None, client_order_id: str | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {'symbol': symbol}
        if order_id is not None:
            params['orderId'] = order_id
        if client_order_id:
            params['origClientOrderId'] = client_order_id
        return await self._signed_request('DELETE', '/api/v3/order', params)

    async def fetch_klines(self, symbol: str | None = None, interval: str | None = None, limit: int = 100) -> list[Candle]:
        resp = await self.rest.get(
            f"{self.base_url}/api/v3/klines",
            params={"symbol": symbol or self.settings.symbol, "interval": interval or self.settings.kline_interval, "limit": limit},
        )
        resp.raise_for_status()
        payload = resp.json()
        out = []
        for item in payload:
            out.append(Candle(
                open_time=int(item[0]),
                open=float(item[1]),
                high=float(item[2]),
                low=float(item[3]),
                close=float(item[4]),
                volume=float(item[5]),
                close_time=int(item[6]),
                quote_volume=float(item[7]),
                taker_buy_quote_volume=float(item[10]) if item[10] is not None else None,
                closed=True,
            ))
        return out

    async def stream_market(self) -> AsyncIterator[dict[str, Any]]:
        import websockets
        async with websockets.connect(self._market_ws_url(), ping_interval=20, ping_timeout=20) as ws:
            async for raw in ws:
                yield json.loads(raw)
