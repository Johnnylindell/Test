from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from threading import RLock
from typing import Any, TypeVar

T = TypeVar("T")


class CircuitOpenError(RuntimeError):
    """Raised when an integration is temporarily blocked after repeated failures."""


@dataclass(slots=True)
class BreakerState:
    failures: int = 0
    opened_until: float = 0.0
    last_error: str = ""
    half_open: bool = False


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, reset_seconds: float = 30.0) -> None:
        self.failure_threshold = max(1, int(failure_threshold))
        self.reset_seconds = max(0.1, float(reset_seconds))
        self._states: dict[str, BreakerState] = {}
        self._lock = RLock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            state = self._states.setdefault(key, BreakerState())
            if state.opened_until > now:
                return False
            if state.opened_until:
                if state.half_open:
                    return False
                state.half_open = True
                state.opened_until = 0.0
                state.failures = max(0, self.failure_threshold - 1)
            return True

    def success(self, key: str) -> None:
        with self._lock:
            self._states[key] = BreakerState()

    def failure(self, key: str, error: Exception | str = "") -> None:
        now = time.monotonic()
        with self._lock:
            state = self._states.setdefault(key, BreakerState())
            state.failures += 1
            state.last_error = str(error)[:240]
            state.half_open = False
            if state.failures >= self.failure_threshold:
                state.opened_until = now + self.reset_seconds

    def call(self, key: str, operation: Callable[[], T]) -> T:
        if not self.allow(key):
            status = self.status(key)
            raise CircuitOpenError(
                f"Circuit {key} är tillfälligt öppen; försök igen om "
                f"{status['retry_after_seconds']:.1f} sekunder"
            )
        try:
            result = operation()
        except Exception as exc:
            self.failure(key, exc)
            raise
        self.success(key)
        return result

    def status(self, key: str) -> dict[str, Any]:
        now = time.monotonic()
        with self._lock:
            state = self._states.setdefault(key, BreakerState())
            open_now = state.opened_until > now
            return {
                "open": open_now,
                "half_open": state.half_open,
                "failures": state.failures,
                "retry_after_seconds": round(max(0.0, state.opened_until - now), 3),
                "last_error": state.last_error,
            }
