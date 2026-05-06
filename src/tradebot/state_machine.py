from __future__ import annotations

from .enums import BotState
from .models import RuntimeState


def transition(runtime: RuntimeState, next_state: BotState | str) -> None:
    runtime.state = BotState(next_state).value if not isinstance(next_state, str) else next_state
