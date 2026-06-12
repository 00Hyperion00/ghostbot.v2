from __future__ import annotations

import argparse
import asyncio
import json

import uvicorn

from .api import create_managed_app
from .config import Settings
from .engine import TradeBotEngine
from .persistence import SQLiteStore
from .ai.provider import XGBoostSignalProvider
from .ai.service import create_ai_service
from .training.train_xgb import train as train_xgb_model


async def run_bot(settings: Settings) -> None:
    store = SQLiteStore(settings.database_path)
    engine = TradeBotEngine(settings, store)
    await engine.start()
    try:
        while True:
            await asyncio.sleep(1)
    finally:
        await engine.close()


def run_api(settings: Settings, host: str, port: int) -> None:
    app = create_managed_app(settings)
    uvicorn.run(app, host=host, port=port, loop='asyncio', log_level='warning', lifespan='on')


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd', required=True)

    run_p = sub.add_parser('run')
    run_p.add_argument('--config', required=True)

    api_p = sub.add_parser('api')
    api_p.add_argument('--config', required=True)
    api_p.add_argument('--host', default='127.0.0.1')
    api_p.add_argument('--port', default=8787, type=int)

    dashboard_p = sub.add_parser('dashboard')
    dashboard_p.add_argument('--config', required=True)
    dashboard_p.add_argument('--host', default='127.0.0.1')
    dashboard_p.add_argument('--port', default=8787, type=int)

    ai_p = sub.add_parser('ai-service')
    ai_p.add_argument('--model-path', required=True)
    ai_p.add_argument('--threshold', type=float, default=0.60)
    ai_p.add_argument('--buy-threshold', type=float, default=0.64)
    ai_p.add_argument('--sell-threshold', type=float, default=0.57)
    ai_p.add_argument('--hold-band-low', type=float, default=0.45)
    ai_p.add_argument('--hold-band-high', type=float, default=0.55)
    ai_p.add_argument('--indecision-margin', type=float, default=0.08)
    ai_p.add_argument('--threshold-profile', default='runtime_settings')
    ai_p.add_argument('--host', default='127.0.0.1')
    ai_p.add_argument('--port', default=8000, type=int)

    train_p = sub.add_parser('train-model')
    train_p.add_argument('--symbol', required=True)
    train_p.add_argument('--interval', default='1m')
    train_p.add_argument('--days', type=int, default=30)
    train_p.add_argument('--out', required=True)
    train_p.add_argument('--base-url', default='https://api.binance.com')
    train_p.add_argument('--class-weight-profile', default='none')
    train_p.add_argument('--threshold-profile', default='balanced')
    train_p.add_argument('--feature-lag', type=int, default=None)

    args = parser.parse_args()
    if args.cmd == 'ai-service':
        provider = XGBoostSignalProvider(args.model_path, threshold=args.threshold, buy_threshold=args.buy_threshold, sell_threshold=args.sell_threshold, hold_band_low=args.hold_band_low, hold_band_high=args.hold_band_high, indecision_margin=args.indecision_margin, threshold_profile=args.threshold_profile)
        app = create_ai_service(provider)
        uvicorn.run(app, host=args.host, port=args.port)
        return
    if args.cmd == 'train-model':
        result = train_xgb_model(
            args.symbol.upper(),
            args.interval,
            args.days,
            args.out,
            base_url=args.base_url,
            class_weight_profile=args.class_weight_profile,
            threshold_profile=args.threshold_profile,
            feature_lag=args.feature_lag,
        )
        print(json.dumps(result, ensure_ascii=False, default=str))
        return
    if args.cmd == 'dashboard':
        from .ui.dashboard import launch_dashboard
        launch_dashboard(args.config, args.host, args.port)
        return

    settings = Settings.from_yaml(args.config)
    if args.cmd == 'run':
        asyncio.run(run_bot(settings))
    else:
        run_api(settings, args.host, args.port)


if __name__ == '__main__':
    main()
