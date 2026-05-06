from __future__ import annotations

from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .provider import XGBoostSignalProvider


class CandleIn(BaseModel):
    closeTime: int
    open: float
    high: float
    low: float
    close: float
    volume: float


class TradeRequest(BaseModel):
    symbol: str
    interval: str = '1m'
    candles: List[CandleIn]


class TradeResponse(BaseModel):
    signal: str
    confidence: float | None = None
    trend: str
    reason: str


class ConfigUpdate(BaseModel):
    threshold: float | None = None
    model_path: str | None = None


def create_ai_service(provider: XGBoostSignalProvider) -> FastAPI:
    app = FastAPI(title='TradeBot AI Brain', version='0.2.0')
    app.add_middleware(
        CORSMiddleware,
        allow_origins=['*'],
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )

    @app.get('/health')
    async def health() -> dict:
        payload = {'ok': provider.available, 'model_path': provider.model_path, 'threshold': provider.threshold}
        schema_info = getattr(provider, 'schema_info', None)
        if callable(schema_info):
            payload.update(schema_info())
        else:
            payload['load_error'] = getattr(provider, 'load_error', None)
        return payload

    @app.post('/update_config')
    async def update_config(config: ConfigUpdate) -> dict:
        provider.reload(model_path=config.model_path, threshold=config.threshold)
        payload = {'ok': True, 'model_path': provider.model_path, 'threshold': provider.threshold, 'available': provider.available}
        schema_info = getattr(provider, 'schema_info', None)
        if callable(schema_info):
            payload.update(schema_info())
        else:
            payload['load_error'] = getattr(provider, 'load_error', None)
        return payload

    @app.post('/predict', response_model=TradeResponse)
    async def predict(payload: TradeRequest) -> TradeResponse:
        try:
            decision = provider.predict([
                {
                    'closeTime': c.closeTime,
                    'open': c.open,
                    'high': c.high,
                    'low': c.low,
                    'close': c.close,
                    'volume': c.volume,
                }
                for c in payload.candles
            ], symbol=payload.symbol, interval=payload.interval)
            return TradeResponse(signal=decision.signal, confidence=decision.confidence, trend=decision.trend, reason=decision.reason)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f'AI Processing Error: {exc}') from exc

    return app


def create_ai_service_from_env() -> FastAPI:
    import os
    provider = XGBoostSignalProvider(
        os.getenv('TRADEBOT_AI_MODEL_PATH', 'models/xgboost_trade_model.json'),
        threshold=float(os.getenv('TRADEBOT_AI_THRESHOLD', '0.60')),
    )
    return create_ai_service(provider)
