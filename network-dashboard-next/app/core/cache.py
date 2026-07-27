from __future__ import annotations

import time
from collections.abc import Callable
from copy import deepcopy
from threading import RLock
from typing import Any


class TTLCache:
    def __init__(self) -> None:
        self._lock = RLock()
        self._values: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        now = time.monotonic()
        with self._lock:
            row = self._values.get(key)
            if not row:
                return None
            expires_at, value = row
            if expires_at <= now:
                self._values.pop(key, None)
                return None
            return deepcopy(value)

    def set(self, key: str, value: Any, ttl_seconds: float) -> Any:
        expires_at = time.monotonic() + max(0.1, float(ttl_seconds))
        with self._lock:
            self._values[key] = (expires_at, deepcopy(value))
        return deepcopy(value)

    def get_or_set(self, key: str, ttl_seconds: float, loader: Callable[[], Any]) -> tuple[Any, bool]:
        cached = self.get(key)
        if cached is not None:
            return cached, True
        value = loader()
        return self.set(key, value, ttl_seconds), False

    def invalidate(self, prefix: str = "") -> int:
        with self._lock:
            keys = [key for key in self._values if not prefix or key.startswith(prefix)]
            for key in keys:
                self._values.pop(key, None)
            return len(keys)

    def size(self) -> int:
        with self._lock:
            return len(self._values)
