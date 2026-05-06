from __future__ import annotations

import logging
from typing import Any

from .models import LogEvent
from .persistence import SQLiteStore
from .utils import stable_hash, utc_ms


class EventLogger:
    def __init__(self, store: SQLiteStore) -> None:
        self.store = store
        self._logger = logging.getLogger('tradebot')
        if not self._logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
            handler.setFormatter(formatter)
            self._logger.addHandler(handler)
            self._logger.setLevel(logging.INFO)
        self._recent_log_fingerprints: dict[str, int] = {}

    def _should_dedupe(self, code: str, data: dict[str, Any], window_ms: int) -> bool:
        now = utc_ms()
        fp = stable_hash({"code": code, "data": data})
        last = self._recent_log_fingerprints.get(fp)
        self._recent_log_fingerprints[fp] = now
        stale = [k for k, v in self._recent_log_fingerprints.items() if now - v > window_ms * 3]
        for k in stale:
            self._recent_log_fingerprints.pop(k, None)
        return last is not None and now - last <= window_ms

    def log(self, level: str, code: str, message: str, data: dict[str, Any] | None = None, *, dedupe_ms: int | None = None) -> None:
        payload = data or {}
        if dedupe_ms and self._should_dedupe(code, payload, dedupe_ms):
            return
        event = LogEvent(ts=utc_ms(), level=level, code=code, message=message, data=payload)
        self.store.append_log(event)
        log_method = getattr(self._logger, level.lower(), self._logger.info)
        log_method('%s | %s | %s', code, message, payload)

    def info(self, code: str, message: str, data: dict[str, Any] | None = None, *, dedupe_ms: int | None = None) -> None:
        self.log('INFO', code, message, data, dedupe_ms=dedupe_ms)

    def warn(self, code: str, message: str, data: dict[str, Any] | None = None, *, dedupe_ms: int | None = None) -> None:
        self.log('WARN', code, message, data, dedupe_ms=dedupe_ms)

    def error(self, code: str, message: str, data: dict[str, Any] | None = None, *, dedupe_ms: int | None = None) -> None:
        self.log('ERROR', code, message, data, dedupe_ms=dedupe_ms)
