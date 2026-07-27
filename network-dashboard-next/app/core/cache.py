from __future__ import annotations

import time
from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
from threading import RLock
from typing import Any, Generic, TypeVar

T = TypeVar("T")
_MISSING = object()


@dataclass(slots=True)
class _Entry(Generic[T]):
    expires_at: float
    value: T


class TTLCache:
    def __init__(self) -> None:
        self._lock = RLock()
        self._values: dict[str, _Entry[Any]] = {}
        self._loading: dict[str, RLock] = {}

    def _get(self, key: str) -> Any:
        now = time.monotonic()
        with self._lock:
            entry = self._values.get(key)
            if entry is None:
                return _MISSING
            if entry.expires_at <= now:
                self._values.pop(key, None)
                return _MISSING
            return deepcopy(entry.value)

    def get(self, key: str, default: Any = None) -> Any:
        value = self._get(key)
        return default if value is _MISSING else value

    def contains(self, key: str) -> bool:
        return self._get(key) is not _MISSING

    def set(self, key: str, value: T, ttl_seconds: float) -> T:
        expires_at = time.monotonic() + max(0.1, float(ttl_seconds))
        stored = deepcopy(value)
        with self._lock:
            self._values[key] = _Entry(expires_at=expires_at, value=stored)
        return deepcopy(stored)

    def get_or_set(self, key: str, ttl_seconds: float, loader: Callable[[], T]) -> tuple[T, bool]:
        cached = self._get(key)
        if cached is not _MISSING:
            return cached, True

        # A per-key lock prevents a burst of identical requests from all calling an
        # external integration after the same cache entry expires.
        with self._lock:
            load_lock = self._loading.setdefault(key, RLock())
        with load_lock:
            cached = self._get(key)
            if cached is not _MISSING:
                return cached, True
            value = loader()
            result = self.set(key, value, ttl_seconds)
        with self._lock:
            self._loading.pop(key, None)
        return result, False

    def invalidate(self, prefix: str = "") -> int:
        with self._lock:
            keys = [key for key in self._values if not prefix or key.startswith(prefix)]
            for key in keys:
                self._values.pop(key, None)
            return len(keys)

    def size(self) -> int:
        with self._lock:
            # Remove expired entries so diagnostics reflect usable cache entries.
            now = time.monotonic()
            expired = [key for key, entry in self._values.items() if entry.expires_at <= now]
            for key in expired:
                self._values.pop(key, None)
            return len(self._values)
