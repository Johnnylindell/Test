from __future__ import annotations

import time
from dataclasses import dataclass
from threading import RLock


@dataclass(slots=True)
class BreakerState:
    failures: int = 0
    opened_until: float = 0.0


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, reset_seconds: float = 30.0) -> None:
        self.failure_threshold = max(1, int(failure_threshold))
        self.reset_seconds = max(1.0, float(reset_seconds))
        self._states: dict[str, BreakerState] = {}
        self._lock = RLock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            state = self._states.setdefault(key, BreakerState())
            if state.opened_until and state.opened_until > now:
                return False
            if state.opened_until and state.opened_until <= now:
                state.opened_until = 0.0
                state.failures = 0
            return True

    def success(self, key: str) -> None:
        with self._lock:
            self._states[key] = BreakerState()

    def failure(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            state = self._states.setdefault(key, BreakerState())
            state.failures += 1
            if state.failures >= self.failure_threshold:
                state.opened_until = now + self.reset_seconds

    def status(self, key: str) -> dict:
        now = time.monotonic()
        with self._lock:
            state = self._states.setdefault(key, BreakerState())
            open_now = state.opened_until > now
            return {
                "open": open_now,
                "failures": state.failures,
                "retry_after_seconds": round(max(0.0, state.opened_until - now), 1),
            }
