from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradebot.config import Settings  # noqa: E402
from tradebot.diagnostics import DIAGNOSTICS_CONTRACT_VERSION, write_support_bundle  # noqa: E402
from tradebot.persistence import SQLiteStore  # noqa: E402
from tradebot.utils import utc_ms  # noqa: E402


def fetch_status(base_url: str, timeout: float) -> dict:
    try:
        with urlopen(f'{base_url.rstrip("/")}/status', timeout=timeout) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as exc:
        return {
            'contract_version': DIAGNOSTICS_CONTRACT_VERSION,
            'status_fetch_ok': False,
            'status_fetch_error': str(exc),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description='Export a redacted TradeBot support bundle.')
    parser.add_argument('--config', default='config.local.yaml')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--output', default=None)
    parser.add_argument('--timeout', type=float, default=3.0)
    args = parser.parse_args()

    config_path = Path(args.config)
    settings = Settings.from_yaml(config_path) if config_path.exists() else Settings()
    store = SQLiteStore(settings.database_path)
    status = fetch_status(f'http://{args.host}:{args.port}', args.timeout)
    logs = store.fetch_logs(limit=250, order='desc')
    out = Path(args.output) if args.output else ROOT / '.tradebot' / f'support_bundle_{utc_ms()}.zip'
    bundle = write_support_bundle(out, status=status, logs=logs, config=settings.to_dict())
    print(json.dumps({
        'contract_version': DIAGNOSTICS_CONTRACT_VERSION,
        'ok': True,
        'bundle_path': str(bundle),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
