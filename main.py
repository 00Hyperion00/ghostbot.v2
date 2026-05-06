from tradebot.ai.provider import XGBoostSignalProvider
from tradebot.ai.service import create_ai_service

import os

provider = XGBoostSignalProvider(
    os.getenv('TRADEBOT_AI_MODEL_PATH', 'models/xgboost_trade_model.json'),
    threshold=float(os.getenv('TRADEBOT_AI_THRESHOLD', '0.60')),
)
app = create_ai_service(provider)
