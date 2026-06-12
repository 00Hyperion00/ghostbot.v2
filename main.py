from tradebot.ai.provider import XGBoostSignalProvider
from tradebot.ai.service import create_ai_service

import os

provider = XGBoostSignalProvider(
    os.getenv('TRADEBOT_AI_MODEL_PATH', 'models/xgboost_trade_model.json'),
    threshold=float(os.getenv('TRADEBOT_AI_THRESHOLD', '0.60')),
    buy_threshold=float(os.getenv('TRADEBOT_AI_BUY_THRESHOLD', '0.64')),
    sell_threshold=float(os.getenv('TRADEBOT_AI_SELL_THRESHOLD', '0.57')),
    hold_band_low=float(os.getenv('TRADEBOT_AI_HOLD_BAND_LOW', '0.45')),
    hold_band_high=float(os.getenv('TRADEBOT_AI_HOLD_BAND_HIGH', '0.55')),
    indecision_margin=float(os.getenv('TRADEBOT_AI_INDECISION_MARGIN', '0.08')),
    threshold_profile=os.getenv('TRADEBOT_AI_THRESHOLD_PROFILE', 'runtime_settings'),
)
app = create_ai_service(provider)
